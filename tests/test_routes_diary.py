from app.repositories.foods import FoodRepository


def _seed(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    return repo.create(
        source="custom", name="Banana", calories_kcal=89,
        protein_g=1.1, carbs_g=22.8, fat_g=0.3,
        serving_quantity=118, serving_unit="g",
    )


def test_create_diary_entry(client, db):
    fid = _seed(db)
    r = client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 100, "unit": "g", "meal_type": "breakfast"
    })
    assert r.status_code == 201
    assert r.json()["grams"] == 100
    assert r.json()["nutrients_total"]["calories_kcal"] == 89


def test_list_diary(client, db):
    fid = _seed(db)
    client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 100, "unit": "g", "meal_type": "breakfast"
    })
    r = client.get("/diary/2026-05-19")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_update_diary_entry(client, db):
    fid = _seed(db)
    r = client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 100, "unit": "g", "meal_type": "breakfast"
    })
    eid = r.json()["id"]
    r2 = client.patch(f"/diary/entries/{eid}", json={"amount": 200, "unit": "g"})
    assert r2.status_code == 200
    assert r2.json()["grams"] == 200


def test_delete_diary_entry(client, db):
    fid = _seed(db)
    r = client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 100, "unit": "g", "meal_type": "breakfast"
    })
    eid = r.json()["id"]
    r2 = client.delete(f"/diary/entries/{eid}")
    assert r2.status_code == 204
