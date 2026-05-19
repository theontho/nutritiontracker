def test_create_weight(client):
    r = client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    assert r.status_code == 201
    assert r.json()["weight_kg"] == 85.5


def test_get_weight_by_date(client):
    client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    r = client.get("/weight?date=2026-05-19")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_weight_range(client):
    client.post("/weight", json={"date": "2026-05-18", "weight_kg": 86})
    client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    r = client.get("/weight?start=2026-05-18&end=2026-05-19")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_patch_weight(client):
    r = client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    wid = r.json()["id"]
    r2 = client.patch(f"/weight/{wid}", json={"weight_kg": 84.0})
    assert r2.status_code == 200
    assert r2.json()["weight_kg"] == 84.0


def test_delete_weight(client):
    r = client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    wid = r.json()["id"]
    r2 = client.delete(f"/weight/{wid}")
    assert r2.status_code == 204
