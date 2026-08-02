from app.config import settings
from app.repositories.foods import FoodRepository


def _admin_headers():
    return {"Authorization": "Bearer admin-token"}


def _create_user(client, name: str) -> dict:
    response = client.post("/users", headers=_admin_headers(), json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_user_tokens_isolate_personal_data_and_custom_foods(client, db, monkeypatch):
    monkeypatch.setattr(settings, "bearer_token", "admin-token")
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
    user = _create_user(client, "Second user")

    response = client.post(
        "/users",
        headers={"Authorization": f"Bearer {user['token']}"},
        json={"name": "Third user"},
    )

    assert response.status_code == 403
