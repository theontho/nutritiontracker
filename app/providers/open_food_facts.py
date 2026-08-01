import httpx

OFF_API_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OFF_TIMEOUT = 5.0  # seconds

OFF_NUTRIENT_MAP = {
    "calories_kcal": (("energy-kcal",), "kcal", "kcal"),
    "protein_g": (("proteins",), "g", "g"),
    "carbs_g": (("carbohydrates",), "g", "g"),
    "fat_g": (("fat",), "g", "g"),
    "sugar_g": (("sugars",), "g", "g"),
    "added_sugar_g": (("added-sugars",), "g", "g"),
    "saturated_fat_g": (("saturated-fat",), "g", "g"),
    "trans_fat_g": (("trans-fat",), "g", "g"),
    "monounsaturated_fat_g": (("monounsaturated-fat",), "g", "g"),
    "polyunsaturated_fat_g": (("polyunsaturated-fat",), "g", "g"),
    "fiber_g": (("fiber",), "g", "g"),
    "cholesterol_mg": (("cholesterol",), "mg", "mg"),
    "caffeine_mg": (("caffeine",), "mg", "mg"),
    "sodium_mg": (("sodium",), "g", "mg"),
    "potassium_mg": (("potassium",), "mg", "mg"),
    "calcium_mg": (("calcium",), "mg", "mg"),
    "iron_mg": (("iron",), "mg", "mg"),
    "magnesium_mg": (("magnesium",), "mg", "mg"),
    "zinc_mg": (("zinc",), "mg", "mg"),
    "phosphorus_mg": (("phosphorus",), "mg", "mg"),
    "copper_mg": (("copper",), "mg", "mg"),
    "manganese_mg": (("manganese",), "mg", "mg"),
    "selenium_ug": (("selenium",), "ug", "ug"),
    "chromium_ug": (("chromium",), "ug", "ug"),
    "iodine_ug": (("iodine",), "ug", "ug"),
    "vitamin_a_ug": (("vitamin-a",), "ug", "ug"),
    "vitamin_c_mg": (("vitamin-c",), "mg", "mg"),
    "vitamin_d_ug": (("vitamin-d",), "ug", "ug"),
    "vitamin_e_mg": (("vitamin-e",), "mg", "mg"),
    "vitamin_k_ug": (("vitamin-k",), "ug", "ug"),
    "thiamin_mg": (("vitamin-b1",), "mg", "mg"),
    "riboflavin_mg": (("vitamin-b2",), "mg", "mg"),
    "vitamin_b6_mg": (("vitamin-b6",), "mg", "mg"),
    "vitamin_b12_ug": (("vitamin-b12",), "ug", "ug"),
    "niacin_mg": (("vitamin-pp", "niacin"), "mg", "mg"),
    "pantothenic_acid_mg": (("pantothenic-acid",), "mg", "mg"),
    "biotin_ug": (("biotin",), "ug", "ug"),
    "folate_ug": (("folates",), "ug", "ug"),
    "folic_acid_ug": (("vitamin-b9",), "ug", "ug"),
    "choline_mg": (("choline",), "g", "mg"),
}

_UNIT_FACTORS_TO_GRAMS = {
    "g": 1,
    "mg": 0.001,
    "ug": 0.000001,
    "mcg": 0.000001,
}


def _normalized_unit(unit: str) -> str:
    return unit.lower().replace("μ", "u").replace("µ", "u")


def _convert_unit(value: float, source_unit: str, target_unit: str) -> float:
    if source_unit == target_unit:
        return value
    if source_unit == "kcal" or target_unit == "kcal":
        raise ValueError(f"Cannot convert {source_unit} to {target_unit}")
    return value * _UNIT_FACTORS_TO_GRAMS[source_unit] / _UNIT_FACTORS_TO_GRAMS[target_unit]


def _parse_serving_quantity(raw: dict) -> float | None:
    val = raw.get("serving_quantity")
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _get_nutrient_value(
    nutriments: dict, source_keys: tuple[str, ...], default_unit: str, target_unit: str
) -> float:
    for source_key in source_keys:
        value = nutriments.get(f"{source_key}_100g")
        if value is None:
            continue
        try:
            source_unit = _normalized_unit(nutriments.get(f"{source_key}_unit", default_unit))
            return _convert_unit(float(value), source_unit, target_unit)
        except (KeyError, TypeError, ValueError):
            return 0
    return 0


def normalize_off_food(raw: dict) -> dict:
    nutriments = raw.get("nutriments", {})
    nutrients = {
        field: _get_nutrient_value(nutriments, source_keys, source_unit, target_unit)
        for field, (source_keys, source_unit, target_unit) in OFF_NUTRIENT_MAP.items()
    }

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


def fetch_off_by_barcode(barcode: str) -> dict | None:
    """Fetch a single product from the live OFF API by barcode.

    Returns a normalized food dict if the product exists and has nutrient data,
    otherwise returns None.
    """
    try:
        resp = httpx.get(
            OFF_API_URL.format(barcode=barcode),
            timeout=OFF_TIMEOUT,
            headers={"User-Agent": "NutritionTracker/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None

    if data.get("status") != 1:
        return None

    product = data.get("product", {})
    name = product.get("product_name", "").strip()
    if not name:
        return None

    normalized = normalize_off_food(product)
    # Only return if we actually got nutrient data
    if normalized.get("calories_kcal", 0) == 0 and normalized.get("protein_g", 0) == 0:
        return None

    return normalized
