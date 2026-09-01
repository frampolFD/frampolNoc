from datetime import datetime, timedelta, timezone

from app.monitoring.alert_engine import (
    AlertAction,
    evaluate_availability,
    evaluate_high_latency,
    evaluate_packet_loss,
    evaluate_sustained_utilisation,
)


def test_availability_opens_on_unreachable():
    decision = evaluate_availability(is_reachable=False, alert_currently_open=False)
    assert decision.action == AlertAction.open


def test_availability_does_not_reopen_while_already_down():
    decision = evaluate_availability(is_reachable=False, alert_currently_open=True)
    assert decision.action == AlertAction.none


def test_availability_closes_on_recovery():
    decision = evaluate_availability(is_reachable=True, alert_currently_open=True)
    assert decision.action == AlertAction.close


def test_availability_noop_when_up_and_no_alert():
    decision = evaluate_availability(is_reachable=True, alert_currently_open=False)
    assert decision.action == AlertAction.none


def test_high_latency_opens_above_threshold():
    decision = evaluate_high_latency(200.0, threshold_ms=150.0, alert_currently_open=False)
    assert decision.action == AlertAction.open


def test_high_latency_closes_below_threshold():
    decision = evaluate_high_latency(100.0, threshold_ms=150.0, alert_currently_open=True)
    assert decision.action == AlertAction.close


def test_high_latency_ignores_missing_sample():
    decision = evaluate_high_latency(None, threshold_ms=150.0, alert_currently_open=False)
    assert decision.action == AlertAction.none


def test_packet_loss_opens_and_closes():
    assert evaluate_packet_loss(20.0, 10.0, False).action == AlertAction.open
    assert evaluate_packet_loss(5.0, 10.0, True).action == AlertAction.close
    assert evaluate_packet_loss(5.0, 10.0, False).action == AlertAction.none


def test_sustained_utilisation_does_not_fire_before_duration_elapsed():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = evaluate_sustained_utilisation(
        utilisation_percent=95.0,
        threshold_percent=90.0,
        duration_seconds=600,
        breach_since=now,
        now=now + timedelta(seconds=60),
        alert_currently_open=False,
    )
    assert result.decision.action == AlertAction.none
    assert result.new_breach_since == now


def test_sustained_utilisation_fires_after_duration_elapsed():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = evaluate_sustained_utilisation(
        utilisation_percent=95.0,
        threshold_percent=90.0,
        duration_seconds=600,
        breach_since=now,
        now=now + timedelta(seconds=601),
        alert_currently_open=False,
    )
    assert result.decision.action == AlertAction.open


def test_sustained_utilisation_starts_breach_clock_on_first_sample_over_threshold():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = evaluate_sustained_utilisation(
        utilisation_percent=95.0,
        threshold_percent=90.0,
        duration_seconds=600,
        breach_since=None,
        now=now,
        alert_currently_open=False,
    )
    assert result.new_breach_since == now
    assert result.decision.action == AlertAction.none


def test_sustained_utilisation_resets_and_closes_when_back_under_threshold():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = evaluate_sustained_utilisation(
        utilisation_percent=50.0,
        threshold_percent=90.0,
        duration_seconds=600,
        breach_since=now - timedelta(seconds=700),
        now=now,
        alert_currently_open=True,
    )
    assert result.decision.action == AlertAction.close
    assert result.new_breach_since is None
