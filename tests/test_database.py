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


def test_schema_records_definition_privacy_flags():
    import sqlite3

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    for table in ("event_types", "foods", "recipes", "favorite_meals"):
        columns = {row[1]: row for row in conn.execute(f"PRAGMA table_info({table})")}
        assert columns["is_private"][3] == 1
        assert columns["is_private"][4] == "0"
    conn.close()


def test_schema_records_structured_mood_events():
    import sqlite3

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    type_columns = {
        row[1]: row for row in conn.execute("PRAGMA table_info(event_types)")
    }
    event_columns = {row[1]: row for row in conn.execute("PRAGMA table_info(events)")}
    conn.close()

    assert type_columns["measurement_kind"][4] == "'generic'"
    assert "mood" in event_columns
