def test_branch_creation_rejects_suburb_from_a_different_city(client):
    customer = client.post("/api/customers", json={"name": "Customer"}).json()
    harare = client.post("/api/cities", json={"name": "Harare", "province": "Harare"}).json()
    bulawayo = client.post("/api/cities", json={"name": "Bulawayo", "province": "Bulawayo"}).json()

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
