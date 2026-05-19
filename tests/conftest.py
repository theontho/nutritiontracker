import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_schema


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr("app.database.get_connection", lambda *args, **kwargs: db)
    with TestClient(app) as c:
        yield c
