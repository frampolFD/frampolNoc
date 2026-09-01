def _make_branch(client) -> int:
    customer = client.post("/api/customers", json={"name": "Customer"}).json()
    city = client.post("/api/cities", json={"customer_id": customer["id"], "name": "Harare"}).json()
    branch = client.post(
        "/api/branches",
        json={"customer_id": customer["id"], "city_id": city["id"], "name": "Branch", "latitude": -17.8, "longitude": 31.0},
    ).json()
    return branch["id"]


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
