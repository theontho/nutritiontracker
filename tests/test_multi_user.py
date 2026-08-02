import hashlib
import secrets

import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.repositories.foods import FoodRepository


def _admin_headers():
    return {"Authorization": "Bearer admin-token"}


def _create_user(client, name: str) -> dict:
    response = client.post("/users", headers=_admin_headers(), json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_user_tokens_isolate_personal_data_and_custom_foods(client, db, monkeypatch):
    monkeypatch.setattr(settings, "bearer_token", "admin-token")
    monkeypatch.setattr(settings, "multi_user_enabled", True)
    user = _create_user(client, "Second user")
    user_headers = {"Authorization": f"Bearer {user['token']}"}

    shared_food_id = FoodRepository(db).create(
        source="food_data_central", name="Shared banana", calories_kcal=89
    )
    custom_response = client.post(
        "/foods",
        headers=user_headers,
        json={"source": "custom", "name": "Private blend"},
    )
    assert custom_response.status_code == 201
    custom_food_id = custom_response.json()["id"]

    assert client.get(f"/foods/{custom_food_id}", headers=_admin_headers()).status_code == 404
    assert client.get(f"/foods/{custom_food_id}", headers=user_headers).status_code == 200

    diary_response = client.post(
        "/diary/2026-08-01/entries",
        headers=user_headers,
        json={
            "food_id": shared_food_id,
            "amount": 100,
            "unit": "g",
            "meal_type": "breakfast",
        },
    )
    assert diary_response.status_code == 201

    assert client.get("/diary/2026-08-01", headers=_admin_headers()).json() == []
    assert len(client.get("/diary/2026-08-01", headers=user_headers).json()) == 1


def test_only_admin_can_create_users(client, monkeypatch):
    monkeypatch.setattr(settings, "bearer_token", "admin-token")
    monkeypatch.setattr(settings, "multi_user_enabled", True)
    user = _create_user(client, "Second user")

    response = client.post(
        "/users",
        headers={"Authorization": f"Bearer {user['token']}"},
        json={"name": "Third user"},
    )

    assert response.status_code == 403


def test_multi_user_routes_are_disabled_by_default(client, monkeypatch):
    monkeypatch.setattr(settings, "bearer_token", "admin-token")
    monkeypatch.setattr(settings, "multi_user_enabled", False)

    response = client.get("/users/me", headers=_admin_headers())

    assert response.status_code == 404


def test_single_user_mode_rejects_alternate_user_token(client, db, monkeypatch):
    monkeypatch.setattr(settings, "bearer_token", "admin-token")
    monkeypatch.setattr(settings, "multi_user_enabled", False)
    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO users (name, token_hash) VALUES (?, ?)",
        ("Second user", hashlib.sha256(token.encode()).hexdigest()),
    )
    db.commit()

    response = client.get(
        "/diary/2026-08-01", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_multi_user_without_a_token_is_refused_at_startup():
    """The combination would make every anonymous caller an admin."""
    with pytest.raises(ValidationError, match="NT_MULTI_USER_ENABLED requires NT_BEARER_TOKEN"):
        Settings(multi_user_enabled=True, bearer_token=None)


def test_unauthenticated_deployment_grants_no_admin(client, monkeypatch):
    monkeypatch.setattr(settings, "bearer_token", None)
    monkeypatch.setattr(settings, "multi_user_enabled", True)

    assert client.get("/users").status_code == 403
    assert client.post("/users", json={"name": "Intruder"}).status_code == 403


def test_default_user_token_cannot_be_rotated(client, monkeypatch):
    monkeypatch.setattr(settings, "bearer_token", "admin-token")
    monkeypatch.setattr(settings, "multi_user_enabled", True)

    response = client.post(
        f"/users/{settings.default_user_id}/token", headers=_admin_headers()
    )

    assert response.status_code == 409
    assert "NT_BEARER_TOKEN" in response.json()["detail"]


def test_other_user_tokens_can_still_be_rotated(client, monkeypatch):
    monkeypatch.setattr(settings, "bearer_token", "admin-token")
    monkeypatch.setattr(settings, "multi_user_enabled", True)
    user = _create_user(client, "Rotatable")

    response = client.post(f"/users/{user['id']}/token", headers=_admin_headers())

    assert response.status_code == 200
    assert response.json()["token"] != user["token"]
