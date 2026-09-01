from sqlalchemy.orm import Session

from app.models import Alert, Measurement, MonitoringStatus, PollState, WANLink
from app.schemas import LatestMetrics


def compute_monitoring_status(icmp_enabled: bool, snmp_enabled: bool, monitoring_disabled: bool = False) -> MonitoringStatus:
    if monitoring_disabled:
        return MonitoringStatus.monitoring_disabled
    if icmp_enabled and snmp_enabled:
        return MonitoringStatus.fully_monitored
    if icmp_enabled:
        return MonitoringStatus.icmp_only
    if snmp_enabled:
        return MonitoringStatus.snmp_only
    return MonitoringStatus.not_configured


def latest_metrics(db: Session, wan_link: WANLink) -> LatestMetrics:
    """ICMP and SNMP polls write independent Measurement rows on independent
    schedules — one poll never fills in the other's fields. Naively taking
    "the single newest row" would blank out bandwidth whenever the most
    recent poll happened to be an ICMP one (or vice versa), even though both
    kinds of data are still current. Instead, find the latest row of each
    kind and merge them.

    ICMP rows always set `availability` (never None); SNMP rows always set
    `rx_bps` together with the rest of the traffic fields (never None) —
    each poll's Measurement rows are mutually exclusive on these fields, so
    filtering on them reliably tells the two kinds apart.
    """
    poll_state: PollState | None = wan_link.poll_state

    latest_icmp: Measurement | None = (
        db.query(Measurement)
        .filter(Measurement.wan_link_id == wan_link.id, Measurement.availability.isnot(None))
        .order_by(Measurement.timestamp.desc())
        .first()
    )
    latest_snmp: Measurement | None = (
        db.query(Measurement)
        .filter(Measurement.wan_link_id == wan_link.id, Measurement.rx_bps.isnot(None))
        .order_by(Measurement.timestamp.desc())
        .first()
    )

    return LatestMetrics(
        rx_bps=latest_snmp.rx_bps if latest_snmp else None,
        tx_bps=latest_snmp.tx_bps if latest_snmp else None,
        total_bps=latest_snmp.total_bps if latest_snmp else None,
        utilisation_percent=latest_snmp.utilisation_percent if latest_snmp else None,
        latency_ms=latest_icmp.latency_ms if latest_icmp else None,
        packet_loss_percent=latest_icmp.packet_loss_percent if latest_icmp else None,
        jitter_ms=latest_icmp.jitter_ms if latest_icmp else None,
        availability=latest_icmp.availability if latest_icmp else None,
        last_snmp_poll_at=poll_state.last_snmp_poll_at if poll_state else None,
        last_icmp_poll_at=poll_state.last_icmp_poll_at if poll_state else None,
    )


def compute_health(db: Session, wan_link: WANLink) -> str:
    # Per UI_DESIGN.md, grey/"unknown" covers both "not configured yet" and
    # "deliberately not monitored" — neither has a meaningful up/down state.
    if wan_link.monitoring_status in (MonitoringStatus.not_configured, MonitoringStatus.monitoring_disabled):
        return "unknown"

    poll_state: PollState | None = wan_link.poll_state
    if poll_state and poll_state.is_down:
        return "critical"

    open_alert_exists = (
        db.query(Alert)
        .filter(Alert.wan_link_id == wan_link.id, Alert.ended_at.is_(None), Alert.alert_type != "wan_recovered")
        .first()
        is not None
    )
    if open_alert_exists:
        return "warning"

    has_any_measurement = db.query(Measurement.id).filter(Measurement.wan_link_id == wan_link.id).first() is not None
    if not has_any_measurement:
        return "unknown"

    return "healthy"
