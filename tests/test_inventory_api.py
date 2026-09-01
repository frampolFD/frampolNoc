def test_branch_creation_rejects_city_from_a_different_customer(client):
    customer_a = client.post("/api/customers", json={"name": "Customer A"}).json()
    customer_b = client.post("/api/customers", json={"name": "Customer B"}).json()

    harare = client.post("/api/cities", json={"customer_id": customer_a["id"], "name": "Harare"}).json()
    bulawayo = client.post("/api/cities", json={"customer_id": customer_b["id"], "name": "Bulawayo"}).json()

    # Customer A's branch, but pointed at Customer B's city — must be rejected.
    resp = client.post(
        "/api/branches",
        json={
            "customer_id": customer_a["id"],
            "city_id": bulawayo["id"],
            "name": "Mismatched Branch",
            "latitude": -17.8,
            "longitude": 31.0,
        },
    )
    assert resp.status_code == 422

    # The correctly matched pair must still work.
    resp = client.post(
        "/api/branches",
        json={
            "customer_id": customer_a["id"],
            "city_id": harare["id"],
            "name": "Head Office",
            "latitude": -17.8,
            "longitude": 31.0,
        },
    )
    assert resp.status_code == 200


def test_branch_creation_rejects_suburb_from_a_different_city(client):
    customer = client.post("/api/customers", json={"name": "Customer"}).json()
    harare = client.post("/api/cities", json={"customer_id": customer["id"], "name": "Harare"}).json()
    bulawayo = client.post("/api/cities", json={"customer_id": customer["id"], "name": "Bulawayo"}).json()

    highlands = client.post("/api/suburbs", json={"city_id": harare["id"], "name": "Highlands"}).json()

    # Highlands belongs to Harare, but the branch claims Bulawayo as its city.
    resp = client.post(
        "/api/branches",
        json={
            "customer_id": customer["id"],
            "city_id": bulawayo["id"],
            "suburb_id": highlands["id"],
            "name": "Mismatched Branch",
            "latitude": -20.0,
            "longitude": 28.6,
        },
    )
    assert resp.status_code == 422

    resp = client.post(
        "/api/branches",
        json={
            "customer_id": customer["id"],
            "city_id": harare["id"],
            "suburb_id": highlands["id"],
            "name": "Correct Branch",
            "latitude": -17.8,
            "longitude": 31.0,
        },
    )
    assert resp.status_code == 200
