from app.monitoring.snmp_client import build_interfaces


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
