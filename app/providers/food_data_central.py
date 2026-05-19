# USDA nutrient ID → our field name
NUTRIENT_MAP = {
    1008: "calories_kcal",
    1003: "protein_g",
    1005: "carbs_g",
    1004: "fat_g",
    2000: "sugar_g",
    1258: "saturated_fat_g",
    1079: "fiber_g",
    1093: "sodium_mg",
    1092: "potassium_mg",
    1087: "calcium_mg",
    1089: "iron_mg",
    1090: "magnesium_mg",
    1095: "zinc_mg",
    1091: "phosphorus_mg",
    1106: "vitamin_a_ug",
    1162: "vitamin_c_mg",
    1114: "vitamin_d_ug",
    1175: "vitamin_b6_mg",
    1178: "vitamin_b12_ug",
    1167: "niacin_mg",
}


def normalize_usda_food(raw: dict) -> dict:
    nutrients = {}
    for fn in raw.get("foodNutrients", []):
        nid = fn.get("nutrientId")
        if nid in NUTRIENT_MAP:
            nutrients[NUTRIENT_MAP[nid]] = fn.get("value", 0) or 0

    return {
        "source": "food_data_central",
        "source_code": str(raw.get("fdcId", "")),
        "name": raw.get("description", ""),
        "brand": raw.get("brandName") or None,
        "barcode": raw.get("gtinUpc") or None,
        "image_url": None,
        "serving_quantity": None,
        "serving_unit": None,
        "serving_size_text": None,
        **{k: nutrients.get(k, 0) for k in NUTRIENT_MAP.values()},
    }
