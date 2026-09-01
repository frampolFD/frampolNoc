"""Background polling worker.

Runs entirely outside the HTTP request/response cycle. A single lightweight
"tick" loop wakes up every few seconds, looks at which WAN links are due for
an ICMP or SNMP poll (per their configured interval), and fires one
independent asyncio task per due poll. Each poll:

- is guarded by a per-target lock so a slow/hung target can never overlap
  with itself on the next tick,
- has its own timeout (enforced inside icmp_client / snmp_client),
- is wrapped in try/except so one target's failure never affects any other
  target or blocks the API.

Quick actions ("Ping Now", "Poll SNMP Now") call the exact same
poll_icmp_for_wan_link / poll_snmp_for_wan_link functions the scheduler
calls, so there is exactly one code path for monitoring logic.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.config import settings
from app.database import SessionLocal
from app.models import Alert, AlertSeverity, AlertType, Measurement, PollState, SNMPCredential, WANLink
from app.monitoring import alert_engine, icmp_client, snmp_client
from app.monitoring.calculations import calculate_rate, total_throughput_bps, utilisation_percent
from app.monitoring.scheduling import effective_interval
from app.security import decrypt_secret
from app.settings_store import get_or_create_settings

logger = logging.getLogger("frampol.worker")


def _aware_utc(dt: datetime | None) -> datetime | None:
    """SQLite has no real timestamptz type: SQLAlchemy writes our
    timezone-aware UTC datetimes as plain strings and reads them back
    naive. Anything loaded from the DB needs this before it can be
    subtracted from a freshly created `datetime.now(timezone.utc)`, or
    Python raises "can't subtract offset-naive and offset-aware
    datetimes". Values are always stored in UTC, so re-attaching UTC
    tzinfo to a naive value is correct (and a no-op if already aware).
    """
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)

_locks: dict[str, asyncio.Lock] = {}
_background_tasks: set[asyncio.Task] = set()


def _lock_for(key: str) -> asyncio.Lock:
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock


def _get_or_create_poll_state(db, wan_link: WANLink) -> PollState:
    state = db.query(PollState).filter(PollState.wan_link_id == wan_link.id).first()
    if state:
        return state
    state = PollState(wan_link_id=wan_link.id)
    db.add(state)
    db.flush()
    return state


def _open_alert(db, wan_link_id: int, alert_type: AlertType, severity: AlertSeverity, message: str, threshold=None, duration_seconds=None):
    existing = (
        db.query(Alert)
        .filter(Alert.wan_link_id == wan_link_id, Alert.alert_type == alert_type, Alert.ended_at.is_(None))
        .first()
    )
    if existing:
        return existing
    alert = Alert(
        wan_link_id=wan_link_id,
        alert_type=alert_type,
        severity=severity,
        threshold=threshold,
        duration_seconds=duration_seconds,
        message=message,
    )
    db.add(alert)
    return alert


def _close_alert(db, wan_link_id: int, alert_type: AlertType):
    existing = (
        db.query(Alert)
        .filter(Alert.wan_link_id == wan_link_id, Alert.alert_type == alert_type, Alert.ended_at.is_(None))
        .first()
    )
    if existing:
        existing.ended_at = datetime.now(timezone.utc)
    return existing


def _alert_open(db, wan_link_id: int, alert_type: AlertType) -> bool:
    return (
        db.query(Alert)
        .filter(Alert.wan_link_id == wan_link_id, Alert.alert_type == alert_type, Alert.ended_at.is_(None))
        .first()
        is not None
    )


async def poll_icmp_for_wan_link(wan_link_id: int) -> None:
    lock = _lock_for(f"icmp:{wan_link_id}")
    if lock.locked():
        logger.debug("skipping ICMP poll for wan_link %s: previous poll still in flight", wan_link_id)
        return

    async with lock:
        db = SessionLocal()
        try:
            wan_link = db.get(WANLink, wan_link_id)
            if not wan_link or not wan_link.icmp_enabled or not wan_link.icmp_target_ip:
                return

            try:
                result = await icmp_client.ping(
                    wan_link.icmp_target_ip,
                    count=settings.icmp_count_per_poll,
                    timeout_seconds=settings.icmp_timeout_seconds,
                )
            except Exception:
                logger.exception("ICMP poll failed for wan_link %s", wan_link_id)
                return

            state = _get_or_create_poll_state(db, wan_link)
            state.last_icmp_poll_at = datetime.now(timezone.utc)

            db.add(
                Measurement(
                    wan_link_id=wan_link.id,
                    latency_ms=result.latency_ms,
                    packet_loss_percent=result.packet_loss_percent,
                    jitter_ms=result.jitter_ms,
                    availability=result.reachable,
                )
            )

            down_open = _alert_open(db, wan_link.id, AlertType.wan_down)
            availability_decision = alert_engine.evaluate_availability(result.reachable, down_open)
            if availability_decision.action == alert_engine.AlertAction.open:
                _open_alert(db, wan_link.id, AlertType.wan_down, AlertSeverity.critical, availability_decision.message)
                state.is_down = True
            elif availability_decision.action == alert_engine.AlertAction.close:
                _close_alert(db, wan_link.id, AlertType.wan_down)
                state.is_down = False
                db.add(
                    Alert(
                        wan_link_id=wan_link.id,
                        alert_type=AlertType.wan_recovered,
                        severity=AlertSeverity.info,
                        message=availability_decision.message,
                        ended_at=datetime.now(timezone.utc),
                    )
                )

            latency_open = _alert_open(db, wan_link.id, AlertType.high_latency)
            latency_decision = alert_engine.evaluate_high_latency(result.latency_ms, settings.high_latency_threshold_ms, latency_open)
            if latency_decision.action == alert_engine.AlertAction.open:
                _open_alert(
                    db, wan_link.id, AlertType.high_latency, AlertSeverity.warning, latency_decision.message,
                    threshold=settings.high_latency_threshold_ms,
                )
            elif latency_decision.action == alert_engine.AlertAction.close:
                _close_alert(db, wan_link.id, AlertType.high_latency)

            loss_open = _alert_open(db, wan_link.id, AlertType.packet_loss)
            loss_decision = alert_engine.evaluate_packet_loss(result.packet_loss_percent, settings.packet_loss_threshold_percent, loss_open)
            if loss_decision.action == alert_engine.AlertAction.open:
                _open_alert(
                    db, wan_link.id, AlertType.packet_loss, AlertSeverity.warning, loss_decision.message,
                    threshold=settings.packet_loss_threshold_percent,
                )
            elif loss_decision.action == alert_engine.AlertAction.close:
                _close_alert(db, wan_link.id, AlertType.packet_loss)

            db.commit()
        finally:
            db.close()


async def poll_snmp_for_wan_link(wan_link_id: int) -> None:
    lock = _lock_for(f"snmp:{wan_link_id}")
    if lock.locked():
        logger.debug("skipping SNMP poll for wan_link %s: previous poll still in flight", wan_link_id)
        return

    async with lock:
        db = SessionLocal()
        try:
            wan_link = db.get(WANLink, wan_link_id)
            if not wan_link or not wan_link.snmp_enabled or not wan_link.snmp_target_ip or wan_link.selected_if_index is None:
                return

            credential = db.get(SNMPCredential, wan_link.snmp_credential_id) if wan_link.snmp_credential_id else None
            if not credential:
                logger.warning("wan_link %s has SNMP enabled but no credential configured", wan_link_id)
                return
            community = decrypt_secret(credential.encrypted_secret)

            try:
                counters = await snmp_client.poll_interface(
                    wan_link.snmp_target_ip,
                    wan_link.snmp_version.value if wan_link.snmp_version else "v2c",
                    community,
                    wan_link.selected_if_index,
                    timeout=settings.snmp_timeout_seconds,
                    retries=settings.snmp_retries,
                )
            except Exception:
                logger.exception("SNMP poll failed for wan_link %s", wan_link_id)
                return
            finally:
                del community

            state = _get_or_create_poll_state(db, wan_link)
            now = datetime.now(timezone.utc)

            util_value = None
            if (
                state.last_in_octets is not None
                and state.last_out_octets is not None
                and state.last_snmp_poll_at is not None
                and counters.in_octets is not None
                and counters.out_octets is not None
            ):
                elapsed = (now - _aware_utc(state.last_snmp_poll_at)).total_seconds()
                if elapsed > 0:
                    rx = calculate_rate(state.last_in_octets, counters.in_octets, elapsed, is_64_bit=counters.used_high_capacity_counters)
                    tx = calculate_rate(state.last_out_octets, counters.out_octets, elapsed, is_64_bit=counters.used_high_capacity_counters)
                    total = total_throughput_bps(rx.bps, tx.bps)
                    util_value = utilisation_percent(total, wan_link.circuit_capacity_bps)

                    db.add(
                        Measurement(
                            wan_link_id=wan_link.id,
                            rx_bps=rx.bps,
                            tx_bps=tx.bps,
                            total_bps=total,
                            utilisation_percent=util_value,
                            rx_bytes_delta=rx.bytes_delta,
                            tx_bytes_delta=tx.bytes_delta,
                        )
                    )

            if counters.in_octets is not None:
                state.last_in_octets = counters.in_octets
            if counters.out_octets is not None:
                state.last_out_octets = counters.out_octets
            state.last_snmp_poll_at = now

            if util_value is not None:
                sustained_open = _alert_open(db, wan_link.id, AlertType.sustained_utilisation)
                result = alert_engine.evaluate_sustained_utilisation(
                    util_value,
                    wan_link.sustained_util_threshold_percent,
                    wan_link.sustained_util_duration_seconds,
                    _aware_utc(state.utilisation_breach_since),
                    now,
                    sustained_open,
                )
                state.utilisation_breach_since = result.new_breach_since
                if result.decision.action == alert_engine.AlertAction.open:
                    _open_alert(
                        db, wan_link.id, AlertType.sustained_utilisation, AlertSeverity.warning, result.decision.message,
                        threshold=wan_link.sustained_util_threshold_percent,
                        duration_seconds=wan_link.sustained_util_duration_seconds,
                    )
                elif result.decision.action == alert_engine.AlertAction.close:
                    _close_alert(db, wan_link.id, AlertType.sustained_utilisation)

            db.commit()
        finally:
            db.close()


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _tick() -> None:
    db = SessionLocal()
    try:
        global_settings = get_or_create_settings(db)
        wan_links = db.query(WANLink).all()
        now = datetime.now(timezone.utc)
        for wan_link in wan_links:
            state = wan_link.poll_state

            if wan_link.icmp_enabled and wan_link.icmp_target_ip:
                interval = effective_interval(wan_link.icmp_interval_seconds, global_settings.icmp_interval_seconds)
                last = _aware_utc(state.last_icmp_poll_at) if state else None
                if last is None or (now - last).total_seconds() >= interval:
                    _spawn(poll_icmp_for_wan_link(wan_link.id))

            if wan_link.snmp_enabled and wan_link.snmp_target_ip and wan_link.selected_if_index is not None:
                interval = effective_interval(wan_link.snmp_interval_seconds, global_settings.snmp_interval_seconds)
                last = _aware_utc(state.last_snmp_poll_at) if state else None
                if last is None or (now - last).total_seconds() >= interval:
                    _spawn(poll_snmp_for_wan_link(wan_link.id))
        db.commit()  # persists the SystemSettings row if this tick just bootstrapped it
    finally:
        db.close()


class Worker:
    """Owns the scheduler loop's lifecycle for the FastAPI app."""

    def __init__(self, tick_seconds: float = 5.0):
        self.tick_seconds = tick_seconds
        self._stop_event: asyncio.Event | None = None
        self._loop_task: asyncio.Task | None = None

    async def _run(self):
        while not self._stop_event.is_set():
            try:
                await _tick()
            except Exception:
                logger.exception("worker tick failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.tick_seconds)
            except asyncio.TimeoutError:
                pass

    def start(self):
        self._stop_event = asyncio.Event()
        self._loop_task = asyncio.create_task(self._run())
        logger.info("monitoring worker started (tick=%ss)", self.tick_seconds)

    async def stop(self):
        if self._stop_event:
            self._stop_event.set()
        if self._loop_task:
            await self._loop_task
        if _background_tasks:
            await asyncio.gather(*_background_tasks, return_exceptions=True)
        logger.info("monitoring worker stopped")


worker = Worker()
