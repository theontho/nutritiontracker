def test_create_journal_entry(client):
    r = client.post("/journal", json={
        "date": "2026-05-19",
        "body": "Good food day.",
        "tags": ["recovery"],
        "mood_score": 7,
        "stress_score": 4,
        "sleep_quality": 6,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["body"] == "Good food day."
    assert data["tags"] == ["recovery"]
    assert data["mood_score"] == 7
    assert data["stress_score"] == 4
    assert data["sleep_quality"] == 6
    assert data["date"] == "2026-05-19"


def test_create_journal_entry_minimal(client):
    r = client.post("/journal", json={
        "date": "2026-05-19",
        "body": "Just a note.",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["tags"] == []
    assert data["mood_score"] is None
    assert data["stress_score"] is None
    assert data["sleep_quality"] is None


def test_get_journal_by_date(client):
    client.post("/journal", json={"date": "2026-05-19", "body": "Entry one."})
    client.post("/journal", json={"date": "2026-05-19", "body": "Entry two."})
    r = client.get("/journal/2026-05-19")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_journal_by_date_empty(client):
    r = client.get("/journal/2020-01-01")
    assert r.status_code == 200
    assert r.json() == []


def test_get_journal_range(client):
    client.post("/journal", json={"date": "2026-05-19", "body": "Day 1."})
    client.post("/journal", json={"date": "2026-05-20", "body": "Day 2."})
    r = client.get("/journal?start=2026-05-19&end=2026-05-20")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["date"] == "2026-05-19"
    assert data[1]["date"] == "2026-05-20"


def test_update_journal_entry(client):
    r = client.post("/journal", json={"date": "2026-05-19", "body": "Original."})
    entry_id = r.json()["id"]
    r2 = client.patch(f"/journal/{entry_id}", json={"mood_score": 8, "body": "Updated."})
    assert r2.status_code == 200
    data = r2.json()
    assert data["mood_score"] == 8
    assert data["body"] == "Updated."


def test_update_journal_entry_not_found(client):
    r = client.patch("/journal/9999", json={"mood_score": 5})
    assert r.status_code == 404


def test_update_journal_entry_no_fields(client):
    r = client.post("/journal", json={"date": "2026-05-19", "body": "Test."})
    entry_id = r.json()["id"]
    r2 = client.patch(f"/journal/{entry_id}", json={})
    assert r2.status_code == 400


def test_delete_journal_entry(client):
    r = client.post("/journal", json={"date": "2026-05-19", "body": "To delete."})
    entry_id = r.json()["id"]
    r2 = client.delete(f"/journal/{entry_id}")
    assert r2.status_code == 204
    r3 = client.get("/journal/2026-05-19")
    assert r3.json() == []


def test_delete_journal_entry_not_found(client):
    r = client.delete("/journal/9999")
    assert r.status_code == 404


def test_create_journal_entry_score_out_of_range(client):
    r = client.post("/journal", json={
        "date": "2026-05-19",
        "body": "Test.",
        "mood_score": 0,
    })
    assert r.status_code == 422


def test_create_journal_entry_score_too_high(client):
    r = client.post("/journal", json={
        "date": "2026-05-19",
        "body": "Test.",
        "stress_score": 11,
    })
    assert r.status_code == 422


def test_create_journal_entry_score_boundary_valid(client):
    r = client.post("/journal", json={
        "date": "2026-05-19",
        "body": "Test.",
        "mood_score": 1,
        "stress_score": 10,
        "sleep_quality": 5,
    })
    assert r.status_code == 201
