from datetime import datetime, timedelta, timezone

from app.health import compute_health, compute_monitoring_status, latest_metrics
from app.models import Branch, City, Customer, Measurement, MonitoringStatus, WANLink


def _make_wan_link(db, **overrides) -> WANLink:
    customer = Customer(name="Test Customer")
    db.add(customer)
    db.flush()
    city = City(name="Test City", province="Test Province", country_code="ZW")
    db.add(city)
    db.flush()
    branch = Branch(customer_id=customer.id, city_id=city.id, name="Test Branch", latitude=0.0, longitude=0.0)
    db.add(branch)
    db.flush()
    wan_link = WANLink(
        branch_id=branch.id,
        name_generated="Test WAN",
        circuit_capacity_bps=100_000_000,
        **overrides,
    )
    db.add(wan_link)
    db.flush()
    return wan_link


# --- compute_monitoring_status ---


def test_monitoring_status_not_configured_when_nothing_enabled():
    assert compute_monitoring_status(False, False) == MonitoringStatus.not_configured


def test_monitoring_status_icmp_only():
    assert compute_monitoring_status(True, False) == MonitoringStatus.icmp_only


def test_monitoring_status_snmp_only():
    assert compute_monitoring_status(False, True) == MonitoringStatus.snmp_only


def test_monitoring_status_fully_monitored():
    assert compute_monitoring_status(True, True) == MonitoringStatus.fully_monitored


def test_monitoring_status_disabled_overrides_enabled_flags():
    # "Deliberately disabled" must win even if icmp/snmp toggles are still
    # set — it's a distinct state from "not configured yet".
    assert compute_monitoring_status(True, True, monitoring_disabled=True) == MonitoringStatus.monitoring_disabled
    assert compute_monitoring_status(False, False, monitoring_disabled=True) == MonitoringStatus.monitoring_disabled


# --- latest_metrics ---


def test_latest_metrics_snmp_survives_a_newer_icmp_poll(db_session):
    wan_link = _make_wan_link(db_session)
    now = datetime.now(timezone.utc)

    db_session.add(
        Measurement(
            wan_link_id=wan_link.id,
            timestamp=now - timedelta(minutes=1),
            rx_bps=30_000_000.0,
            tx_bps=5_000_000.0,
            total_bps=35_000_000.0,
            utilisation_percent=30.0,
        )
    )
    db_session.add(
        Measurement(
            wan_link_id=wan_link.id,
            timestamp=now,
            latency_ms=12.0,
            packet_loss_percent=0.0,
            jitter_ms=1.0,
            availability=True,
        )
    )
    db_session.flush()

    result = latest_metrics(db_session, wan_link)

    assert result.rx_bps == 30_000_000.0
    assert result.tx_bps == 5_000_000.0
    assert result.utilisation_percent == 30.0
    assert result.latency_ms == 12.0
    assert result.availability is True


def test_latest_metrics_icmp_survives_a_newer_snmp_poll(db_session):
    wan_link = _make_wan_link(db_session)
    now = datetime.now(timezone.utc)

    db_session.add(
        Measurement(
            wan_link_id=wan_link.id,
            timestamp=now - timedelta(minutes=1),
            latency_ms=15.0,
            packet_loss_percent=2.0,
            jitter_ms=0.5,
            availability=True,
        )
    )
    db_session.add(
        Measurement(
            wan_link_id=wan_link.id,
            timestamp=now,
            rx_bps=40_000_000.0,
            tx_bps=8_000_000.0,
            total_bps=48_000_000.0,
            utilisation_percent=40.0,
        )
    )
    db_session.flush()

    result = latest_metrics(db_session, wan_link)

    assert result.latency_ms == 15.0
    assert result.packet_loss_percent == 2.0
    assert result.availability is True
    assert result.rx_bps == 40_000_000.0
    assert result.utilisation_percent == 40.0


def test_latest_metrics_no_measurements_yet(db_session):
    wan_link = _make_wan_link(db_session)
    result = latest_metrics(db_session, wan_link)
    assert result.rx_bps is None
    assert result.latency_ms is None
    assert result.availability is None


# --- compute_health ---


def test_health_unknown_when_not_configured(db_session):
    wan_link = _make_wan_link(db_session, monitoring_status=MonitoringStatus.not_configured)
    assert compute_health(db_session, wan_link) == "unknown"


def test_health_unknown_when_monitoring_disabled(db_session):
    wan_link = _make_wan_link(db_session, monitoring_status=MonitoringStatus.monitoring_disabled, monitoring_disabled=True)
    assert compute_health(db_session, wan_link) == "unknown"
