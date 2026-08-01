# USDA nutrient ID → our field name
NUTRIENT_MAP = {
    1008: "calories_kcal",
    1003: "protein_g",
    1005: "carbs_g",
    1004: "fat_g",
    2000: "sugar_g",
    1235: "added_sugar_g",
    1258: "saturated_fat_g",
    1257: "trans_fat_g",
    1292: "monounsaturated_fat_g",
    1293: "polyunsaturated_fat_g",
    1079: "fiber_g",
    1253: "cholesterol_mg",
    1057: "caffeine_mg",
    1093: "sodium_mg",
    1092: "potassium_mg",
    1087: "calcium_mg",
    1089: "iron_mg",
    1090: "magnesium_mg",
    1095: "zinc_mg",
    1091: "phosphorus_mg",
    1098: "copper_mg",
    1101: "manganese_mg",
    1103: "selenium_ug",
    1096: "chromium_ug",
    1100: "iodine_ug",
    1106: "vitamin_a_ug",
    1162: "vitamin_c_mg",
    1114: "vitamin_d_ug",
    1109: "vitamin_e_mg",
    1185: "vitamin_k_ug",
    1165: "thiamin_mg",
    1166: "riboflavin_mg",
    1175: "vitamin_b6_mg",
    1178: "vitamin_b12_ug",
    1167: "niacin_mg",
    1170: "pantothenic_acid_mg",
    1176: "biotin_ug",
    1177: "folate_ug",
    1186: "folic_acid_ug",
    1180: "choline_mg",
}


def normalize_usda_food(raw: dict) -> dict:
    nutrients = {}
    for fn in raw.get("foodNutrients", []):
        # Support both flat nutrientId (some formats) and nested nutrient.id (SR Legacy, Foundation)
        nid = fn.get("nutrientId") or fn.get("nutrient", {}).get("id")
        if nid in NUTRIENT_MAP:
            nutrients[NUTRIENT_MAP[nid]] = fn.get("amount") or fn.get("value") or 0

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
