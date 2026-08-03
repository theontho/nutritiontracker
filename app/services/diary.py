from app.services.nutrients import scale_nutrients


def compute_entry_nutrients(food: dict, grams: float) -> dict:
    return scale_nutrients(food, grams / 100)


def build_food_snapshot(food: dict) -> dict:
    exclude = {"created_at", "updated_at"}
    return {k: v for k, v in food.items() if k not in exclude}
