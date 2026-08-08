"""Upgrade mood events to independent dimensions and multi-label affect.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-07
"""

import json

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

_DIMENSIONS = {
    "happy": (2, 1),
    "excited": (2, 2),
    "hopeful": (2, 1),
    "proud": (2, 1),
    "calm": (2, -1),
    "content": (2, -1),
    "grateful": (2, -1),
    "relieved": (2, -1),
    "sad": (-2, -1),
    "low": (-2, -2),
    "tired": (-1, -2),
    "lonely": (-2, -1),
    "bored": (-1, -2),
    "anxious": (-2, 2),
    "angry": (-2, 2),
    "overwhelmed": (-2, 2),
    "disgusted": (-2, 1),
    "surprised": (0, 2),
    "confused": (-1, -1),
}


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.exec_driver_sql(
        "SELECT id, mood FROM events WHERE mood IS NOT NULL"
    ).fetchall()
    for event_id, raw_mood in rows:
        mood = json.loads(raw_mood)
        if mood.get("version") == 2:
            continue
        primary = mood["primary"]
        intensity = mood.get("intensity", 2)
        labels = [{"category": primary, "intensity": intensity}]
        if mood.get("secondary") is not None:
            labels.append({"category": mood["secondary"], "intensity": intensity})
        pleasantness, energy = _DIMENSIONS[primary]
        upgraded = {
            "version": 2,
            "pleasantness": pleasantness,
            "energy": energy,
            "capture_mode": "spontaneous",
            "labels": labels,
            "stress": None,
            "motivation": None,
            "functional_impact": None,
            "context_tags": [],
            "body_cues": [],
            "regulation": [],
            "duration_minutes": None,
        }
        connection.exec_driver_sql(
            "UPDATE events SET mood = ? WHERE id = ?",
            (json.dumps(upgraded, separators=(",", ":")), event_id),
        )


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")
