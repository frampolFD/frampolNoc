import pytest

from app.monitoring.calculations import (
    COUNTER32_MAX,
    calculate_rate,
    counter_delta,
    total_throughput_bps,
    utilisation_percent,
)


def test_counter_delta_normal_increase():
    assert counter_delta(1000, 1500, is_64_bit=False) == 500


def test_counter_delta_32bit_wrap():
    previous = COUNTER32_MAX - 100
    current = 50
    assert counter_delta(previous, current, is_64_bit=False) == 151


def test_counter_delta_64bit_reset_treated_as_since_reset():
    # A 64-bit counter that goes backwards means the device reset/rebooted;
    # a real wrap of a 64-bit counter is not realistic within a poll interval.
    assert counter_delta(10_000_000, 500, is_64_bit=True) == 500


def test_calculate_rate_basic():
    result = calculate_rate(1_000_000, 2_000_000, elapsed_seconds=60, is_64_bit=True)
    assert result.bytes_delta == 1_000_000
    assert result.bps == pytest.approx((1_000_000 * 8) / 60)


def test_calculate_rate_rejects_non_positive_elapsed():
    with pytest.raises(ValueError):
        calculate_rate(100, 200, elapsed_seconds=0, is_64_bit=True)


def test_total_throughput():
    assert total_throughput_bps(30_000_000, 5_000_000) == 35_000_000


def test_utilisation_percent():
    # 50 Mbps of traffic on a 100 Mbps circuit = 50%
    assert utilisation_percent(50_000_000, 100_000_000) == pytest.approx(50.0)


def test_utilisation_percent_rejects_non_positive_capacity():
    with pytest.raises(ValueError):
        utilisation_percent(1000, 0)
