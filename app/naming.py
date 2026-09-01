"""Generated WAN link naming.

Engineers never type the full sensor name — it's assembled from structured
fields. Example target format:

PCD - Harare - New Ardbennie - FortiGate 100F - Frampol LTZ - (169.239.24.126) - 100Mbps
"""


def format_capacity(circuit_capacity_bps: int) -> str:
    mbps = circuit_capacity_bps / 1_000_000
    if mbps >= 1000 and mbps % 1000 == 0:
        return f"{int(mbps / 1000)}Gbps"
    if mbps == int(mbps):
        return f"{int(mbps)}Mbps"
    return f"{mbps:.1f}Mbps"


def generate_wan_name(
    *,
    customer_name: str,
    city_name: str,
    branch_name: str,
    device_model: str | None,
    isp_name: str | None,
    public_ip: str | None,
    circuit_capacity_bps: int | None,
) -> str:
    """Matches the documented template exactly:

    PCD - Harare - New Ardbennie - FortiGate 100F - Frampol LTZ - (169.239.24.126) - 100Mbps

    i.e. Customer - City - Branch - DeviceModel - ISP - (PublicIP) - Capacity.
    Suburb is part of the navigation hierarchy but is deliberately not part
    of the generated name (the branch name already identifies the location).

    circuit_capacity_bps may be absent for an inventory-only/not-yet-
    configured link (see WANLink.circuit_capacity_bps) — the capacity
    segment is simply omitted rather than showing a fabricated "0Mbps".
    """
    parts: list[str] = [customer_name, city_name, branch_name]
    if device_model:
        parts.append(device_model)
    if isp_name:
        parts.append(isp_name)
    if public_ip:
        parts.append(f"({public_ip})")
    if circuit_capacity_bps is not None:
        parts.append(format_capacity(circuit_capacity_bps))
    return " - ".join(parts)
