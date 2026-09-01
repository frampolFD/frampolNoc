import importlib.util
from pathlib import Path

from app.models import Branch, City, Customer, Suburb


def test_city_creation_no_longer_requires_customer_id(client):
    resp = client.post("/api/cities", json={"name": "Chinhoyi", "province": "Mashonaland West"})
    assert resp.status_code == 200
    body = resp.json()
    assert "customer_id" not in body
    assert body["name"] == "Chinhoyi"
    assert body["province"] == "Mashonaland West"
    assert body["country_code"] == "ZW"


def test_city_list_is_shared_globally(client):
    client.post("/api/cities", json={"name": "Kadoma", "province": "Mashonaland West"})
    # No customer context involved at all — the list endpoint takes no
    # customer_id parameter any more.
    resp = client.get("/api/cities")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "Kadoma" in names


def test_two_customers_can_create_branches_using_the_same_city(client):
    customer_a = client.post("/api/customers", json={"name": "Customer A"}).json()
    customer_b = client.post("/api/customers", json={"name": "Customer B"}).json()
    harare = client.post("/api/cities", json={"name": "Harare", "province": "Harare"}).json()

    resp_a = client.post(
        "/api/branches",
        json={"customer_id": customer_a["id"], "city_id": harare["id"], "name": "A's Office", "latitude": -17.8, "longitude": 31.0},
    )
    resp_b = client.post(
        "/api/branches",
        json={"customer_id": customer_b["id"], "city_id": harare["id"], "name": "B's Office", "latitude": -17.8, "longitude": 31.0},
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json()["city_id"] == resp_b.json()["city_id"] == harare["id"]


def test_two_customers_can_use_the_same_suburb(client):
    customer_a = client.post("/api/customers", json={"name": "Customer A"}).json()
    customer_b = client.post("/api/customers", json={"name": "Customer B"}).json()
    harare = client.post("/api/cities", json={"name": "Harare", "province": "Harare"}).json()
    highlands = client.post("/api/suburbs", json={"city_id": harare["id"], "name": "Highlands"}).json()

    resp_a = client.post(
        "/api/branches",
        json={
            "customer_id": customer_a["id"], "city_id": harare["id"], "suburb_id": highlands["id"],
            "name": "A's Office", "latitude": -17.8, "longitude": 31.0,
        },
    )
    resp_b = client.post(
        "/api/branches",
        json={
            "customer_id": customer_b["id"], "city_id": harare["id"], "suburb_id": highlands["id"],
            "name": "B's Office", "latitude": -17.8, "longitude": 31.0,
        },
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json()["suburb_id"] == resp_b.json()["suburb_id"] == highlands["id"]


def test_duplicate_city_in_same_province_rejected_case_insensitively(client):
    resp = client.post("/api/cities", json={"name": "Gweru", "province": "Midlands"})
    assert resp.status_code == 200

    resp = client.post("/api/cities", json={"name": "GWERU", "province": "midlands"})
    assert resp.status_code == 409

    # A same-named city in a *different* province is a different place and
    # must be allowed.
    resp = client.post("/api/cities", json={"name": "Gweru", "province": "Harare"})
    assert resp.status_code == 200


def test_duplicate_suburb_under_same_city_rejected_case_insensitively(client):
    city = client.post("/api/cities", json={"name": "Bulawayo", "province": "Bulawayo"}).json()
    resp = client.post("/api/suburbs", json={"city_id": city["id"], "name": "Suburbs"})
    assert resp.status_code == 200

    resp = client.post("/api/suburbs", json={"city_id": city["id"], "name": "SUBURBS"})
    assert resp.status_code == 409

    # Same suburb name under a *different* city must be allowed (this is
    # also proven independently by test_two_customers_can_use_the_same_suburb).
    other_city = client.post("/api/cities", json={"name": "Gweru", "province": "Midlands"}).json()
    resp = client.post("/api/suburbs", json={"city_id": other_city["id"], "name": "Suburbs"})
    assert resp.status_code == 200


def _load_migration_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "8610f8c7c2c6_shared_geographic_reference_model_for_.py"
    )
    spec = importlib.util.spec_from_file_location("shared_geo_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preload_contains_exactly_66_records():
    module = _load_migration_module()
    assert len(module.ZW_SEED_CITIES) == 66


def test_preload_contains_required_cities():
    module = _load_migration_module()
    names = {rec["name"] for rec in module.ZW_SEED_CITIES}
    for expected in ["Harare", "Bulawayo", "Mutare", "Gweru", "Masvingo", "Beitbridge", "Victoria Falls"]:
        assert expected in names


def test_explorer_shows_same_shared_city_under_each_customer(client):
    customer_a = client.post("/api/customers", json={"name": "Customer A"}).json()
    customer_b = client.post("/api/customers", json={"name": "Customer B"}).json()
    harare = client.post("/api/cities", json={"name": "Harare", "province": "Harare"}).json()

    client.post(
        "/api/branches",
        json={"customer_id": customer_a["id"], "city_id": harare["id"], "name": "A's Office", "latitude": -17.8, "longitude": 31.0},
    )
    client.post(
        "/api/branches",
        json={"customer_id": customer_b["id"], "city_id": harare["id"], "name": "B's Office", "latitude": -17.8, "longitude": 31.0},
    )

    tree = client.get("/api/explorer").json()
    node_a = next(c for c in tree if c["name"] == "Customer A")
    node_b = next(c for c in tree if c["name"] == "Customer B")

    city_a = next(c for c in node_a["cities"] if c["name"] == "Harare")
    city_b = next(c for c in node_b["cities"] if c["name"] == "Harare")

    assert city_a["id"] == city_b["id"] == harare["id"]
    assert [b["name"] for b in city_a["branches"]] == ["A's Office"]
    assert [b["name"] for b in city_b["branches"]] == ["B's Office"]


def test_deleting_customer_does_not_delete_shared_city_or_suburb(db_session):
    customer = Customer(name="Customer")
    db_session.add(customer)
    db_session.flush()

    city = City(name="Harare", province="Harare", country_code="ZW")
    db_session.add(city)
    db_session.flush()
    suburb = Suburb(city_id=city.id, name="Highlands")
    db_session.add(suburb)
    db_session.flush()

    branch = Branch(customer_id=customer.id, city_id=city.id, suburb_id=suburb.id, name="Office", latitude=0.0, longitude=0.0)
    db_session.add(branch)
    db_session.commit()

    db_session.delete(customer)
    db_session.commit()

    assert db_session.get(Branch, branch.id) is None  # customer's own branch is gone
    assert db_session.get(City, city.id) is not None  # shared city survives
    assert db_session.get(Suburb, suburb.id) is not None  # shared suburb survives
