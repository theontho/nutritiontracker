from app.services.kitchen import (
    canonicalize_ingredient_name,
    generate_shopping_items_for_meals,
    rank_favorite_meals,
)


def test_canonicalize_ingredient_name_trims_and_collapses_spaces():
    assert canonicalize_ingredient_name("  Frozen   Chicken  ") == "frozen chicken"


def test_rank_favorite_meals_prioritizes_use_soon_items():
    meals = [
        {
            "id": 1,
            "name": "Plain Eggs",
            "tags": [],
            "effort": "low",
            "favorite_score": 1,
            "last_made_at": None,
            "ingredients": [
                {
                    "canonical_name": "eggs",
                    "display_name": "Eggs",
                    "role": "required",
                },
            ],
        },
        {
            "id": 2,
            "name": "Spinach Eggs",
            "tags": [],
            "effort": "low",
            "favorite_score": 1,
            "last_made_at": None,
            "ingredients": [
                {
                    "canonical_name": "eggs",
                    "display_name": "Eggs",
                    "role": "required",
                },
                {
                    "canonical_name": "spinach",
                    "display_name": "Spinach",
                    "role": "optional",
                },
            ],
        },
    ]
    inventory = [
        {"canonical_name": "eggs", "display_name": "Eggs", "status": "have"},
        {"canonical_name": "spinach", "display_name": "Spinach", "status": "use_soon"},
    ]
    results = rank_favorite_meals(meals=meals, inventory=inventory, request_filters={})
    assert results[0]["meal_id"] == 2
    assert results[0]["use_soon_ingredients"] == ["Spinach"]


def test_rank_favorite_meals_penalizes_missing_required_items():
    meals = [
        {
            "id": 1,
            "name": "Turkey Tacos",
            "tags": [],
            "effort": "low",
            "favorite_score": 5,
            "last_made_at": None,
            "ingredients": [
                {
                    "canonical_name": "ground turkey",
                    "display_name": "Ground Turkey",
                    "role": "required",
                },
                {
                    "canonical_name": "tortillas",
                    "display_name": "Tortillas",
                    "role": "required",
                },
            ],
        }
    ]
    inventory = [
        {"canonical_name": "tortillas", "display_name": "Tortillas", "status": "have"}
    ]
    results = rank_favorite_meals(meals=meals, inventory=inventory, request_filters={})
    assert results[0]["missing_required_ingredients"] == ["Ground Turkey"]
    assert results[0]["score"] < 0


def test_rank_favorite_meals_treats_staples_as_available():
    meals = [
        {
            "id": 1,
            "name": "Rice Bowl",
            "tags": [],
            "effort": "low",
            "favorite_score": 0,
            "last_made_at": None,
            "ingredients": [
                {
                    "canonical_name": "rice",
                    "display_name": "Rice",
                    "role": "required",
                },
            ],
        }
    ]
    inventory = [{"canonical_name": "rice", "display_name": "Rice", "status": "staple"}]
    results = rank_favorite_meals(meals=meals, inventory=inventory, request_filters={})
    assert results[0]["available_required_ingredients"] == ["Rice"]
    assert results[0]["missing_required_ingredients"] == []


def test_generate_shopping_items_skips_have_and_staples():
    meals = [
        {
            "id": 7,
            "name": "Turkey Tacos",
            "ingredients": [
                {
                    "canonical_name": "ground turkey",
                    "display_name": "Ground Turkey",
                    "role": "required",
                },
                {
                    "canonical_name": "tortillas",
                    "display_name": "Tortillas",
                    "role": "required",
                },
                {
                    "canonical_name": "salt",
                    "display_name": "Salt",
                    "role": "required",
                },
            ],
        }
    ]
    inventory = [
        {"canonical_name": "tortillas", "display_name": "Tortillas", "status": "have"},
        {"canonical_name": "salt", "display_name": "Salt", "status": "staple"},
    ]
    items = generate_shopping_items_for_meals(meals=meals, inventory=inventory)
    assert items == [
        {
            "canonical_name": "ground turkey",
            "display_name": "Ground Turkey",
            "source": "meal_plan",
            "linked_meal_ids": [7],
        }
    ]
