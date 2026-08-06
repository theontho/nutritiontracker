import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_schema


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr("app.main.get_connection", lambda *args, **kwargs: db)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def loopback_client(db, monkeypatch):
    monkeypatch.setattr("app.main.get_connection", lambda *args, **kwargs: db)
    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        yield c


@pytest.fixture
def remote_client(db, monkeypatch):
    monkeypatch.setattr("app.main.get_connection", lambda *args, **kwargs: db)
    with TestClient(app, client=("192.0.2.10", 50000)) as c:
        yield c
