from app.repositories.foods import FoodRepository
from app.services.food_search import FoodSearchService


def test_dedup_by_barcode(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    repo.create(source="open_food_facts", name="Banana", barcode="123", calories_kcal=89, protein_g=1.1)
    repo.create(source="food_data_central", name="Banana, raw", barcode="123", calories_kcal=89, protein_g=1.1, fiber_g=2.6)
    svc = FoodSearchService(repo)
    results = svc.search("banana")
    # Should deduplicate — prefer FDC because it has more nutrient data (fiber_g)
    assert len(results) == 1
    assert results[0]["fiber_g"] == 2.6


def test_dedup_by_name(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    repo.create(source="open_food_facts", name="Chicken Breast", calories_kcal=165)
    repo.create(source="food_data_central", name="Chicken Breast", calories_kcal=165, protein_g=31)
    svc = FoodSearchService(repo)
    results = svc.search("chicken breast")
    assert len(results) == 1


def test_no_dedup_different_foods(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    repo.create(source="open_food_facts", name="Banana")
    repo.create(source="food_data_central", name="Banana Chips")
    svc = FoodSearchService(repo)
    results = svc.search("banana")
    assert len(results) == 2
