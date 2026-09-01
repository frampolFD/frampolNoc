"""Real ICMP monitoring via the operating system's ping utility.

Shelling out to the OS `ping` (rather than crafting raw ICMP sockets in
Python) avoids needing administrator/root privileges on Windows while still
sending genuine ICMP echo requests over the network — this is real ping
traffic, not a simulation.
"""
import asyncio
import platform
import re
from dataclasses import dataclass, field

_TIME_RE = re.compile(r"time[=<]?\s*([\d.]+)\s*ms", re.IGNORECASE)
_LOSS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:packet )?loss", re.IGNORECASE)


@dataclass
class ICMPResult:
    reachable: bool
    packets_sent: int
    packets_received: int
    packet_loss_percent: float
    latency_ms: float | None
    jitter_ms: float | None
    raw_samples_ms: list[float] = field(default_factory=list)
    error: str | None = None


def _build_command(host: str, count: int, timeout_seconds: int) -> list[str]:
    if platform.system().lower() == "windows":
        return ["ping", "-n", str(count), "-w", str(int(timeout_seconds * 1000)), host]
    return ["ping", "-c", str(count), "-W", str(int(timeout_seconds)), host]


def _parse(output: str, count: int) -> ICMPResult:
    samples = [float(m) for m in _TIME_RE.findall(output)]
    loss_match = _LOSS_RE.search(output)
    if loss_match:
        loss_percent = float(loss_match.group(1))
    else:
        loss_percent = 0.0 if samples else 100.0

    jitter_ms = None
    if len(samples) >= 2:
        diffs = [abs(samples[i] - samples[i - 1]) for i in range(1, len(samples))]
        jitter_ms = sum(diffs) / len(diffs)

    latency_ms = (sum(samples) / len(samples)) if samples else None

    return ICMPResult(
        reachable=len(samples) > 0,
        packets_sent=count,
        packets_received=len(samples),
        packet_loss_percent=loss_percent,
        latency_ms=latency_ms,
        jitter_ms=jitter_ms,
        raw_samples_ms=samples,
    )


async def ping(host: str, count: int = 4, timeout_seconds: int = 2) -> ICMPResult:
    """Send `count` real ICMP echo requests to `host` and summarize the result."""
    command = _build_command(host, count, timeout_seconds)
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return ICMPResult(False, count, 0, 100.0, None, None, [], error="system ping utility not found")

    overall_timeout = timeout_seconds * count + 5
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=overall_timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return ICMPResult(False, count, 0, 100.0, None, None, [], error="ping process timed out")

    output = stdout_bytes.decode(errors="replace") + "\n" + stderr_bytes.decode(errors="replace")
    return _parse(output, count)
