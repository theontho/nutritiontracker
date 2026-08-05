from app.repositories.foods import FoodRepository


def _seed_food(db, name="Banana", **kwargs):
    repo = FoodRepository(db)
    repo.ensure_fts()
    return repo.create(source="custom", name=name, owner_user_id=1, **kwargs)


def test_search_foods(client, db):
    _seed_food(db, "Chicken Breast", protein_g=31)
    _seed_food(db, "Chicken Thigh", protein_g=26)
    r = client.get("/foods/search?q=chicken")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_food(client, db):
    fid = _seed_food(
        db,
        "Banana",
        calories_kcal=89,
        stearic_acid_g=0.462,
        oleic_acid_cis_g=1.007,
        dpa_g=0.003,
    )
    r = client.get(f"/foods/{fid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Banana"
    assert r.json()["stearic_acid_g"] == 0.462
    assert r.json()["oleic_acid_cis_g"] == 1.007
    assert r.json()["dpa_g"] == 0.003


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


def test_barcode_lookup_caches_global_open_food_facts_result(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.foods.fetch_off_by_barcode",
        lambda barcode: {
            "source": "open_food_facts",
            "source_code": barcode,
            "name": "Imported product",
            "barcode": barcode,
            "caffeine_mg": 56.3,
        },
    )

    r = client.get("/foods/barcode/0889392000863")

    assert r.status_code == 200
    assert r.json()["caffeine_mg"] == 56.3
    assert client.get("/foods/barcode/0889392000863").json()["id"] == r.json()["id"]


def test_barcode_refresh_stores_a_measured_zero(client, db, monkeypatch):
    """A refreshed label declaring 0 must overwrite NULL, not be filtered out.

    NULL means "not reported" and 0 means "measured as zero", so a truthiness
    filter on the refresh would leave the column unknown forever.
    """
    _seed_food(db, "Diet soda", barcode="555", source_code="555")
    db.execute("UPDATE foods SET source = 'open_food_facts' WHERE barcode = '555'")
    db.commit()

    monkeypatch.setattr(
        "app.routes.foods.fetch_off_by_barcode",
        lambda barcode: {
            "source": "open_food_facts",
            "source_code": barcode,
            "name": "Diet soda",
            "barcode": barcode,
            "calories_kcal": 0,
            "sugar_g": 0,
        },
    )

    body = client.get("/foods/barcode/555").json()

    assert body["calories_kcal"] == 0
    assert body["sugar_g"] == 0


def test_create_custom_food(client, db):
    FoodRepository(db).ensure_fts()
    r = client.post(
        "/foods",
        json={
            "name": "My Food",
            "source": "custom",
            "nutrients": {"calories_kcal": 100},
        },
    )
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
