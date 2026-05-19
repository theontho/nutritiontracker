from app.repositories.foods import FoodRepository


def _seed_food(db, name="Banana", **kwargs):
    repo = FoodRepository(db)
    repo.ensure_fts()
    return repo.create(source="custom", name=name, **kwargs)


def test_search_foods(client, db):
    _seed_food(db, "Chicken Breast", protein_g=31)
    _seed_food(db, "Chicken Thigh", protein_g=26)
    r = client.get("/foods/search?q=chicken")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_food(client, db):
    fid = _seed_food(db, "Banana", calories_kcal=89)
    r = client.get(f"/foods/{fid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Banana"


def test_get_food_404(client):
    r = client.get("/foods/9999")
    assert r.status_code == 404


def test_barcode_lookup(client, db):
    _seed_food(db, "Granola", barcode="12345")
    r = client.get("/foods/barcode/12345")
    assert r.status_code == 200
    assert r.json()["name"] == "Granola"


def test_barcode_404(client):
    r = client.get("/foods/barcode/nope")
    assert r.status_code == 404


def test_create_custom_food(client, db):
    FoodRepository(db).ensure_fts()
    r = client.post("/foods", json={"name": "My Food", "source": "custom",
                                     "nutrients": {"calories_kcal": 100}})
    assert r.status_code == 201
    assert r.json()["name"] == "My Food"


def test_update_custom_food(client, db):
    fid = _seed_food(db, "Old")
    r = client.patch(f"/foods/{fid}", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


def test_delete_custom_food(client, db):
    fid = _seed_food(db, "Gone")
    r = client.delete(f"/foods/{fid}")
    assert r.status_code == 204
