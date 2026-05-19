import pytest
from app.repositories.foods import FoodRepository
from app.repositories.diary import DiaryRepository


@pytest.fixture
def food_repo(db):
    r = FoodRepository(db)
    r.ensure_fts()
    return r


@pytest.fixture
def diary_repo(db):
    return DiaryRepository(db)


@pytest.fixture
def banana_id(food_repo):
    return food_repo.create(source="custom", name="Banana", calories_kcal=89, protein_g=1.1, carbs_g=22.8, fat_g=0.3)


def test_create_and_get_entry(diary_repo, banana_id):
    entry_id = diary_repo.create(
        user_id=1, date="2026-05-19", meal_type="breakfast",
        food_id=banana_id, food_snapshot={"name": "Banana"},
        amount=1, unit="serving", grams=118,
        nutrients_total={"calories_kcal": 105},
    )
    entry = diary_repo.get(entry_id)
    assert entry is not None
    assert entry["meal_type"] == "breakfast"


def test_list_by_date(diary_repo, banana_id):
    diary_repo.create(
        user_id=1, date="2026-05-19", meal_type="breakfast",
        food_id=banana_id, food_snapshot={}, amount=1, unit="g", grams=100,
        nutrients_total={},
    )
    diary_repo.create(
        user_id=1, date="2026-05-20", meal_type="lunch",
        food_id=banana_id, food_snapshot={}, amount=1, unit="g", grams=100,
        nutrients_total={},
    )
    entries = diary_repo.list_by_date(user_id=1, date="2026-05-19")
    assert len(entries) == 1


def test_update_entry(diary_repo, banana_id):
    entry_id = diary_repo.create(
        user_id=1, date="2026-05-19", meal_type="breakfast",
        food_id=banana_id, food_snapshot={}, amount=1, unit="g", grams=100,
        nutrients_total={},
    )
    diary_repo.update(entry_id, amount=2, grams=200)
    entry = diary_repo.get(entry_id)
    assert entry["amount"] == 2


def test_delete_entry(diary_repo, banana_id):
    entry_id = diary_repo.create(
        user_id=1, date="2026-05-19", meal_type="breakfast",
        food_id=banana_id, food_snapshot={}, amount=1, unit="g", grams=100,
        nutrients_total={},
    )
    diary_repo.delete(entry_id)
    assert diary_repo.get(entry_id) is None
