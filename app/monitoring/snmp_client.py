"""Real SNMP interface discovery and polling using standard IF-MIB / IP-MIB objects.

MVP supports SNMP v2c only. The module is structured so SNMP v3 (UsmUserData
auth/priv) can be added later by extending `_auth_data()` — callers only ever
deal with `SNMPCredential` records, never raw protocol details.

Everything here uses pysnmp's classic synchronous hlapi, run inside a worker
thread (`asyncio.to_thread`) so it never blocks the FastAPI event loop or the
background poller's own event loop.
"""
import asyncio
from dataclasses import dataclass, field

from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    bulkCmd,
    getCmd,
)

# IF-MIB (RFC 2863) — base ifTable
IF_INDEX = "1.3.6.1.2.1.2.2.1.1"
IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
IF_SPEED = "1.3.6.1.2.1.2.2.1.5"
IF_PHYS_ADDRESS = "1.3.6.1.2.1.2.2.1.6"
IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"
IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"
IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"

# IF-MIB ifXTable — high-capacity / extended columns
IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
IF_HC_IN_OCTETS = "1.3.6.1.2.1.31.1.1.1.6"
IF_HC_OUT_OCTETS = "1.3.6.1.2.1.31.1.1.1.10"
IF_HIGH_SPEED = "1.3.6.1.2.1.31.1.1.1.15"  # Mbps
IF_ALIAS = "1.3.6.1.2.1.31.1.1.1.18"

# IP-MIB — maps IP addresses to ifIndex
IP_AD_ENT_IF_INDEX = "1.3.6.1.2.1.4.20.1.2"

ADMIN_STATUS_LABELS = {1: "up", 2: "down", 3: "testing"}
OPER_STATUS_LABELS = {1: "up", 2: "down", 3: "testing", 4: "unknown", 5: "dormant", 6: "notPresent", 7: "lowerLayerDown"}


class SNMPError(Exception):
    pass


@dataclass
class DiscoveredInterface:
    if_index: int
    name: str | None = None
    description: str | None = None
    alias: str | None = None
    ip_address: str | None = None
    speed_bps: int | None = None
    mac_address: str | None = None
    admin_status: str | None = None
    oper_status: str | None = None


@dataclass
class InterfaceCounters:
    if_index: int
    in_octets: int | None
    out_octets: int | None
    oper_status: str | None
    used_high_capacity_counters: bool


def _auth_data(version: str, community: str):
    if version == "v2c":
        return CommunityData(community, mpModel=1)
    raise SNMPError(f"SNMP version '{version}' is not yet implemented for polling")


def _walk_column_sync(target_ip: str, port: int, auth, base_oid: str, timeout: int, retries: int) -> dict[int, object]:
    """Walk a single MIB table column and return {last_oid_index: value}."""
    engine = SnmpEngine()
    transport = UdpTransportTarget((target_ip, port), timeout=timeout, retries=retries)
    results: dict[int, object] = {}

    for errorIndication, errorStatus, errorIndex, varBinds in bulkCmd(
        engine,
        auth,
        transport,
        ContextData(),
        0,
        25,
        ObjectType(ObjectIdentity(base_oid)),
        lexicographicMode=False,
    ):
        if errorIndication:
            raise SNMPError(str(errorIndication))
        if errorStatus:
            raise SNMPError(f"{errorStatus.prettyPrint()} at {errorIndex}")

        for varBind in varBinds:
            oid, value = varBind
            oid_str = str(oid)
            if not oid_str.startswith(base_oid + "."):
                continue
            suffix = oid_str[len(base_oid) + 1 :]
            # Table index for ifTable/ifXTable columns is just the ifIndex.
            # For ipAdEntIfIndex the index is the dotted IP address itself.
            index_key = suffix
            results[index_key] = value

    return results


def _extract_ipv4_from_index_suffix(suffix: str) -> str | None:
    """Extract the IPv4 address from an ipAddrTable row's OID index suffix.

    ipAdEntAddr — this table's INDEX — is a fixed 4-octet IpAddress per
    RFC 1213, so a compliant row's OID suffix is exactly `A.B.C.D`. A
    since-reported regression (not reproduced against the one live device
    this codebase has been tested against, but documented in the bug
    report that prompted this fix) showed some Fortinet firmware appending
    exactly ONE extra numeric sub-identifier after those four octets, e.g.
    `41.79.31.22.1` — a device-specific disambiguation index, not part of
    the address. We accept only that one documented shape (4 octets plus
    at most one trailing integer) and extract just the four octets from
    it. Anything else — too few components, a non-numeric or out-of-range
    octet, or more than one trailing component — has no verified meaning
    here, so it is rejected outright rather than guessed at (blindly
    keeping "the first four components" no matter how many more follow
    would risk silently mangling data from a table this code doesn't
    actually understand).
    """
    parts = suffix.split(".")
    if len(parts) not in (4, 5):
        return None
    try:
        octets = [int(p) for p in parts[:4]]
    except ValueError:
        return None
    if any(o < 0 or o > 255 for o in octets):
        return None
    if len(parts) == 5 and not parts[4].isdigit():
        # The only supported trailing shape is a single plain non-negative
        # integer disambiguator; anything else past the four octets is an
        # arbitrary/malformed suffix, not this documented quirk.
        return None
    return ".".join(str(o) for o in octets)


def parse_ip_index_map(raw_rows: dict[str, object]) -> dict[str, int]:
    """Pure merge of walked IP-MIB ipAdEntIfIndex rows into {ip_address: ifIndex}.

    `raw_rows` is {oid_index_suffix: ifIndex_value} as produced by
    `_walk_column_sync` for the IP_AD_ENT_IF_INDEX column. Rows whose
    suffix doesn't resolve to a valid IPv4 address, or whose value isn't a
    real ifIndex integer, are safely skipped rather than guessed at.
    """
    ip_to_index: dict[str, int] = {}
    for suffix, value in raw_rows.items():
        ip_address = _extract_ipv4_from_index_suffix(str(suffix))
        if ip_address is None:
            continue
        try:
            ip_to_index[ip_address] = int(value)
        except (TypeError, ValueError):
            continue
    return ip_to_index


def _walk_ip_map_sync(target_ip: str, port: int, auth, timeout: int, retries: int) -> dict[str, int]:
    """Returns {ip_address: ifIndex} discovered from IP-MIB ipAddrTable."""
    raw_rows = _walk_column_sync(target_ip, port, auth, IP_AD_ENT_IF_INDEX, timeout, retries)
    return parse_ip_index_map(raw_rows)


def build_interfaces(
    descr: dict[str, object],
    speed: dict[str, object],
    admin: dict[str, object],
    oper: dict[str, object],
    mac: dict[str, object],
    name: dict[str, object],
    alias: dict[str, object],
    high_speed: dict[str, object],
    index_to_ip: dict[int, str],
) -> list[DiscoveredInterface]:
    """Pure merge of walked IF-MIB/IP-MIB columns into interface records.

    Kept free of any network I/O so the discovery merge logic (HC-counter
    fallback, MAC formatting, status label mapping, IP matching) can be unit
    tested with synthetic data — this is the project's development/test
    adapter for SNMP discovery, used only by the automated test suite. It
    never talks to the network and its output must never be shown to an
    engineer as if it came from a real device.
    """
    interfaces: list[DiscoveredInterface] = []
    for index_key in descr.keys():
        if_index = int(index_key)

        speed_bps = None
        if index_key in high_speed:
            speed_bps = int(high_speed[index_key]) * 1_000_000  # ifHighSpeed is in Mbps
        elif index_key in speed:
            speed_bps = int(speed[index_key])

        mac_raw = mac.get(index_key)
        mac_str = None
        if mac_raw is not None:
            hex_bytes = bytes(mac_raw)
            if hex_bytes:
                mac_str = ":".join(f"{b:02x}" for b in hex_bytes)

        interfaces.append(
            DiscoveredInterface(
                if_index=if_index,
                name=str(name[index_key]) if index_key in name else None,
                description=str(descr[index_key]),
                alias=str(alias[index_key]) if index_key in alias and str(alias[index_key]) else None,
                ip_address=index_to_ip.get(if_index),
                speed_bps=speed_bps,
                mac_address=mac_str,
                admin_status=ADMIN_STATUS_LABELS.get(int(admin[index_key]), "unknown") if index_key in admin else None,
                oper_status=OPER_STATUS_LABELS.get(int(oper[index_key]), "unknown") if index_key in oper else None,
            )
        )

    interfaces.sort(key=lambda i: i.if_index)
    return interfaces


def _discover_sync(target_ip: str, version: str, community: str, port: int, timeout: int, retries: int) -> list[DiscoveredInterface]:
    auth = _auth_data(version, community)

    descr = _walk_column_sync(target_ip, port, auth, IF_DESCR, timeout, retries)
    if not descr:
        raise SNMPError("Device returned no interfaces (empty ifTable) — check target IP, community and reachability")

    speed = _walk_column_sync(target_ip, port, auth, IF_SPEED, timeout, retries)
    admin = _walk_column_sync(target_ip, port, auth, IF_ADMIN_STATUS, timeout, retries)
    oper = _walk_column_sync(target_ip, port, auth, IF_OPER_STATUS, timeout, retries)
    mac = _walk_column_sync(target_ip, port, auth, IF_PHYS_ADDRESS, timeout, retries)

    # ifXTable columns are optional extensions; devices that don't support
    # them simply return an empty walk here, and we fall back to ifTable data.
    try:
        name = _walk_column_sync(target_ip, port, auth, IF_NAME, timeout, retries)
    except SNMPError:
        name = {}
    try:
        alias = _walk_column_sync(target_ip, port, auth, IF_ALIAS, timeout, retries)
    except SNMPError:
        alias = {}
    try:
        high_speed = _walk_column_sync(target_ip, port, auth, IF_HIGH_SPEED, timeout, retries)
    except SNMPError:
        high_speed = {}

    try:
        ip_to_index = _walk_ip_map_sync(target_ip, port, auth, timeout, retries)
    except SNMPError:
        ip_to_index = {}
    index_to_ip: dict[int, str] = {}
    for ip, idx in ip_to_index.items():
        index_to_ip.setdefault(idx, ip)

    return build_interfaces(descr, speed, admin, oper, mac, name, alias, high_speed, index_to_ip)


def _poll_sync(target_ip: str, version: str, community: str, if_index: int, port: int, timeout: int, retries: int) -> InterfaceCounters:
    auth = _auth_data(version, community)
    engine = SnmpEngine()
    transport = UdpTransportTarget((target_ip, port), timeout=timeout, retries=retries)

    var_binds = [
        ObjectType(ObjectIdentity(f"{IF_HC_IN_OCTETS}.{if_index}")),
        ObjectType(ObjectIdentity(f"{IF_HC_OUT_OCTETS}.{if_index}")),
        ObjectType(ObjectIdentity(f"{IF_IN_OCTETS}.{if_index}")),
        ObjectType(ObjectIdentity(f"{IF_OUT_OCTETS}.{if_index}")),
        ObjectType(ObjectIdentity(f"{IF_OPER_STATUS}.{if_index}")),
    ]

    iterator = getCmd(engine, auth, transport, ContextData(), *var_binds)
    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication:
        raise SNMPError(str(errorIndication))
    if errorStatus:
        raise SNMPError(f"{errorStatus.prettyPrint()} at {errorIndex}")

    def _as_int_or_none(v):
        name = v.__class__.__name__
        if name in ("NoSuchObject", "NoSuchInstance", "NoSuchInstanceObject"):
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    hc_in, hc_out, in_octets, out_octets, oper_status = (v for _, v in varBinds)

    hc_in_val = _as_int_or_none(hc_in)
    hc_out_val = _as_int_or_none(hc_out)
    used_hc = hc_in_val is not None and hc_out_val is not None

    in_val = hc_in_val if used_hc else _as_int_or_none(in_octets)
    out_val = hc_out_val if used_hc else _as_int_or_none(out_octets)
    oper_val = _as_int_or_none(oper_status)

    return InterfaceCounters(
        if_index=if_index,
        in_octets=in_val,
        out_octets=out_val,
        oper_status=OPER_STATUS_LABELS.get(oper_val, "unknown") if oper_val is not None else None,
        used_high_capacity_counters=used_hc,
    )


async def discover_interfaces(
    target_ip: str, version: str, community: str, port: int = 161, timeout: int = 3, retries: int = 1
) -> list[DiscoveredInterface]:
    return await asyncio.to_thread(_discover_sync, target_ip, version, community, port, timeout, retries)


async def poll_interface(
    target_ip: str, version: str, community: str, if_index: int, port: int = 161, timeout: int = 3, retries: int = 1
) -> InterfaceCounters:
    return await asyncio.to_thread(_poll_sync, target_ip, version, community, if_index, port, timeout, retries)
