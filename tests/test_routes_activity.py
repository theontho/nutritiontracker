def test_import_steps_creates_daily_activity(client):
    payload = {
        "source": "apple_shortcuts",
        "observed_at": "2026-05-19T14:00:00-07:00",
        "period_start": "2026-05-19T00:00:00-07:00",
        "period_end": "2026-05-19T14:00:00-07:00",
        "steps_total_today": 5234,
        "timezone": "America/Los_Angeles",
    }
    r = client.post("/imports/activity/steps", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["steps"] == 5234
    assert data["source"] == "apple_shortcuts"
    assert data["anomaly_flag"] is False


def test_import_steps_higher_replaces(client):
    payload = {
        "source": "apple_shortcuts",
        "observed_at": "2026-05-19T13:00:00-07:00",
        "period_start": "2026-05-19T00:00:00-07:00",
        "period_end": "2026-05-19T13:00:00-07:00",
        "steps_total_today": 4000,
        "timezone": "America/Los_Angeles",
    }
    client.post("/imports/activity/steps", json=payload)

    payload2 = {**payload, "observed_at": "2026-05-19T14:00:00-07:00",
                "period_end": "2026-05-19T14:00:00-07:00",
                "steps_total_today": 5234}
    r = client.post("/imports/activity/steps", json=payload2)
    assert r.status_code == 200
    assert r.json()["steps"] == 5234
    assert r.json()["anomaly_flag"] is False


def test_import_steps_anomaly_flag(client):
    payload = {
        "source": "apple_shortcuts",
        "observed_at": "2026-05-19T13:00:00-07:00",
        "period_start": "2026-05-19T00:00:00-07:00",
        "period_end": "2026-05-19T13:00:00-07:00",
        "steps_total_today": 5000,
        "timezone": "America/Los_Angeles",
    }
    client.post("/imports/activity/steps", json=payload)

    # Later observation with LOWER steps → anomaly
    payload2 = {**payload, "observed_at": "2026-05-19T14:00:00-07:00",
                "period_end": "2026-05-19T14:00:00-07:00",
                "steps_total_today": 3000}
    r = client.post("/imports/activity/steps", json=payload2)
    assert r.status_code == 200
    assert r.json()["steps"] == 5000  # unchanged
    assert r.json()["anomaly_flag"] is True


def test_get_daily_activity(client):
    payload = {
        "source": "apple_shortcuts",
        "observed_at": "2026-05-19T14:00:00-07:00",
        "period_start": "2026-05-19T00:00:00-07:00",
        "period_end": "2026-05-19T14:00:00-07:00",
        "steps_total_today": 7000,
        "timezone": "America/Los_Angeles",
    }
    client.post("/imports/activity/steps", json=payload)
    r = client.get("/activity/daily/2026-05-19")
    assert r.status_code == 200
    assert r.json()["steps"] == 7000


def test_get_daily_activity_not_found(client):
    r = client.get("/activity/daily/2026-01-01")
    assert r.status_code == 404


def test_get_activity_range(client):
    for obs_at, steps in [("2026-05-19T14:00:00-07:00", 6000), ("2026-05-20T14:00:00-07:00", 8000)]:
        client.post("/imports/activity/steps", json={
            "source": "apple_shortcuts",
            "observed_at": obs_at,
            "period_start": obs_at[:10] + "T00:00:00-07:00",
            "period_end": obs_at,
            "steps_total_today": steps,
            "timezone": "America/Los_Angeles",
        })
    r = client.get("/activity/range?start=2026-05-19&end=2026-05-20")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_daily_stats_includes_activity(client):
    payload = {
        "source": "apple_shortcuts",
        "observed_at": "2026-05-19T14:00:00-07:00",
        "period_start": "2026-05-19T00:00:00-07:00",
        "period_end": "2026-05-19T14:00:00-07:00",
        "steps_total_today": 9000,
        "timezone": "America/Los_Angeles",
    }
    client.post("/imports/activity/steps", json=payload)
    r = client.get("/stats/daily/2026-05-19")
    assert r.status_code == 200
    assert r.json()["activity"]["steps"] == 9000


def test_daily_stats_no_activity_is_null(client):
    r = client.get("/stats/daily/2020-01-01")
    assert r.status_code == 200
    assert r.json()["activity"] is None
