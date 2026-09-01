"""Pure traffic-rate and utilisation math.

SNMP octet counters are cumulative — never display a raw counter as a rate.
Everything here derives bits-per-second from the delta between two counter
samples divided by elapsed time, and handles counter resets/wraps safely.
"""
from dataclasses import dataclass

COUNTER32_MAX = 2**32 - 1
COUNTER64_MAX = 2**64 - 1


@dataclass
class RateResult:
    bytes_delta: int
    bps: float


def counter_delta(previous: int, current: int, *, is_64_bit: bool) -> int:
    """Delta between two cumulative counter samples, handling wrap-around.

    A counter "reset" (device reboot, counter cleared, or the previous value
    simply being larger than the current one for a reason that isn't a
    single wrap) is treated the same as a wrap for 64-bit counters — the
    36-quintillion range makes a genuine wrap effectively impossible within
    a normal polling interval, so a decrease is always a reset there. For
    32-bit counters a real wrap is achievable on fast links, so we assume
    wrap rather than reset.
    """
    if current >= previous:
        return current - previous

    if is_64_bit:
        return current  # treat as a reset; current value is "since reset"

    return (COUNTER32_MAX - previous) + current + 1


def calculate_rate(previous_octets: int, current_octets: int, elapsed_seconds: float, *, is_64_bit: bool) -> RateResult:
    if elapsed_seconds <= 0:
        raise ValueError("elapsed_seconds must be positive")

    delta = counter_delta(previous_octets, current_octets, is_64_bit=is_64_bit)
    bps = (delta * 8) / elapsed_seconds
    return RateResult(bytes_delta=delta, bps=bps)


def total_throughput_bps(rx_bps: float, tx_bps: float) -> float:
    return rx_bps + tx_bps


def utilisation_percent(total_bps: float, circuit_capacity_bps: int) -> float:
    if circuit_capacity_bps <= 0:
        raise ValueError("circuit_capacity_bps must be positive")
    return (total_bps / circuit_capacity_bps) * 100.0
