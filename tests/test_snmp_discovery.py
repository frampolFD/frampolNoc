from app.monitoring.snmp_client import build_interfaces, parse_ip_index_map


def test_build_interfaces_merges_columns_and_prefers_high_speed():
    descr = {"1": "port1", "2": "wan1"}
    speed = {"1": 100_000_000, "2": 4_294_967_295}  # ifSpeed maxes out at ~4.29G for gig+ links
    admin = {"1": 1, "2": 1}
    oper = {"1": 1, "2": 2}
    mac = {"1": bytes([0x00, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E])}
    name = {"2": "wan1"}
    alias = {"2": "Primary Internet"}
    high_speed = {"2": 1000}  # Mbps -> should override the saturated ifSpeed value
    index_to_ip = {2: "169.239.24.126"}

    interfaces = build_interfaces(descr, speed, admin, oper, mac, name, alias, high_speed, index_to_ip)

    assert [i.if_index for i in interfaces] == [1, 2]

    port1 = interfaces[0]
    assert port1.description == "port1"
    assert port1.speed_bps == 100_000_000
    assert port1.mac_address == "00:1a:2b:3c:4d:5e"
    assert port1.admin_status == "up"
    assert port1.oper_status == "up"
    assert port1.ip_address is None

    wan1 = interfaces[1]
    assert wan1.name == "wan1"
    assert wan1.alias == "Primary Internet"
    assert wan1.speed_bps == 1_000_000_000  # from ifHighSpeed, not the saturated ifSpeed
    assert wan1.oper_status == "down"
    assert wan1.ip_address == "169.239.24.126"


def test_build_interfaces_handles_missing_optional_columns():
    descr = {"5": "mgmt"}
    interfaces = build_interfaces(descr, {}, {}, {}, {}, {}, {}, {}, {})

    assert len(interfaces) == 1
    iface = interfaces[0]
    assert iface.if_index == 5
    assert iface.name is None
    assert iface.alias is None
    assert iface.mac_address is None
    assert iface.admin_status is None
    assert iface.oper_status is None
    assert iface.ip_address is None


# --- IP-MIB ipAdEntIfIndex suffix parsing -----------------------------------
#
# ipAdEntAddr (this table's INDEX) is a fixed 4-octet IpAddress per RFC 1213,
# so a compliant row's OID suffix is exactly the address's four octets, e.g.
# walking 1.3.6.1.2.1.4.20.1.2 yields rows like
# "1.3.6.1.2.1.4.20.1.2.169.239.24.126" -> suffix "169.239.24.126". A
# previously reported regression (documented in the bug report, though not
# reproduced against the one live device this codebase has been tested
# against) showed some Fortinet firmware appending exactly ONE extra numeric
# sub-identifier after those four octets, e.g. suffix "169.239.24.126.1".
# Only that one specific, documented shape is treated as a supported
# trailing index component and stripped; anything else with more than four
# components is an arbitrary/unsupported suffix and must be rejected rather
# than guessed at.


def test_parse_ip_index_map_extracts_clean_four_octet_address():
    raw_rows = {"169.239.24.126": 1}
    assert parse_ip_index_map(raw_rows) == {"169.239.24.126": 1}


def test_parse_ip_index_map_strips_supported_single_trailing_index_component():
    # The one documented row shape: exactly one extra numeric
    # sub-identifier tacked on after the real 4-octet address.
    raw_rows = {"169.239.24.126.1": 1}
    assert parse_ip_index_map(raw_rows) == {"169.239.24.126": 1}


def test_parse_ip_index_map_preserves_addresses_that_genuinely_end_in_dot_one():
    # 10.255.1.1 is a real, complete 4-octet address whose last octet
    # happens to be 1 — this must never be mistaken for an address with an
    # appended extra component and truncated to "10.255.1".
    raw_rows = {"10.255.1.1": 18, "10.254.94.1": 21}
    assert parse_ip_index_map(raw_rows) == {"10.255.1.1": 18, "10.254.94.1": 21}


def test_parse_ip_index_map_never_returns_a_five_component_address():
    raw_rows = {
        "169.239.24.126.1": 1,
        "172.16.25.190.1": 2,
        "10.255.1.1": 3,
    }
    result = parse_ip_index_map(raw_rows)
    for ip in result:
        assert len(ip.split(".")) == 4


def test_parse_ip_index_map_maps_extracted_ip_to_correct_if_index():
    raw_rows = {"41.79.31.22": 1, "102.207.50.75.1": 2, "10.255.1.1": 18}
    result = parse_ip_index_map(raw_rows)
    assert result["41.79.31.22"] == 1
    assert result["102.207.50.75"] == 2
    assert result["10.255.1.1"] == 18


def test_parse_ip_index_map_rejects_arbitrary_malformed_suffixes_with_extra_components():
    # More than one trailing component past the four octets has no
    # verified/documented meaning for this table — unlike the single
    # trailing-index shape above, these must be rejected, not truncated to
    # "the first four components" on the assumption that the rest is safe
    # to discard.
    raw_rows = {
        "169.239.24.126.1.2": 1,  # two extra components
        "169.239.24.126.1.2.3": 2,  # three extra components
        "169.239.24.126.abc": 3,  # trailing component isn't even numeric
        "169.239.24.126.-1": 4,  # trailing component isn't a plain non-negative int
    }
    assert parse_ip_index_map(raw_rows) == {}


def test_parse_ip_index_map_ignores_malformed_or_unsupported_suffixes():
    raw_rows = {
        "": 1,  # empty
        "1.2.3": 2,  # too short to be an address
        "not.an.ip.address": 3,  # non-numeric octets
        "999.1.2.3": 4,  # octet out of range
        "-1.2.3.4": 5,  # negative octet
    }
    assert parse_ip_index_map(raw_rows) == {}


def test_parse_ip_index_map_ignores_row_with_non_integer_value():
    raw_rows = {"41.79.31.22": "not-an-ifindex"}
    assert parse_ip_index_map(raw_rows) == {}
