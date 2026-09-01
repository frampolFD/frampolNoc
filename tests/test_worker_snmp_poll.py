import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.database import Base
from app.models import Branch, City, Customer, PollState, SNMPCredential, SNMPVersion, WANLink
from app.monitoring import worker as worker_module
from app.monitoring.snmp_client import InterfaceCounters
from app.security import encrypt_secret


def _make_snmp_wan_link(db, *, credential_id="default", encrypted_secret=None, monitoring_disabled=False):
    customer = Customer(name="Test Customer")
    db.add(customer)
    db.flush()
    city = City(name="Test City", province="Test Province", country_code="ZW")
    db.add(city)
    db.flush()
    branch = Branch(customer_id=customer.id, city_id=city.id, name="Test Branch", latitude=0.0, longitude=0.0)
    db.add(branch)
    db.flush()

    resolved_credential_id = None
    if credential_id == "default":
        credential = SNMPCredential(
            name="Test Cred", version=SNMPVersion.v2c, encrypted_secret=encrypted_secret or encrypt_secret("public")
        )
        db.add(credential)
        db.flush()
        resolved_credential_id = credential.id
    elif credential_id is not None:
        resolved_credential_id = credential_id  # explicit id, e.g. pointing at nothing

    wan_link = WANLink(
        branch_id=branch.id,
        name_generated="Test WAN",
        circuit_capacity_bps=100_000_000,
        snmp_enabled=True,
        snmp_target_ip="192.0.2.10",
        snmp_version=SNMPVersion.v2c,
        snmp_credential_id=resolved_credential_id,
        selected_if_index=1,
        monitoring_disabled=monitoring_disabled,
    )
    db.add(wan_link)
    db.commit()
    return wan_link


@pytest.fixture()
def worker_test_session(monkeypatch):
    """Point the worker module's SessionLocal at an isolated in-memory DB
    for the duration of the test, instead of the real dev database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(worker_module, "SessionLocal", session_factory)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_failed_snmp_poll_still_records_attempt_time(worker_test_session, monkeypatch):
    wan_link = _make_snmp_wan_link(worker_test_session)

    async def _raise(*args, **kwargs):
        raise TimeoutError("simulated SNMP timeout")

    monkeypatch.setattr(worker_module.snmp_client, "poll_interface", _raise)

    await worker_module.poll_snmp_for_wan_link(wan_link.id)

    state = worker_test_session.query(PollState).filter(PollState.wan_link_id == wan_link.id).first()
    assert state is not None
    assert state.last_snmp_poll_at is not None


@pytest.mark.asyncio
async def test_failed_snmp_poll_does_not_touch_wan_down_alert(worker_test_session, monkeypatch):
    from app.models import Alert

    wan_link = _make_snmp_wan_link(worker_test_session)

    async def _raise(*args, **kwargs):
        raise TimeoutError("simulated SNMP timeout")

    monkeypatch.setattr(worker_module.snmp_client, "poll_interface", _raise)

    await worker_module.poll_snmp_for_wan_link(wan_link.id)

    # SNMP failures must never create/close a wan_down alert — that's
    # exclusively ICMP's signal, since the two are independently scheduled.
    alerts = worker_test_session.query(Alert).filter(Alert.wan_link_id == wan_link.id).all()
    assert alerts == []


@pytest.mark.asyncio
async def test_snmp_failure_clears_stale_counter_baseline(worker_test_session, monkeypatch):
    wan_link = _make_snmp_wan_link(worker_test_session)
    state = worker_module._get_or_create_poll_state(worker_test_session, wan_link)
    state.last_in_octets = 123_456
    state.last_out_octets = 654_321
    worker_test_session.commit()

    async def _raise(*args, **kwargs):
        raise TimeoutError("simulated SNMP timeout")

    monkeypatch.setattr(worker_module.snmp_client, "poll_interface", _raise)
    await worker_module.poll_snmp_for_wan_link(wan_link.id)

    worker_test_session.refresh(state)
    assert state.last_in_octets is None
    assert state.last_out_octets is None


@pytest.mark.asyncio
async def test_snmp_failure_then_recovery_establishes_fresh_baseline_without_inflated_rate(worker_test_session, monkeypatch):
    from app.models import Measurement

    wan_link = _make_snmp_wan_link(worker_test_session)
    state = worker_module._get_or_create_poll_state(worker_test_session, wan_link)
    # Old, now-stale counters from before the outage.
    state.last_in_octets = 1_000_000
    state.last_out_octets = 1_000_000
    worker_test_session.commit()

    async def _raise(*args, **kwargs):
        raise TimeoutError("simulated SNMP timeout")

    monkeypatch.setattr(worker_module.snmp_client, "poll_interface", _raise)
    await worker_module.poll_snmp_for_wan_link(wan_link.id)

    # Device comes back with much higher counters after the outage — if the
    # stale baseline were used, this would compute a huge/inflated rate.
    async def _succeed(*args, **kwargs):
        return InterfaceCounters(if_index=1, in_octets=50_000_000, out_octets=50_000_000, oper_status="up", used_high_capacity_counters=True)

    monkeypatch.setattr(worker_module.snmp_client, "poll_interface", _succeed)
    await worker_module.poll_snmp_for_wan_link(wan_link.id)

    # First poll after recovery only establishes the new baseline — no rate
    # can be computed yet (no prior sample to diff against), so no
    # Measurement row should exist, and definitely no bogus 49M-byte-delta rate.
    measurements = worker_test_session.query(Measurement).filter(Measurement.wan_link_id == wan_link.id).all()
    assert measurements == []

    worker_test_session.refresh(state)
    assert state.last_in_octets == 50_000_000
    assert state.last_out_octets == 50_000_000


@pytest.mark.asyncio
async def test_missing_credential_records_failed_attempt(worker_test_session):
    wan_link = _make_snmp_wan_link(worker_test_session, credential_id=None)

    await worker_module.poll_snmp_for_wan_link(wan_link.id)

    state = worker_test_session.query(PollState).filter(PollState.wan_link_id == wan_link.id).first()
    assert state is not None
    assert state.last_snmp_poll_at is not None


@pytest.mark.asyncio
async def test_credential_decryption_failure_records_failed_attempt(worker_test_session):
    wan_link = _make_snmp_wan_link(worker_test_session, encrypted_secret=b"not-a-valid-fernet-token")

    await worker_module.poll_snmp_for_wan_link(wan_link.id)

    state = worker_test_session.query(PollState).filter(PollState.wan_link_id == wan_link.id).first()
    assert state is not None
    assert state.last_snmp_poll_at is not None


@pytest.mark.asyncio
async def test_monitoring_disabled_wan_is_skipped_by_snmp_poll(worker_test_session, monkeypatch):
    wan_link = _make_snmp_wan_link(worker_test_session, monitoring_disabled=True)

    called = False

    async def _fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("should never be called for a monitoring_disabled link")

    monkeypatch.setattr(worker_module.snmp_client, "poll_interface", _fail_if_called)
    await worker_module.poll_snmp_for_wan_link(wan_link.id)

    assert called is False
    state = worker_test_session.query(PollState).filter(PollState.wan_link_id == wan_link.id).first()
    assert state is None  # never even touched


@pytest.mark.asyncio
async def test_monitoring_disabled_wan_is_skipped_by_icmp_poll(worker_test_session, monkeypatch):
    wan_link = _make_snmp_wan_link(worker_test_session, monitoring_disabled=True)
    wan_link.icmp_enabled = True
    wan_link.icmp_target_ip = "192.0.2.10"
    worker_test_session.commit()

    called = False

    async def _fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("should never be called for a monitoring_disabled link")

    monkeypatch.setattr(worker_module.icmp_client, "ping", _fail_if_called)
    await worker_module.poll_icmp_for_wan_link(wan_link.id)

    assert called is False


@pytest.mark.asyncio
async def test_tick_does_not_schedule_monitoring_disabled_wan(worker_test_session, monkeypatch):
    wan_link = _make_snmp_wan_link(worker_test_session, monitoring_disabled=True)
    wan_link.icmp_enabled = True
    wan_link.icmp_target_ip = "192.0.2.10"
    worker_test_session.commit()

    spawned = []

    def _record_spawn(coro):
        spawned.append(coro)
        coro.close()  # avoid "coroutine was never awaited" warnings

    monkeypatch.setattr(worker_module, "_spawn", _record_spawn)
    await worker_module._tick()

    assert spawned == []
