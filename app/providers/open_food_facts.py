NUTRIMENT_MAP = {
    "energy-kcal_100g": "calories_kcal",
    "proteins_100g": "protein_g",
    "carbohydrates_100g": "carbs_g",
    "fat_100g": "fat_g",
    "sugars_100g": "sugar_g",
    "saturated-fat_100g": "saturated_fat_g",
    "fiber_100g": "fiber_g",
    "sodium_100g": "sodium_mg",
    "potassium_100g": "potassium_mg",
    "calcium_100g": "calcium_mg",
    "iron_100g": "iron_mg",
    "magnesium_100g": "magnesium_mg",
    "zinc_100g": "zinc_mg",
    "phosphorus_100g": "phosphorus_mg",
    "vitamin-a_100g": "vitamin_a_ug",
    "vitamin-c_100g": "vitamin_c_mg",
    "vitamin-d_100g": "vitamin_d_ug",
    "vitamin-b6_100g": "vitamin_b6_mg",
    "vitamin-b12_100g": "vitamin_b12_ug",
    "niacin_100g": "niacin_mg",
}


def _parse_serving_quantity(raw: dict) -> float | None:
    val = raw.get("serving_quantity")
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def normalize_off_food(raw: dict) -> dict:
    nutriments = raw.get("nutriments", {})
    # Keys where OFF stores values in grams but we need milligrams
    G_TO_MG_KEYS = {"sodium_mg", "potassium_mg", "calcium_mg", "iron_mg",
                     "magnesium_mg", "zinc_mg", "phosphorus_mg"}

    nutrients = {}
    for off_key, our_key in NUTRIMENT_MAP.items():
        val = nutriments.get(off_key, 0) or 0
        if our_key in G_TO_MG_KEYS:
            val = val * 1000  # OFF stores these in grams per 100g
        nutrients[our_key] = val

    return {
        "source": "open_food_facts",
        "source_code": raw.get("code", ""),
        "name": raw.get("product_name", ""),
        "brand": raw.get("brands") or None,
        "barcode": raw.get("code") or None,
        "image_url": raw.get("image_url") or None,
        "serving_quantity": _parse_serving_quantity(raw),
        "serving_unit": "g",
        "serving_size_text": raw.get("serving_size") or None,
        **nutrients,
    }
