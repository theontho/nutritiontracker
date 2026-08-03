# USDA nutrient ID → our field name
NUTRIENT_MAP = {
    1051: "water_g",
    1007: "ash_g",
    1018: "alcohol_g",
    1041: "oxalate_mg",
    1008: "calories_kcal",
    2047: "calories_kcal",
    2048: "calories_kcal",
    1003: "protein_g",
    1005: "carbs_g",
    1009: "starch_g",
    1004: "fat_g",
    2000: "sugar_g",
    1012: "fructose_g",
    1075: "galactose_g",
    1011: "glucose_g",
    1013: "lactose_g",
    1014: "maltose_g",
    1010: "sucrose_g",
    1235: "added_sugar_g",
    1258: "saturated_fat_g",
    1257: "trans_fat_g",
    1292: "monounsaturated_fat_g",
    1293: "polyunsaturated_fat_g",
    1404: "alpha_linolenic_acid_g",
    1272: "dha_g",
    1278: "epa_g",
    1271: "arachidonic_acid_g",
    1316: "linoleic_acid_g",
    1079: "fiber_g",
    1084: "insoluble_fiber_g",
    1082: "soluble_fiber_g",
    1253: "cholesterol_mg",
    1283: "phytosterol_mg",
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
    1099: "fluoride_ug",
    1100: "iodine_ug",
    1102: "molybdenum_ug",
    1106: "vitamin_a_ug",
    1105: "retinol_ug",
    1107: "beta_carotene_ug",
    1159: "cis_beta_carotene_ug",
    2028: "trans_beta_carotene_ug",
    1108: "alpha_carotene_ug",
    1118: "gamma_carotene_ug",
    1120: "beta_cryptoxanthin_ug",
    2032: "alpha_cryptoxanthin_ug",
    1122: "lycopene_ug",
    1160: "cis_lycopene_ug",
    2029: "trans_lycopene_ug",
    1121: "lutein_ug",
    1123: "lutein_zeaxanthin_ug",
    1161: "cis_lutein_zeaxanthin_ug",
    1162: "vitamin_c_mg",
    1114: "vitamin_d_ug",
    1111: "vitamin_d2_ug",
    1112: "vitamin_d3_ug",
    1113: "vitamin_d3_25_hydroxy_ug",
    2059: "vitamin_d4_ug",
    1109: "vitamin_e_mg",
    1242: "vitamin_e_added_mg",
    1125: "beta_tocopherol_mg",
    1126: "gamma_tocopherol_mg",
    1127: "delta_tocopherol_mg",
    1128: "alpha_tocotrienol_mg",
    1129: "beta_tocotrienol_mg",
    1130: "gamma_tocotrienol_mg",
    1131: "delta_tocotrienol_mg",
    1185: "vitamin_k_ug",
    1184: "dihydrophylloquinone_ug",
    1183: "menaquinone_4_ug",
    1165: "thiamin_mg",
    1166: "riboflavin_mg",
    1175: "vitamin_b6_mg",
    1178: "vitamin_b12_ug",
    1167: "niacin_mg",
    1170: "pantothenic_acid_mg",
    1176: "biotin_ug",
    1177: "folate_ug",
    1186: "folic_acid_ug",
    1187: "folate_food_ug",
    1190: "folate_dfe_ug",
    1188: "folate_5_mthf_ug",
    1191: "folate_10_formyl_ug",
    1192: "folate_5_formyl_ug",
    1246: "vitamin_b12_added_ug",
    1180: "choline_mg",
    1194: "choline_free_mg",
    1195: "choline_phosphocholine_mg",
    1196: "choline_phosphatidylcholine_mg",
    1197: "choline_glycerophosphocholine_mg",
    1199: "choline_sphingomyelin_mg",
    1222: "alanine_g",
    1220: "arginine_g",
    1223: "aspartic_acid_g",
    1216: "cystine_g",
    1224: "glutamic_acid_g",
    1225: "glycine_g",
    1221: "histidine_g",
    1228: "hydroxyproline_g",
    1212: "isoleucine_g",
    1213: "leucine_g",
    1214: "lysine_g",
    1215: "methionine_g",
    1217: "phenylalanine_g",
    1226: "proline_g",
    1227: "serine_g",
    1211: "threonine_g",
    1210: "tryptophan_g",
    1218: "tyrosine_g",
    1219: "valine_g",
}

NUTRIENT_PRIORITY = {
    2047: 1,
    2048: 2,
    1008: 3,
}

DEFAULT_USDA_SOURCE = "food_data_central"

# Top-level key in an FDC JSON export → our source code.
DATASET_KEY_SOURCES = {
    "SurveyFoods": "usda_fndds",
    "FoundationFoods": "usda_foundation",
    "SRLegacyFoods": "usda_sr_legacy",
    "BrandedFoods": "usda_branded",
}

# Per-record `dataType` value (lowercased) → our source code.
DATA_TYPE_SOURCES = {
    "survey (fndds)": "usda_fndds",
    "foundation": "usda_foundation",
    "sr legacy": "usda_sr_legacy",
    "branded": "usda_branded",
}

_UNSPECIFIED_MEASURES = {"", "undetermined", "quantity not specified"}


def usda_source_for(raw: dict, default: str = DEFAULT_USDA_SOURCE) -> str:
    """Resolve a single FDC record to a source code via its `dataType`."""
    data_type = (raw.get("dataType") or "").strip().lower()
    return DATA_TYPE_SOURCES.get(data_type, default)


def _serving_from_portions(raw: dict) -> tuple[float | None, str | None]:
    """Pick the first usable household measure from an FDC record.

    FNDDS ships `portionDescription` ("1 cup"); SR Legacy and Foundation ship
    an `amount` plus a `modifier` or `measureUnit`. Portions with no gram
    weight or an unspecified measure are skipped.
    """
    for portion in raw.get("foodPortions") or []:
        gram_weight = portion.get("gramWeight")
        if not gram_weight:
            continue
        text = (portion.get("portionDescription") or "").strip()
        if text.lower() in _UNSPECIFIED_MEASURES:
            text = ""
        if not text:
            measure = (portion.get("modifier") or "").strip()
            if measure.lower() in _UNSPECIFIED_MEASURES:
                measure = (portion.get("measureUnit") or {}).get("name", "").strip()
            if measure.lower() in _UNSPECIFIED_MEASURES:
                continue
            amount = portion.get("amount")
            text = f"{amount:g} {measure}".strip() if amount else measure
        try:
            return float(gram_weight), text or None
        except (TypeError, ValueError):
            continue
    return None, None


def normalize_usda_food(raw: dict, *, source: str | None = None) -> dict:
    nutrients: dict[str, float] = {}
    priorities: dict[str, int] = {}
    for fn in raw.get("foodNutrients", []):
        # Support both flat nutrientId (some formats) and nested nutrient.id (SR Legacy, Foundation)
        nid = fn.get("nutrientId") or fn.get("nutrient", {}).get("id")
        if nid in NUTRIENT_MAP:
            field = NUTRIENT_MAP[nid]
            priority = NUTRIENT_PRIORITY.get(nid, 0)
            amount = fn.get("amount")
            if amount is None:
                amount = fn.get("value")
            if amount is None:
                continue
            if priority >= priorities.get(field, -1):
                nutrients[field] = amount
                priorities[field] = priority

    serving_grams, serving_text = _serving_from_portions(raw)

    return {
        "source": source or usda_source_for(raw),
        "source_code": str(raw.get("fdcId", "")),
        "name": raw.get("description", ""),
        "brand": raw.get("brandName") or None,
        "barcode": raw.get("gtinUpc") or None,
        "image_url": None,
        "serving_quantity": serving_grams,
        "serving_unit": "g" if serving_grams else None,
        "serving_size_text": serving_text,
        # A nutrient the dataset does not report stays None: unknown, not zero.
        **{k: nutrients.get(k) for k in NUTRIENT_MAP.values()},
    }
