from app.database import init_schema


def test_schema_includes_expanded_nutrients():
    import sqlite3

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(foods)")}
    conn.close()

    assert {"caffeine_mg", "riboflavin_mg", "biotin_ug", "chromium_ug"} <= columns
