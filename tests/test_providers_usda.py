from app.providers.food_data_central import NUTRIENT_MAP, normalize_usda_food


USDA_169768_ADDITIONAL_NUTRIENTS = {
    1062: "energy_kj",
    1198: "betaine_mg",
    1104: "vitamin_a_iu",
    1110: "vitamin_d_iu",
    1259: "butyric_acid_g",
    1260: "caproic_acid_g",
    1261: "caprylic_acid_g",
    1262: "capric_acid_g",
    1263: "lauric_acid_g",
    1264: "myristic_acid_g",
    1299: "pentadecylic_acid_g",
    1265: "palmitic_acid_g",
    1300: "margaric_acid_g",
    1266: "stearic_acid_g",
    1267: "arachidic_acid_g",
    1273: "behenic_acid_g",
    1301: "lignoceric_acid_g",
    1274: "myristoleic_acid_g",
    1333: "pentadecenoic_acid_g",
    1275: "palmitoleic_acid_g",
    1314: "sapienic_acid_g",
    1323: "heptadecenoic_acid_g",
    1268: "oleic_acid_g",
    1315: "oleic_acid_cis_g",
    1277: "gondoic_acid_g",
    1279: "docosenoic_acid_g",
    1317: "erucic_acid_g",
    1312: "nervonic_acid_g",
    1269: "pufa_18_2_g",
    1311: "conjugated_linoleic_acid_g",
    1270: "pufa_18_3_g",
    1321: "gamma_linolenic_acid_g",
    1409: "pufa_18_3i_g",
    1276: "stearidonic_acid_g",
    1313: "eicosadienoic_acid_g",
    1325: "pufa_20_3_g",
    1405: "eicosatrienoic_acid_g",
    1406: "dihomo_gamma_linolenic_acid_g",
    1411: "adrenic_acid_g",
    1280: "dpa_g",
    1329: "trans_monoenoic_fat_g",
    1303: "trans_palmitoleic_acid_g",
    1304: "trans_oleic_acid_g",
    1305: "trans_erucic_acid_g",
    1306: "trans_linoleic_acid_g",
    1331: "trans_polyenoic_fat_g",
    1058: "theobromine_mg",
}


def test_normalize_usda_food():
    raw = {
        "fdcId": 12345,
        "description": "Banana, raw",
        "brandName": None,
        "gtinUpc": "",
        "foodNutrients": [
            {"nutrientId": 1008, "value": 89},  # Energy
            {"nutrientId": 1003, "value": 1.1},  # Protein
            {"nutrientId": 1005, "value": 22.8},  # Carbs
            {"nutrientId": 1004, "value": 0.3},  # Fat
            {"nutrientId": 1057, "value": 1.2},  # Caffeine
            {"nutrientId": 1166, "value": 0.07},  # Riboflavin
            {"nutrientId": 1176, "value": 0.2},  # Biotin
            {"nutrientId": 1103, "value": 1.1},  # Selenium
            {"nutrientId": 1105, "value": 12.0},  # Retinol
            {"nutrientId": 1107, "value": 26.0},  # Beta-carotene
            {"nutrientId": 1111, "value": 0.4},  # Vitamin D2
            {"nutrientId": 1112, "value": 1.5},  # Vitamin D3
            {"nutrientId": 1126, "value": 0.8},  # Gamma tocopherol
            {"nutrientId": 1242, "value": 1.25},  # Added vitamin E
            {"nutrientId": 1183, "value": 2.0},  # Menaquinone-4
            {"nutrientId": 1190, "value": 19.0},  # Folate DFE
            {"nutrientId": 1194, "value": 3.0},  # Free choline
            {"nutrientId": 1051, "value": 74.9},  # Water
            {"nutrientId": 1010, "value": 2.4},  # Sucrose
            {"nutrientId": 1082, "value": 0.7},  # Soluble fiber
            {"nutrientId": 1099, "value": 2.2},  # Fluoride
            {"nutrientId": 1102, "value": 4.0},  # Molybdenum
            {"nutrientId": 1272, "value": 0.03},  # DHA
            {"nutrientId": 1404, "value": 0.04},  # ALA
            {"nutrientId": 1213, "value": 0.08},  # Leucine
        ],
    }
    food = normalize_usda_food(raw)
    assert food["name"] == "Banana, raw"
    assert food["source"] == "food_data_central"
    assert food["source_code"] == "12345"
    assert food["calories_kcal"] == 89
    assert food["protein_g"] == 1.1
    assert food["caffeine_mg"] == 1.2
    assert food["riboflavin_mg"] == 0.07
    assert food["biotin_ug"] == 0.2
    assert food["selenium_ug"] == 1.1
    assert food["retinol_ug"] == 12.0
    assert food["beta_carotene_ug"] == 26.0
    assert food["vitamin_d2_ug"] == 0.4
    assert food["vitamin_d3_ug"] == 1.5
    assert food["gamma_tocopherol_mg"] == 0.8
    assert food["vitamin_e_added_mg"] == 1.25
    assert food["menaquinone_4_ug"] == 2.0
    assert food["folate_dfe_ug"] == 19.0
    assert food["choline_free_mg"] == 3.0
    assert food["water_g"] == 74.9
    assert food["sucrose_g"] == 2.4
    assert food["soluble_fiber_g"] == 0.7
    assert food["fluoride_ug"] == 2.2
    assert food["molybdenum_ug"] == 4.0
    assert food["dha_g"] == 0.03
    assert food["alpha_linolenic_acid_g"] == 0.04
    assert food["leucine_g"] == 0.08
    assert food.get("menaquinone_7_ug") is None


def test_normalize_handles_missing_nutrients():
    raw = {
        "fdcId": 99,
        "description": "Mystery food",
        "foodNutrients": [],
    }
    food = normalize_usda_food(raw)
    assert food["calories_kcal"] is None


def test_normalize_preserves_all_additional_usda_169768_nutrients():
    assert {
        nutrient_id: NUTRIENT_MAP[nutrient_id]
        for nutrient_id in USDA_169768_ADDITIONAL_NUTRIENTS
    } == USDA_169768_ADDITIONAL_NUTRIENTS
    raw = {
        "fdcId": 169768,
        "description": "Potatoes, mashed, ready-to-eat",
        "foodNutrients": [
            {"nutrient": {"id": nutrient_id}, "amount": index / 1000}
            for index, nutrient_id in enumerate(
                USDA_169768_ADDITIONAL_NUTRIENTS, start=1
            )
        ],
    }

    food = normalize_usda_food(raw)

    for index, field in enumerate(USDA_169768_ADDITIONAL_NUTRIENTS.values(), start=1):
        assert food[field] == index / 1000


def test_normalize_keeps_measured_zero():
    """An analysed zero must stay 0 so it is distinguishable from unknown."""
    raw = {
        "fdcId": 100,
        "description": "Vegetable oil",
        "foodNutrients": [
            {"nutrient": {"id": 1003}, "amount": 0},
            {"nutrient": {"id": 1004}, "amount": 100},
        ],
    }
    food = normalize_usda_food(raw)
    assert food["protein_g"] == 0
    assert food["fat_g"] == 100
    assert food["vitamin_k_ug"] is None
    assert food["protein_g"] == 0


def test_normalize_supports_foundation_energy_ids_with_precedence():
    raw = {
        "fdcId": 100,
        "description": "Foundation food",
        "foodNutrients": [
            {"nutrient": {"id": 1008}, "amount": 90},
            {"nutrient": {"id": 2047}, "amount": 80},
            {"nutrient": {"id": 2048}, "amount": 85},
        ],
    }

    food = normalize_usda_food(raw)

    assert food["calories_kcal"] == 90


def test_normalize_detects_fndds_from_data_type():
    raw = {
        "fdcId": 321,
        "dataType": "Survey (FNDDS)",
        "description": "Milk, whole",
        "foodNutrients": [{"nutrient": {"id": 1003}, "amount": 3.2}],
    }
    assert normalize_usda_food(raw)["source"] == "usda_fndds"


def test_normalize_detects_each_usda_dataset():
    cases = {
        "Survey (FNDDS)": "usda_fndds",
        "Foundation": "usda_foundation",
        "SR Legacy": "usda_sr_legacy",
        "Branded": "usda_branded",
    }
    for data_type, expected in cases.items():
        raw = {"fdcId": 1, "dataType": data_type, "description": "x"}
        assert normalize_usda_food(raw)["source"] == expected


def test_normalize_falls_back_to_generic_source():
    raw = {"fdcId": 1, "description": "No dataType here"}
    assert normalize_usda_food(raw)["source"] == "food_data_central"


def test_explicit_source_overrides_data_type():
    raw = {"fdcId": 1, "dataType": "Foundation", "description": "x"}
    assert normalize_usda_food(raw, source="usda_fndds")["source"] == "usda_fndds"


def test_normalize_reads_fndds_portion():
    raw = {
        "fdcId": 5,
        "dataType": "Survey (FNDDS)",
        "description": "Milk, whole",
        "foodNutrients": [],
        "foodPortions": [{"portionDescription": "1 cup", "gramWeight": 244}],
    }
    food = normalize_usda_food(raw)
    assert food["serving_quantity"] == 244
    assert food["serving_unit"] == "g"
    assert food["serving_size_text"] == "1 cup"


def test_normalize_reads_sr_legacy_portion():
    raw = {
        "fdcId": 6,
        "dataType": "SR Legacy",
        "description": "Banana, raw",
        "foodNutrients": [],
        "foodPortions": [
            {"amount": 1, "gramWeight": 118, "modifier": "cup, sliced"},
        ],
    }
    food = normalize_usda_food(raw)
    assert food["serving_quantity"] == 118
    assert food["serving_size_text"] == "1 cup, sliced"


def test_normalize_skips_unusable_portions():
    raw = {
        "fdcId": 7,
        "description": "Something",
        "foodNutrients": [],
        "foodPortions": [
            {"portionDescription": "Quantity not specified", "gramWeight": 100},
            {"portionDescription": "1 tbsp", "gramWeight": 14},
        ],
    }
    food = normalize_usda_food(raw)
    assert food["serving_quantity"] == 14
    assert food["serving_size_text"] == "1 tbsp"


def test_normalize_without_portions_leaves_serving_unset():
    raw = {"fdcId": 8, "description": "Plain", "foodNutrients": []}
    food = normalize_usda_food(raw)
    assert food["serving_quantity"] is None
    assert food["serving_unit"] is None
