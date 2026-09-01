from app.naming import generate_wan_name


def test_generate_wan_name_matches_documented_format():
    name = generate_wan_name(
        customer_name="PCD",
        city_name="Harare",
        branch_name="New Ardbennie",
        device_model="FortiGate 100F",
        isp_name="Frampol LTZ",
        public_ip="169.239.24.126",
        circuit_capacity_bps=100_000_000,
    )
    assert name == "PCD - Harare - New Ardbennie - FortiGate 100F - Frampol LTZ - (169.239.24.126) - 100Mbps"


def test_generate_wan_name_omits_capacity_when_absent():
    # Inventory-only WAN links may not have a circuit capacity yet — the
    # name must not fabricate a "0Mbps" segment.
    name = generate_wan_name(
        customer_name="PCD",
        city_name="Harare",
        branch_name="New Ardbennie",
        device_model=None,
        isp_name=None,
        public_ip=None,
        circuit_capacity_bps=None,
    )
    assert name == "PCD - Harare - New Ardbennie"
    assert "0Mbps" not in name
