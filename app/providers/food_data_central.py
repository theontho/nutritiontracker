# USDA nutrient ID → our field name
NUTRIENT_MAP = {
    1008: "calories_kcal",
    2047: "calories_kcal",
    2048: "calories_kcal",
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

NUTRIENT_PRIORITY = {
    2047: 1,
    2048: 2,
    1008: 3,
}


def normalize_usda_food(raw: dict) -> dict:
    nutrients = {}
    priorities = {}
    for fn in raw.get("foodNutrients", []):
        # Support both flat nutrientId (some formats) and nested nutrient.id (SR Legacy, Foundation)
        nid = fn.get("nutrientId") or fn.get("nutrient", {}).get("id")
        if nid in NUTRIENT_MAP:
            field = NUTRIENT_MAP[nid]
            priority = NUTRIENT_PRIORITY.get(nid, 0)
            if priority >= priorities.get(field, -1):
                nutrients[field] = fn.get("amount") or fn.get("value") or 0
                priorities[field] = priority

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
