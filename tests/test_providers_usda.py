from app.providers.food_data_central import normalize_usda_food


def test_normalize_usda_food():
    raw = {
        "fdcId": 12345,
        "description": "Banana, raw",
        "brandName": None,
        "gtinUpc": "",
        "foodNutrients": [
            {"nutrientId": 1008, "value": 89},   # Energy
            {"nutrientId": 1003, "value": 1.1},   # Protein
            {"nutrientId": 1005, "value": 22.8},  # Carbs
            {"nutrientId": 1004, "value": 0.3},   # Fat
        ],
    }
    food = normalize_usda_food(raw)
    assert food["name"] == "Banana, raw"
    assert food["source"] == "food_data_central"
    assert food["source_code"] == "12345"
    assert food["calories_kcal"] == 89
    assert food["protein_g"] == 1.1


def test_normalize_handles_missing_nutrients():
    raw = {
        "fdcId": 99,
        "description": "Mystery food",
        "foodNutrients": [],
    }
    food = normalize_usda_food(raw)
    assert food["calories_kcal"] == 0
    assert food["protein_g"] == 0
