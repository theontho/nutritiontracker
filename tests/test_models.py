import pytest
from app.models.food import NutrientsPer100, FoodCreate
from app.models.diary import DiaryEntryCreate
from app.models.recipe import RecipeCreate, RecipeIngredientInput
from app.models.weight import WeightEntryCreate


def test_nutrients_defaults_to_zeros():
    n = NutrientsPer100()
    assert n.calories_kcal == 0
    assert n.protein_g == 0
    assert n.niacin_mg == 0


def test_food_create_minimal():
    f = FoodCreate(name="Banana", source="custom")
    assert f.name == "Banana"
    assert f.brand is None


def test_food_create_rejects_invalid_source():
    with pytest.raises(ValueError):
        FoodCreate(name="X", source="invalid")


def test_diary_entry_create():
    e = DiaryEntryCreate(food_id=1, amount=1.5, unit="cup", meal_type="breakfast")
    assert e.meal_type == "breakfast"


def test_diary_entry_rejects_invalid_meal_type():
    with pytest.raises(ValueError):
        DiaryEntryCreate(food_id=1, amount=1, unit="g", meal_type="brunch")


def test_recipe_create():
    r = RecipeCreate(
        name="Oatmeal",
        servings=2,
        total_weight_g=400,
        ingredients=[
            RecipeIngredientInput(food_id=1, amount=100, unit="g"),
            RecipeIngredientInput(food_id=2, amount=200, unit="ml"),
        ],
    )
    assert len(r.ingredients) == 2


def test_weight_entry_create():
    w = WeightEntryCreate(weight_kg=85.5, date="2026-05-19")
    assert w.weight_kg == 85.5
