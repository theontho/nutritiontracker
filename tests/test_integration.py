from app.repositories.foods import FoodRepository


def _seed(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    return repo.create(
        source="custom", name="Chicken Breast",
        calories_kcal=165, protein_g=31, carbs_g=0, fat_g=3.6,
        serving_quantity=100, serving_unit="g",
    )


def test_full_flow(client, db):
    # Create food
    fid = _seed(db)

    # Search
    r = client.get("/foods/search?q=chicken")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Log diary entry
    r = client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 200, "unit": "g", "meal_type": "lunch"
    })
    assert r.status_code == 201
    entry = r.json()
    assert entry["nutrients_total"]["calories_kcal"] == 330
    assert entry["nutrients_total"]["protein_g"] == 62

    # Check daily stats
    r = client.get("/stats/daily/2026-05-19")
    assert r.status_code == 200
    stats = r.json()
    assert stats["total"]["calories_kcal"] == 330
    assert stats["meals"]["lunch"]["protein_g"] == 62
    assert stats["entry_count"] == 1

    # Log weight
    r = client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    assert r.status_code == 201

    # Check weight
    r = client.get("/weight?date=2026-05-19")
    assert r.status_code == 200
    assert r.json()[0]["weight_kg"] == 85.5

    # Health check
    r = client.get("/health")
    assert r.status_code == 200
