def test_create_and_list_inventory_item(client):
    r = client.post(
        "/kitchen/inventory",
        json={
            "name": "Eggs",
            "status": "have",
            "location": "fridge",
            "category": "protein",
        },
    )
    assert r.status_code == 201
    assert r.json()["canonical_name"] == "eggs"

    listed = client.get("/kitchen/inventory?status=have")
    assert listed.status_code == 200
    assert listed.json()[0]["display_name"] == "Eggs"


def test_create_favorite_meal_and_get_matches(client):
    client.post("/kitchen/inventory", json={"name": "Eggs", "status": "have"})
    client.post("/kitchen/inventory", json={"name": "Spinach", "status": "use_soon"})
    r = client.post(
        "/kitchen/meals",
        json={
            "name": "Spinach Eggs",
            "is_private": True,
            "tags": ["breakfast", "high_protein"],
            "effort": "low",
            "favorite_score": 3,
            "ingredients": [
                {"name": "Eggs", "role": "required"},
                {"name": "Spinach", "role": "optional"},
            ],
        },
    )
    assert r.status_code == 201
    assert r.json()["is_private"] is True

    updated = client.patch(
        f"/kitchen/meals/{r.json()['id']}",
        json={"is_private": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_private"] is False

    matches = client.post("/kitchen/matches", json={"effort": "low"})
    assert matches.status_code == 200
    assert matches.json()[0]["meal_name"] == "Spinach Eggs"
    assert matches.json()[0]["use_soon_ingredients"] == ["Spinach"]


def test_generate_shopping_list_from_meals(client):
    client.post("/kitchen/inventory", json={"name": "Tortillas", "status": "have"})
    meal = client.post(
        "/kitchen/meals",
        json={
            "name": "Turkey Tacos",
            "ingredients": [
                {"name": "Ground Turkey", "role": "required"},
                {"name": "Tortillas", "role": "required"},
            ],
        },
    ).json()
    r = client.post("/kitchen/shopping-list/generate", json={"meal_ids": [meal["id"]]})
    assert r.status_code == 200
    assert [item["display_name"] for item in r.json()] == ["Ground Turkey"]


def test_mark_meal_made(client):
    meal = client.post(
        "/kitchen/meals",
        json={
            "name": "Chicken Rice Bowl",
            "ingredients": [],
        },
    ).json()
    r = client.post(f"/kitchen/meals/{meal['id']}/made")
    assert r.status_code == 200
    assert r.json()["times_made"] == 1
    assert r.json()["last_made_at"] is not None


def test_check_shopping_item(client):
    item = client.post("/kitchen/shopping-list", json={"name": "Greek Yogurt"}).json()
    r = client.patch(f"/kitchen/shopping-list/{item['id']}", json={"checked": True})
    assert r.status_code == 200
    assert r.json()["checked"] is True
