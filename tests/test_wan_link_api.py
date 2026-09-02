def _make_branch(client) -> int:
    customer = client.post("/api/customers", json={"name": "Customer"}).json()
    city = client.post("/api/cities", json={"name": "Harare", "province": "Harare"}).json()
    branch = client.post(
        "/api/branches",
        json={"customer_id": customer["id"], "city_id": city["id"], "name": "Branch", "latitude": -17.8, "longitude": 31.0},
    ).json()
    return branch["id"]


def _make_snmp_wan_link(client, target_ip="169.239.24.126") -> int:
    branch_id = _make_branch(client)
    cred = client.post(
        "/api/snmp-credentials", json={"name": "Test Cred", "version": "v2c", "community": "public"}
    ).json()
    wan = client.post(
        "/api/wan-links",
        json={
            "branch_id": branch_id,
            "snmp_enabled": True,
            "snmp_target_ip": target_ip,
            "snmp_credential_id": cred["id"],
            "circuit_capacity_bps": 100_000_000,
        },
    ).json()
    return wan["id"]


def test_discover_marks_exact_ip_match_as_suggested(client, monkeypatch):
    from app.monitoring.snmp_client import DiscoveredInterface

    wan_link_id = _make_snmp_wan_link(client, target_ip="169.239.24.126")

    async def _fake_discover(*args, **kwargs):
        return [
            DiscoveredInterface(if_index=1, name="wan1", ip_address="169.239.24.126"),
            DiscoveredInterface(if_index=2, name="wan2", ip_address="10.0.0.5"),
        ]

    import app.api.wan_links as wan_links_module

    monkeypatch.setattr(wan_links_module.snmp_client, "discover_interfaces", _fake_discover)

    resp = client.post(f"/api/wan-links/{wan_link_id}/discover")
    assert resp.status_code == 200
    by_index = {i["if_index"]: i for i in resp.json()}
    assert by_index[1]["suggested_match"] is True
    assert by_index[2]["suggested_match"] is False


def test_discover_no_match_when_no_interface_ip_equals_target(client, monkeypatch):
    from app.monitoring.snmp_client import DiscoveredInterface

    wan_link_id = _make_snmp_wan_link(client, target_ip="169.239.24.126")

    async def _fake_discover(*args, **kwargs):
        return [
            DiscoveredInterface(if_index=1, name="wan1", ip_address="169.239.24.126.5"),  # not an exact match
            DiscoveredInterface(if_index=2, name="wan2", ip_address="10.0.0.5"),
        ]

    import app.api.wan_links as wan_links_module

    monkeypatch.setattr(wan_links_module.snmp_client, "discover_interfaces", _fake_discover)

    resp = client.post(f"/api/wan-links/{wan_link_id}/discover")
    assert resp.status_code == 200
    assert all(i["suggested_match"] is False for i in resp.json())


def test_inventory_only_wan_link_can_omit_circuit_capacity(client):
    branch_id = _make_branch(client)
    resp = client.post("/api/wan-links", json={"branch_id": branch_id, "icmp_enabled": False, "snmp_enabled": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["circuit_capacity_bps"] is None
    assert body["monitoring_status"] == "not_configured"


def test_enabling_icmp_requires_circuit_capacity(client):
    branch_id = _make_branch(client)
    resp = client.post(
        "/api/wan-links",
        json={"branch_id": branch_id, "icmp_enabled": True, "icmp_target_ip": "10.0.0.1"},
    )
    assert resp.status_code == 422


def test_enabling_icmp_with_capacity_succeeds(client):
    branch_id = _make_branch(client)
    resp = client.post(
        "/api/wan-links",
        json={"branch_id": branch_id, "icmp_enabled": True, "icmp_target_ip": "10.0.0.1", "circuit_capacity_bps": 100_000_000},
    )
    assert resp.status_code == 200
    assert resp.json()["monitoring_status"] == "icmp_only"


def test_monitoring_disabled_flag_produces_monitoring_disabled_status(client):
    branch_id = _make_branch(client)
    resp = client.post("/api/wan-links", json={"branch_id": branch_id, "monitoring_disabled": True})
    assert resp.status_code == 200
    assert resp.json()["monitoring_status"] == "monitoring_disabled"


def test_wan_link_name_omits_capacity_when_inventory_only(client):
    branch_id = _make_branch(client)
    resp = client.post("/api/wan-links", json={"branch_id": branch_id})
    assert resp.status_code == 200
    assert "Mbps" not in resp.json()["name_generated"]
    assert "Gbps" not in resp.json()["name_generated"]


def test_monitoring_disabled_rejects_icmp_enabled(client):
    branch_id = _make_branch(client)
    resp = client.post(
        "/api/wan-links",
        json={
            "branch_id": branch_id,
            "monitoring_disabled": True,
            "icmp_enabled": True,
            "icmp_target_ip": "10.0.0.1",
            "circuit_capacity_bps": 100_000_000,
        },
    )
    assert resp.status_code == 422


def test_monitoring_disabled_rejects_snmp_enabled(client):
    branch_id = _make_branch(client)
    resp = client.post(
        "/api/wan-links",
        json={
            "branch_id": branch_id,
            "monitoring_disabled": True,
            "snmp_enabled": True,
            "snmp_target_ip": "10.0.0.1",
            "snmp_credential_id": 1,
            "circuit_capacity_bps": 100_000_000,
        },
    )
    assert resp.status_code == 422


def test_monitoring_disabled_alone_is_accepted(client):
    branch_id = _make_branch(client)
    resp = client.post("/api/wan-links", json={"branch_id": branch_id, "monitoring_disabled": True})
    assert resp.status_code == 200


def test_circuit_capacity_zero_is_rejected(client):
    branch_id = _make_branch(client)
    resp = client.post("/api/wan-links", json={"branch_id": branch_id, "circuit_capacity_bps": 0})
    assert resp.status_code == 422


def test_circuit_capacity_negative_is_rejected(client):
    branch_id = _make_branch(client)
    resp = client.post("/api/wan-links", json={"branch_id": branch_id, "circuit_capacity_bps": -100})
    assert resp.status_code == 422


def test_circuit_capacity_positive_is_accepted(client):
    branch_id = _make_branch(client)
    resp = client.post("/api/wan-links", json={"branch_id": branch_id, "circuit_capacity_bps": 1})
    assert resp.status_code == 200
