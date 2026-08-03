import hashlib
import json

from app.services.nutrients import scale_nutrients

SNAPSHOT_CATALOG_VERSION_KEY = "_catalog_version"


def compute_entry_nutrients(food: dict, grams: float) -> dict:
    return scale_nutrients(food, grams / 100)


def build_food_snapshot(food: dict) -> dict:
    exclude = {"created_at", "updated_at"}
    snapshot = {k: v for k, v in food.items() if k not in exclude}
    serialized = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    snapshot[SNAPSHOT_CATALOG_VERSION_KEY] = f"sha256:{digest}"
    return snapshot
