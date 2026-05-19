from app.repositories.foods import FoodRepository


def _seed_foods(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    oats = repo.create(source="custom", name="Oats", calories_kcal=350, protein_g=12, carbs_g=60, fat_g=6)
    milk = repo.create(source="custom", name="Milk", calories_kcal=60, protein_g=3, carbs_g=5, fat_g=3)
    return oats, milk


def test_create_recipe(client, db):
    oats, milk = _seed_foods(db)
    r = client.post("/recipes", json={
        "name": "Oatmeal",
        "servings": 2,
        "total_weight_g": 300,
        "ingredients": [
            {"food_id": oats, "amount": 100, "unit": "g"},
            {"food_id": milk, "amount": 200, "unit": "ml"},
        ],
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Oatmeal"
    assert "calories_kcal" in data["nutrients_per_serving"]


def test_list_recipes(client, db):
    oats, milk = _seed_foods(db)
    client.post("/recipes", json={
        "name": "Oatmeal", "servings": 2, "total_weight_g": 300,
        "ingredients": [{"food_id": oats, "amount": 100, "unit": "g"}],
    })
    r = client.get("/recipes")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_recipe(client, db):
    oats, _ = _seed_foods(db)
    r = client.post("/recipes", json={
        "name": "Oatmeal", "servings": 1, "total_weight_g": 100,
        "ingredients": [{"food_id": oats, "amount": 100, "unit": "g"}],
    })
    rid = r.json()["id"]
    r2 = client.get(f"/recipes/{rid}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "Oatmeal"


def test_delete_recipe(client, db):
    oats, _ = _seed_foods(db)
    r = client.post("/recipes", json={
        "name": "Oatmeal", "servings": 1, "total_weight_g": 100,
        "ingredients": [{"food_id": oats, "amount": 100, "unit": "g"}],
    })
    rid = r.json()["id"]
    r2 = client.delete(f"/recipes/{rid}")
    assert r2.status_code == 204
