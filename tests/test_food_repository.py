import pytest
from app.repositories.foods import FoodRepository


@pytest.fixture
def repo(db):
    r = FoodRepository(db)
    r.ensure_fts()
    return r


def test_create_and_get(repo):
    food_id = repo.create(
        source="custom", name="Banana", calories_kcal=89, protein_g=1.1,
        carbs_g=22.8, fat_g=0.3,
    )
    food = repo.get(food_id)
    assert food["name"] == "Banana"
    assert food["calories_kcal"] == 89


def test_get_nonexistent_returns_none(repo):
    assert repo.get(9999) is None


def test_search_by_name(repo):
    repo.create(source="custom", name="Chicken Breast Grilled")
    repo.create(source="custom", name="Chicken Thigh")
    repo.create(source="custom", name="Banana")
    results = repo.search("chicken")
    assert len(results) == 2


def test_search_prefix(repo):
    repo.create(source="custom", name="Broccoli")
    results = repo.search("broc")
    assert len(results) == 1
    assert results[0]["name"] == "Broccoli"


def test_search_with_source_filter(repo):
    repo.create(source="open_food_facts", name="Oats OFF")
    repo.create(source="food_data_central", name="Oats USDA")
    results = repo.search("oats", source="food_data_central")
    assert len(results) == 1
    assert results[0]["name"] == "Oats USDA"


def test_search_limit_offset(repo):
    for i in range(10):
        repo.create(source="custom", name=f"Apple Variety {i}")
    results = repo.search("apple", limit=3, offset=0)
    assert len(results) == 3
    results2 = repo.search("apple", limit=3, offset=3)
    assert len(results2) == 3
    assert results[0]["id"] != results2[0]["id"]


def test_barcode_lookup(repo):
    repo.create(source="open_food_facts", name="Granola Bar", barcode="1234567890")
    food = repo.get_by_barcode("1234567890")
    assert food["name"] == "Granola Bar"


def test_update_food(repo):
    food_id = repo.create(source="custom", name="Old Name")
    repo.update(food_id, name="New Name", protein_g=25)
    food = repo.get(food_id)
    assert food["name"] == "New Name"
    assert food["protein_g"] == 25


def test_delete_food(repo):
    food_id = repo.create(source="custom", name="To Delete")
    repo.delete(food_id)
    assert repo.get(food_id) is None
