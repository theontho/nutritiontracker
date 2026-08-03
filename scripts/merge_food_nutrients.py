"""Fill missing nutrients from an identity-compatible reference food.

Usage:
    python -m scripts.merge_food_nutrients DB TARGET_FOOD_ID REFERENCE_FOOD_ID

The merge is allowed only when every nutrient reported by both foods agrees.
Existing target values are never overwritten. Diary snapshots that reference
the target food are refreshed in the same transaction.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
from typing import TypedDict

from app.models.food import NUTRIENT_FIELDS
from app.services.diary import build_food_snapshot, compute_entry_nutrients


class MergeResult(TypedDict):
    target_food_id: int
    reference_food_id: int
    shared_nutrients: int
    merged_fields: tuple[str, ...]
    diary_entries_refreshed: int


def merge_missing_nutrients(
    db_path: Path,
    target_food_id: int,
    reference_food_id: int,
) -> MergeResult:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN IMMEDIATE")
        target = connection.execute(
            "SELECT * FROM foods WHERE id = ?", (target_food_id,)
        ).fetchone()
        if target is None:
            raise ValueError(f"No target food {target_food_id}")
        reference = connection.execute(
            "SELECT * FROM foods WHERE id = ?", (reference_food_id,)
        ).fetchone()
        if reference is None:
            raise ValueError(f"No reference food {reference_food_id}")
        if target_food_id == reference_food_id:
            raise ValueError("Target and reference food must differ")

        shared = [
            field
            for field in NUTRIENT_FIELDS
            if target[field] is not None and reference[field] is not None
        ]
        if not shared:
            raise ValueError("Foods have no overlapping reported nutrients")
        mismatches = [
            field
            for field in shared
            if not math.isclose(
                float(target[field]),
                float(reference[field]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
        ]
        if mismatches:
            raise ValueError(
                "Foods disagree on overlapping nutrients: " + ", ".join(mismatches)
            )

        merged = [
            field
            for field in NUTRIENT_FIELDS
            if target[field] is None and reference[field] is not None
        ]
        if merged:
            assignments = ", ".join(f"{field} = ?" for field in merged)
            connection.execute(
                f"UPDATE foods SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [*(reference[field] for field in merged), target_food_id],
            )

        updated_food = connection.execute(
            "SELECT * FROM foods WHERE id = ?", (target_food_id,)
        ).fetchone()
        assert updated_food is not None
        food = dict(updated_food)
        snapshot = build_food_snapshot(food)
        diary_entries = connection.execute(
            "SELECT id, grams FROM diary_entries WHERE food_id = ? ORDER BY id",
            (target_food_id,),
        ).fetchall()
        for entry in diary_entries:
            nutrients = compute_entry_nutrients(food, float(entry["grams"]))
            connection.execute(
                """
                UPDATE diary_entries
                SET food_snapshot = ?, food_name = ?, nutrients_total = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    json.dumps(snapshot, separators=(",", ":")),
                    food["name"],
                    json.dumps(nutrients, separators=(",", ":")),
                    entry["id"],
                ),
            )

        connection.commit()
        return {
            "target_food_id": target_food_id,
            "reference_food_id": reference_food_id,
            "shared_nutrients": len(shared),
            "merged_fields": tuple(merged),
            "diary_entries_refreshed": len(diary_entries),
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db", type=Path)
    parser.add_argument("target_food_id", type=int)
    parser.add_argument("reference_food_id", type=int)
    args = parser.parse_args()

    result = merge_missing_nutrients(
        args.db,
        args.target_food_id,
        args.reference_food_id,
    )
    print(
        f"Merged {len(result['merged_fields'])} missing nutrient field(s) into "
        f"food {result['target_food_id']} from food {result['reference_food_id']}."
    )
    print(f"Refreshed {result['diary_entries_refreshed']} diary entry snapshot(s).")


if __name__ == "__main__":
    main()
