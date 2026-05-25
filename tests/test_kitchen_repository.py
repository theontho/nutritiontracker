from app.repositories.kitchen import KitchenRepository


def test_upsert_inventory_creates_item(db):
    repo = KitchenRepository(db)
    item = repo.upsert_inventory_item(
        user_id=1,
        display_name="Eggs",
        canonical_name="eggs",
        status="have",
        location="fridge",
        category="protein",
        notes=None,
    )
    assert item["display_name"] == "Eggs"
    assert item["canonical_name"] == "eggs"
    assert item["status"] == "have"
    assert item["location"] == "fridge"


def test_upsert_inventory_updates_existing_item(db):
    repo = KitchenRepository(db)
    first = repo.upsert_inventory_item(
        user_id=1,
        display_name="Spinach",
        canonical_name="spinach",
        status="have",
    )
    second = repo.upsert_inventory_item(
        user_id=1,
        display_name="Spinach",
        canonical_name="spinach",
        status="use_soon",
        location="fridge",
    )
    assert second["id"] == first["id"]
    assert second["status"] == "use_soon"
    assert second["location"] == "fridge"


def test_list_inventory_filters_by_status(db):
    repo = KitchenRepository(db)
    repo.upsert_inventory_item(
        user_id=1, display_name="Eggs", canonical_name="eggs", status="have"
    )
    repo.upsert_inventory_item(
        user_id=1,
        display_name="Spinach",
        canonical_name="spinach",
        status="use_soon",
    )
    results = repo.list_inventory(user_id=1, status="use_soon")
    assert [item["canonical_name"] for item in results] == ["spinach"]


def test_create_favorite_meal_with_ingredients(db):
    repo = KitchenRepository(db)
    meal = repo.create_favorite_meal(
        user_id=1,
        name="Egg Fried Rice",
        tags=["dinner", "low_effort"],
        prep_time_minutes=15,
        effort="low",
        favorite_score=4,
        ingredients=[
            {
                "display_name": "Eggs",
                "canonical_name": "eggs",
                "role": "required",
                "category": "protein",
            },
            {
                "display_name": "Rice",
                "canonical_name": "rice",
                "role": "required",
                "category": "grain",
            },
            {
                "display_name": "Spinach",
                "canonical_name": "spinach",
                "role": "optional",
                "category": "vegetable",
            },
        ],
    )
    assert meal["name"] == "Egg Fried Rice"
    assert meal["tags"] == ["dinner", "low_effort"]
    assert len(meal["ingredients"]) == 3


def test_mark_favorite_meal_made_updates_history(db):
    repo = KitchenRepository(db)
    meal = repo.create_favorite_meal(
        user_id=1,
        name="Chicken Rice Bowl",
        tags=[],
        ingredients=[],
    )
    updated = repo.mark_meal_made(
        user_id=1, meal_id=meal["id"], made_at="2026-05-25T12:00:00"
    )
    assert updated["times_made"] == 1
    assert updated["last_made_at"] == "2026-05-25T12:00:00"


def test_upsert_shopping_list_item_merges_by_name(db):
    repo = KitchenRepository(db)
    first = repo.upsert_shopping_list_item(
        user_id=1,
        display_name="Tortillas",
        canonical_name="tortillas",
        source="manual",
        linked_meal_ids=[],
    )
    second = repo.upsert_shopping_list_item(
        user_id=1,
        display_name="Tortillas",
        canonical_name="tortillas",
        source="meal_plan",
        linked_meal_ids=[7],
    )
    assert second["id"] == first["id"]
    assert second["linked_meal_ids"] == [7]
