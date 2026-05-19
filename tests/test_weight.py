import pytest
from app.repositories.weight import WeightRepository


@pytest.fixture
def repo(db):
    return WeightRepository(db)


def test_create_and_get(repo):
    wid = repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    entry = repo.get(wid)
    assert entry["weight_kg"] == 85.5


def test_list_by_date(repo):
    repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    entries = repo.list_by_date_range(user_id=1, start="2026-05-19", end="2026-05-19")
    assert len(entries) == 1


def test_list_by_range(repo):
    repo.create(user_id=1, date="2026-05-18", weight_kg=86)
    repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    repo.create(user_id=1, date="2026-05-20", weight_kg=85)
    entries = repo.list_by_date_range(user_id=1, start="2026-05-18", end="2026-05-20")
    assert len(entries) == 3


def test_update(repo):
    wid = repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    repo.update(wid, weight_kg=84.0)
    assert repo.get(wid)["weight_kg"] == 84.0


def test_delete(repo):
    wid = repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    repo.delete(wid)
    assert repo.get(wid) is None
