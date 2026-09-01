import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.database import Base
from app.models import Branch, City, Customer, PollState, SNMPCredential, SNMPVersion, WANLink
from app.monitoring import worker as worker_module
from app.security import encrypt_secret


def _make_snmp_wan_link(db):
    customer = Customer(name="Test Customer")
    db.add(customer)
    db.flush()
    city = City(customer_id=customer.id, name="Test City")
    db.add(city)
    db.flush()
    branch = Branch(customer_id=customer.id, city_id=city.id, name="Test Branch", latitude=0.0, longitude=0.0)
    db.add(branch)
    db.flush()

    credential = SNMPCredential(name="Test Cred", version=SNMPVersion.v2c, encrypted_secret=encrypt_secret("public"))
    db.add(credential)
    db.flush()

    wan_link = WANLink(
        branch_id=branch.id,
        name_generated="Test WAN",
        circuit_capacity_bps=100_000_000,
        snmp_enabled=True,
        snmp_target_ip="192.0.2.10",
        snmp_version=SNMPVersion.v2c,
        snmp_credential_id=credential.id,
        selected_if_index=1,
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
