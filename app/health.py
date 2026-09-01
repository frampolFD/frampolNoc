from sqlalchemy.orm import Session

from app.models import Alert, Measurement, MonitoringStatus, PollState, WANLink
from app.schemas import LatestMetrics


def compute_monitoring_status(icmp_enabled: bool, snmp_enabled: bool) -> MonitoringStatus:
    if icmp_enabled and snmp_enabled:
        return MonitoringStatus.fully_monitored
    if icmp_enabled:
        return MonitoringStatus.icmp_only
    if snmp_enabled:
        return MonitoringStatus.snmp_only
    return MonitoringStatus.not_configured


def latest_metrics(db: Session, wan_link: WANLink) -> LatestMetrics:
    latest: Measurement | None = (
        db.query(Measurement)
        .filter(Measurement.wan_link_id == wan_link.id)
        .order_by(Measurement.timestamp.desc())
        .first()
    )
    poll_state: PollState | None = wan_link.poll_state

    if not latest:
        return LatestMetrics(
            last_snmp_poll_at=poll_state.last_snmp_poll_at if poll_state else None,
            last_icmp_poll_at=poll_state.last_icmp_poll_at if poll_state else None,
        )

    return LatestMetrics(
        rx_bps=latest.rx_bps,
        tx_bps=latest.tx_bps,
        total_bps=latest.total_bps,
        utilisation_percent=latest.utilisation_percent,
        latency_ms=latest.latency_ms,
        packet_loss_percent=latest.packet_loss_percent,
        jitter_ms=latest.jitter_ms,
        availability=latest.availability,
        last_snmp_poll_at=poll_state.last_snmp_poll_at if poll_state else None,
        last_icmp_poll_at=poll_state.last_icmp_poll_at if poll_state else None,
    )


def compute_health(db: Session, wan_link: WANLink) -> str:
    if wan_link.monitoring_status == MonitoringStatus.not_configured:
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
