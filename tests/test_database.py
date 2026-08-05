from app.database import init_schema


def test_schema_includes_expanded_nutrients():
    import sqlite3

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(foods)")}
    conn.close()

    assert {
        "caffeine_mg",
        "riboflavin_mg",
        "biotin_ug",
        "chromium_ug",
        "stearic_acid_g",
        "oleic_acid_cis_g",
        "dpa_g",
        "betaine_mg",
        "theobromine_mg",
    } <= columns


def test_schema_records_diary_amount_method():
    import sqlite3

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(diary_entries)")}
    conn.close()

    assert columns["amount_method"][4] == "'unspecified'"


def test_schema_records_food_source_data_method():
    import sqlite3

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(food_sources)")}
    conn.close()

    assert columns["data_method"][4] == "'unspecified'"
