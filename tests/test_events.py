"""Events: a generic log of things that happened, with user-defined types.

Nothing here is nutrition- or fitness-specific by design; the type registry is
empty until the user fills it.
"""

import pytest


def _make_type(client, name="Red light therapy", unit="minutes", notes=None):
    response = client.post(
        "/events/types", json={"name": name, "unit": unit, "notes": notes}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_no_event_types_are_seeded(client):
    """The registry starts empty -- people define their own categories."""
    response = client.get("/events/types")
    assert response.status_code == 200
    assert response.json() == []


def test_define_a_type_and_log_an_event(client):
    event_type = client.post(
        "/events/types",
        json={
            "name": "Red light therapy",
            "unit": "minutes",
            "is_private": True,
        },
    ).json()
    assert event_type["name"] == "Red light therapy"
    assert event_type["unit"] == "minutes"
    assert event_type["is_private"] is True

    response = client.post(
        "/events",
        json={
            "event_type_id": event_type["id"],
            "date": "2026-08-02",
            "value": 5,
            "notes": "panel at 18 inches",
        },
    )
    assert response.status_code == 201, response.text
    event = response.json()
    assert event["event_type_name"] == "Red light therapy"
    assert event["event_type_is_private"] is True
    assert event["value"] == 5
    assert event["unit"] == "minutes"
    assert event["notes"] == "panel at 18 inches"


def test_event_inherits_the_type_unit_but_can_override_it(client):
    event_type = _make_type(client, unit="minutes")

    inherited = client.post(
        "/events", json={"event_type_id": event_type["id"], "date": "2026-08-02"}
    ).json()
    assert inherited["unit"] == "minutes"

    overridden = client.post(
        "/events",
        json={
            "event_type_id": event_type["id"],
            "date": "2026-08-02",
            "value": 2,
            "unit": "hours",
        },
    ).json()
    assert overridden["unit"] == "hours"


def test_an_event_may_have_no_value_at_all(client):
    """Some events are just "this happened" -- a number is not required."""
    event_type = _make_type(client, name="Cold plunge", unit=None)
    event = client.post(
        "/events", json={"event_type_id": event_type["id"], "date": "2026-08-02"}
    ).json()
    assert event["value"] is None
    assert event["unit"] is None


def test_a_zero_value_is_kept_as_a_measurement(client):
    """Zero is something you measured, not something you failed to record.

    Anything filtering on truthiness would turn a recorded 0 into "unknown",
    which is a different claim entirely.
    """
    event_type = _make_type(client, name="Alcohol", unit="drinks")
    event = client.post(
        "/events",
        json={"event_type_id": event_type["id"], "date": "2026-08-02", "value": 0},
    ).json()
    assert event["value"] == 0

    fetched = client.get(f"/events/{event['id']}").json()
    assert fetched["value"] == 0


def test_editing_a_type_unit_leaves_logged_events_alone(client):
    """Past readings keep the unit they were recorded in.

    Rewriting them would silently reinterpret a number nobody re-measured.
    """
    event_type = _make_type(client, name="Sauna", unit="minutes")
    event = client.post(
        "/events",
        json={"event_type_id": event_type["id"], "date": "2026-08-02", "value": 20},
    ).json()

    client.patch(f"/events/types/{event_type['id']}", json={"unit": "sessions"})

    assert client.get(f"/events/{event['id']}").json()["unit"] == "minutes"
    assert client.get(f"/events/types/{event_type['id']}").json()["unit"] == "sessions"


def test_event_type_privacy_can_be_updated(client):
    event_type = _make_type(client, name="Personal activity")
    assert event_type["is_private"] is False

    updated = client.patch(
        f"/events/types/{event_type['id']}",
        json={"is_private": True},
    )

    assert updated.status_code == 200
    assert updated.json()["is_private"] is True


def test_mood_events_preserve_dimensions_labels_and_optional_context(client):
    event_type = client.post(
        "/events/types",
        json={"name": "Mood", "measurement_kind": "mood"},
    ).json()

    response = client.post(
        "/events",
        json={
            "event_type_id": event_type["id"],
            "date": "2026-08-07",
            "at": "13:44",
            "mood": {
                "pleasantness": -2,
                "energy": 1,
                "capture_mode": "scheduled",
                "labels": [
                    {"category": "overwhelmed", "intensity": 3},
                    {"category": "tired", "intensity": 2},
                ],
                "stress": 3,
                "motivation": -1,
                "functional_impact": 2,
                "context_tags": ["work", "poor sleep"],
                "body_cues": ["heavy eyes"],
                "regulation": ["situation_change", "reappraisal"],
                "duration_minutes": 90,
            },
            "notes": "Executive functioning is low.",
        },
    )

    assert response.status_code == 201, response.text
    event = response.json()
    assert event["event_type_measurement_kind"] == "mood"
    assert event["mood"] == {
        "version": 2,
        "pleasantness": -2,
        "energy": 1,
        "capture_mode": "scheduled",
        "dimension_source": "reported",
        "labels": [
            {"category": "overwhelmed", "intensity": 3},
            {"category": "tired", "intensity": 2},
        ],
        "stress": 3,
        "motivation": -1,
        "functional_impact": 2,
        "context_tags": ["work", "poor sleep"],
        "body_cues": ["heavy eyes"],
        "regulation": ["situation_change", "reappraisal"],
        "duration_minutes": 90,
    }
    assert client.get(f"/events/{event['id']}").json()["mood"] == event["mood"]


def test_legacy_mood_payload_is_upgraded_for_compatibility(client):
    event_type = client.post(
        "/events/types",
        json={"name": "Mood", "measurement_kind": "mood"},
    ).json()
    response = client.post(
        "/events",
        json={
            "event_type_id": event_type["id"],
            "date": "2026-08-07",
            "mood": {
                "primary": "overwhelmed",
                "secondary": "tired",
                "intensity": 2,
            },
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["mood"] == {
        "version": 2,
        "pleasantness": -2,
        "energy": 2,
        "capture_mode": "spontaneous",
        "dimension_source": "legacy_inferred",
        "labels": [
            {"category": "overwhelmed", "intensity": 2},
            {"category": "tired", "intensity": 2},
        ],
        "stress": None,
        "motivation": None,
        "functional_impact": None,
        "context_tags": [],
        "body_cues": [],
        "regulation": [],
        "duration_minutes": None,
    }


@pytest.mark.parametrize(
    "payload, message",
    [
        ({}, "require structured mood"),
        ({"value": 2}, "do not use value"),
        (
            {"mood": {"primary": "happy", "secondary": "happy"}},
            "mood labels must be unique",
        ),
        (
            {
                "mood": {
                    "pleasantness": 1,
                    "energy": 0,
                    "context_tags": ["work", "WORK"],
                }
            },
            "context_tags must contain unique",
        ),
        (
            {"mood": {"pleasantness": 4, "energy": 0}},
            "Input should be -3, -2, -1, 0, 1, 2 or 3",
        ),
        (
            {
                "mood": {
                    "pleasantness": 1,
                    "energy": 0,
                    "labels": [
                        {"category": category}
                        for category in (
                            "happy",
                            "amused",
                            "excited",
                            "hopeful",
                            "inspired",
                            "proud",
                            "calm",
                        )
                    ],
                }
            },
            "List should have at most 6 items",
        ),
        (
            {
                "mood": {
                    "pleasantness": 1,
                    "energy": 0,
                    "body_cues": [" "],
                }
            },
            "body_cues must not contain blank",
        ),
        (
            {
                "mood": {
                    "pleasantness": 1,
                    "energy": 0,
                    "regulation": ["reappraisal", "reappraisal"],
                }
            },
            "regulation strategies must be unique",
        ),
        (
            {
                "mood": {
                    "pleasantness": 1,
                    "energy": 0,
                    "duration_minutes": 1441,
                }
            },
            "less than or equal to 1440",
        ),
    ],
)
def test_mood_events_reject_incomplete_or_conflicting_data(client, payload, message):
    event_type = client.post(
        "/events/types",
        json={"name": "Mood", "measurement_kind": "mood"},
    ).json()
    response = client.post(
        "/events",
        json={"event_type_id": event_type["id"], "date": "2026-08-07", **payload},
    )

    assert response.status_code == 422
    assert message in response.text


def test_generic_events_reject_structured_mood_data(client):
    event_type = _make_type(client, name="Journal marker")
    response = client.post(
        "/events",
        json={
            "event_type_id": event_type["id"],
            "date": "2026-08-07",
            "mood": {"primary": "calm"},
        },
    )

    assert response.status_code == 422
    assert "requires a mood event type" in response.text


def test_measurement_kind_cannot_change_after_logging(client):
    event_type = _make_type(client, name="Journal marker", unit=None)
    client.post(
        "/events",
        json={"event_type_id": event_type["id"], "date": "2026-08-07"},
    )

    response = client.patch(
        f"/events/types/{event_type['id']}",
        json={"measurement_kind": "mood"},
    )

    assert response.status_code == 409


def test_duplicate_type_names_are_rejected(client):
    _make_type(client, name="Meditation")
    response = client.post("/events/types", json={"name": "Meditation"})
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_blank_type_names_are_rejected(client):
    assert client.post("/events/types", json={"name": "   "}).status_code == 422


def test_logging_against_an_unknown_type_is_rejected(client):
    response = client.post("/events", json={"event_type_id": 999, "date": "2026-08-02"})
    assert response.status_code == 404


def test_a_malformed_date_is_rejected(client):
    event_type = _make_type(client)
    response = client.post(
        "/events", json={"event_type_id": event_type["id"], "date": "02-08-2026"}
    )
    assert response.status_code == 422


def test_deleting_a_type_with_events_is_refused_then_cascades(client):
    event_type = _make_type(client, name="Breathwork")
    client.post(
        "/events",
        json={"event_type_id": event_type["id"], "date": "2026-08-02", "value": 10},
    )

    refused = client.delete(f"/events/types/{event_type['id']}")
    assert refused.status_code == 409
    assert "cascade" in refused.json()["detail"]
    assert client.get("/events").json() != []

    forced = client.delete(f"/events/types/{event_type['id']}?cascade=true")
    assert forced.status_code == 204
    assert client.get("/events").json() == []
    assert client.get("/events/types").json() == []


def test_events_are_filtered_by_date_and_type(client):
    sauna = _make_type(client, name="Sauna", unit="minutes")
    plunge = _make_type(client, name="Cold plunge", unit="minutes")
    for date, type_id in [
        ("2026-08-01", sauna["id"]),
        ("2026-08-02", sauna["id"]),
        ("2026-08-02", plunge["id"]),
        ("2026-08-05", plunge["id"]),
    ]:
        client.post("/events", json={"event_type_id": type_id, "date": date})

    ranged = client.get("/events?start=2026-08-02&end=2026-08-02").json()
    assert len(ranged) == 2

    by_type = client.get(f"/events?event_type_id={sauna['id']}").json()
    assert len(by_type) == 2
    assert {e["event_type_name"] for e in by_type} == {"Sauna"}


def test_summary_totals_by_type_and_counts_unmeasured_events(client):
    event_type = _make_type(client, name="Red light therapy", unit="minutes")
    for value in (5, 10, None):
        payload = {"event_type_id": event_type["id"], "date": "2026-08-02"}
        if value is not None:
            payload["value"] = value
        client.post("/events", json=payload)

    rows = client.get("/events/summary").json()
    assert len(rows) == 1
    assert rows[0]["event_type_name"] == "Red light therapy"
    assert rows[0]["count"] == 3
    assert rows[0]["unmeasured_count"] == 1
    assert rows[0]["total_value"] == 15


def test_summary_never_adds_across_units(client):
    """Minutes and sessions are not the same quantity.

    A single total would invent a number that was never recorded, so each unit
    is reported on its own row.
    """
    event_type = _make_type(client, name="Sauna", unit="minutes")
    client.post(
        "/events",
        json={"event_type_id": event_type["id"], "date": "2026-08-02", "value": 20},
    )
    client.post(
        "/events",
        json={
            "event_type_id": event_type["id"],
            "date": "2026-08-03",
            "value": 1,
            "unit": "sessions",
        },
    )

    rows = client.get("/events/summary").json()
    assert len(rows) == 2
    assert {(r["unit"], r["total_value"]) for r in rows} == {
        ("minutes", 20.0),
        ("sessions", 1.0),
    }


def test_summary_reports_null_when_nothing_was_measured(client):
    """No values recorded is not the same as a total of zero."""
    event_type = _make_type(client, name="Headache", unit=None)
    client.post(
        "/events", json={"event_type_id": event_type["id"], "date": "2026-08-02"}
    )

    row = client.get("/events/summary").json()[0]
    assert row["count"] == 1
    assert row["unmeasured_count"] == 1
    assert row["total_value"] is None


def test_update_and_delete_an_event(client):
    event_type = _make_type(client, name="Walk", unit="km")
    event = client.post(
        "/events",
        json={"event_type_id": event_type["id"], "date": "2026-08-02", "value": 3},
    ).json()

    updated = client.patch(f"/events/{event['id']}", json={"value": 4.5}).json()
    assert updated["value"] == 4.5

    assert client.patch(f"/events/{event['id']}", json={}).status_code == 400
    assert client.delete(f"/events/{event['id']}").status_code == 204
    assert client.get(f"/events/{event['id']}").status_code == 404


@pytest.mark.parametrize("path", ["/events/999", "/events/types/999"])
def test_missing_records_are_404_not_500(client, path):
    assert client.get(path).status_code == 404


def test_events_are_isolated_between_users(client, monkeypatch):
    """One person's log must be invisible to another.

    Event types are user-scoped too, so two people can both define "Sauna"
    without colliding, and neither can read or edit the other's entries.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "bearer_token", "admin-token")
    monkeypatch.setattr(settings, "multi_user_enabled", True)
    admin_headers = {"Authorization": "Bearer admin-token"}

    created = client.post("/users", headers=admin_headers, json={"name": "Second user"})
    assert created.status_code == 201
    other_headers = {"Authorization": f"Bearer {created.json()['token']}"}

    mine = client.post(
        "/events/types",
        headers=admin_headers,
        json={"name": "Sauna", "unit": "minutes"},
    ).json()
    client.post(
        "/events",
        headers=admin_headers,
        json={"event_type_id": mine["id"], "date": "2026-08-02", "value": 20},
    )

    # The same name is available to the other user rather than colliding.
    theirs = client.post(
        "/events/types",
        headers=other_headers,
        json={"name": "Sauna", "unit": "sessions"},
    )
    assert theirs.status_code == 201

    assert client.get("/events", headers=other_headers).json() == []
    assert client.get("/events/summary", headers=other_headers).json() == []
    assert len(client.get("/events/types", headers=other_headers).json()) == 1

    assert (
        client.get(f"/events/types/{mine['id']}", headers=other_headers).status_code
        == 404
    )
    assert (
        client.patch(
            f"/events/types/{mine['id']}", headers=other_headers, json={"unit": "hours"}
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/events/types/{mine['id']}", headers=other_headers).status_code
        == 404
    )

    my_event_id = client.get("/events", headers=admin_headers).json()[0]["id"]
    assert (
        client.get(f"/events/{my_event_id}", headers=other_headers).status_code == 404
    )
    assert (
        client.delete(f"/events/{my_event_id}", headers=other_headers).status_code
        == 404
    )

    # Nothing the other user attempted changed anything.
    assert (
        client.get(f"/events/{my_event_id}", headers=admin_headers).json()["value"]
        == 20
    )
    assert (
        client.get(f"/events/types/{mine['id']}", headers=admin_headers).json()["unit"]
        == "minutes"
    )


def test_cannot_log_an_event_against_someone_elses_type(client, monkeypatch):
    """A type id is not a capability -- it must belong to the caller."""
    from app.config import settings

    monkeypatch.setattr(settings, "bearer_token", "admin-token")
    monkeypatch.setattr(settings, "multi_user_enabled", True)
    admin_headers = {"Authorization": "Bearer admin-token"}
    created = client.post("/users", headers=admin_headers, json={"name": "Second user"})
    other_headers = {"Authorization": f"Bearer {created.json()['token']}"}

    mine = client.post(
        "/events/types", headers=admin_headers, json={"name": "Sauna"}
    ).json()

    response = client.post(
        "/events",
        headers=other_headers,
        json={"event_type_id": mine["id"], "date": "2026-08-02"},
    )
    assert response.status_code == 404
    assert client.get("/events", headers=admin_headers).json() == []


def test_time_of_day_is_normalized_and_junk_rejected(client):
    """`at` sorts events within a day, so it has to be a real time."""
    event_type = _make_type(client, name="Nap", unit="minutes")

    ok = client.post(
        "/events",
        json={"event_type_id": event_type["id"], "date": "2026-08-02", "at": "14:05"},
    )
    assert ok.status_code == 201
    assert ok.json()["at"] == "14:05:00"

    junk = client.post(
        "/events",
        json={
            "event_type_id": event_type["id"],
            "date": "2026-08-02",
            "at": "afternoon",
        },
    )
    assert junk.status_code == 422


def test_events_within_a_day_are_ordered_by_time(client):
    event_type = _make_type(client, name="Water", unit="ml")
    for at in ("08:00", "20:00", "12:00"):
        client.post(
            "/events",
            json={"event_type_id": event_type["id"], "date": "2026-08-02", "at": at},
        )

    listed = client.get("/events").json()
    assert [e["at"] for e in listed] == ["20:00:00", "12:00:00", "08:00:00"]
