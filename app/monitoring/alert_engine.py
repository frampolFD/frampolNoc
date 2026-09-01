"""Pure alert decision logic.

Each function takes the current measurement plus whatever bit of state is
needed to detect a *transition* (an alert already open, or a breach-start
timestamp) and returns a decision — open a new alert, close an existing one,
or do nothing. No database access happens here, which is what makes this
testable without wiring up SQLAlchemy sessions or a live poller.
"""
import enum
from dataclasses import dataclass
from datetime import datetime


class AlertAction(str, enum.Enum):
    none = "none"
    open = "open"
    close = "close"


@dataclass
class AlertDecision:
    action: AlertAction
    message: str | None = None


def evaluate_availability(is_reachable: bool, alert_currently_open: bool) -> AlertDecision:
    if not is_reachable and not alert_currently_open:
        return AlertDecision(AlertAction.open, "WAN is unreachable (ICMP: 100% packet loss)")
    if is_reachable and alert_currently_open:
        return AlertDecision(AlertAction.close, "WAN has recovered")
    return AlertDecision(AlertAction.none)


def evaluate_high_latency(latency_ms: float | None, threshold_ms: float, alert_currently_open: bool) -> AlertDecision:
    if latency_ms is None:
        return AlertDecision(AlertAction.none)
    if latency_ms > threshold_ms and not alert_currently_open:
        return AlertDecision(AlertAction.open, f"Latency {latency_ms:.1f}ms exceeds threshold {threshold_ms:.1f}ms")
    if latency_ms <= threshold_ms and alert_currently_open:
        return AlertDecision(AlertAction.close, "Latency back within threshold")
    return AlertDecision(AlertAction.none)


def evaluate_packet_loss(loss_percent: float | None, threshold_percent: float, alert_currently_open: bool) -> AlertDecision:
    if loss_percent is None:
        return AlertDecision(AlertAction.none)
    if loss_percent > threshold_percent and not alert_currently_open:
        return AlertDecision(AlertAction.open, f"Packet loss {loss_percent:.1f}% exceeds threshold {threshold_percent:.1f}%")
    if loss_percent <= threshold_percent and alert_currently_open:
        return AlertDecision(AlertAction.close, "Packet loss back within threshold")
    return AlertDecision(AlertAction.none)


@dataclass
class SustainedUtilisationResult:
    decision: AlertDecision
    new_breach_since: datetime | None


def evaluate_sustained_utilisation(
    utilisation_percent: float | None,
    threshold_percent: float,
    duration_seconds: int,
    breach_since: datetime | None,
    now: datetime,
    alert_currently_open: bool,
) -> SustainedUtilisationResult:
    if utilisation_percent is None:
        return SustainedUtilisationResult(AlertDecision(AlertAction.none), breach_since)

    if utilisation_percent <= threshold_percent:
        decision = AlertDecision(AlertAction.close, "Utilisation back within threshold") if alert_currently_open else AlertDecision(AlertAction.none)
        return SustainedUtilisationResult(decision, None)

    # Above threshold.
    if breach_since is None:
        breach_since = now

    breached_for = (now - breach_since).total_seconds()
    if breached_for >= duration_seconds and not alert_currently_open:
        message = f"Utilisation {utilisation_percent:.1f}% sustained above {threshold_percent:.1f}% for {int(breached_for)}s"
        return SustainedUtilisationResult(AlertDecision(AlertAction.open, message), breach_since)

    return SustainedUtilisationResult(AlertDecision(AlertAction.none), breach_since)
