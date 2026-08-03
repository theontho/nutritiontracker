from app.services.nutrients import scale_nutrients, sum_nutrients


def compute_recipe_nutrients(
    ingredients: list[dict], total_weight_g: float, servings: float
) -> tuple[dict, dict]:
    totals = sum_nutrients(
        (
            scale_nutrients(ingredient["food_snapshot"], ingredient["grams"] / 100)
            for ingredient in ingredients
        ),
        empty_is_zero=True,
    )
    per_100 = scale_nutrients(totals, 100 / total_weight_g)
    per_serving = scale_nutrients(totals, 1 / servings)
    return per_100, per_serving
