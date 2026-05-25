import re
from datetime import datetime, timezone


AVAILABLE_STATUSES = {"have", "use_soon", "staple"}
MISSING_REQUIRED_PENALTY = -12


def canonicalize_ingredient_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _inventory_by_name(inventory: list[dict]) -> dict[str, dict]:
    return {item["canonical_name"]: item for item in inventory}


def _days_since(iso_value: str | None) -> int | None:
    if not iso_value:
        return None
    raw = iso_value.replace("Z", "+00:00")
    try:
        then = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return max(0, (now - then).days)


def rank_favorite_meals(
    *,
    meals: list[dict],
    inventory: list[dict],
    request_filters: dict | None = None,
) -> list[dict]:
    request_filters = request_filters or {}
    inventory_map = _inventory_by_name(inventory)
    results = []

    for meal in meals:
        score = int(meal.get("favorite_score") or 0)
        breakdown = [{"reason": "favorite_score", "points": score}]
        available_required = []
        missing_required = []
        available_optional = []
        use_soon = []
        maybe = []
        out = []

        for ingredient in meal.get("ingredients", []):
            canonical = ingredient["canonical_name"]
            display = ingredient["display_name"]
            role = ingredient["role"]
            inv = inventory_map.get(canonical)
            status = inv["status"] if inv else "missing"

            if status == "use_soon":
                score += 8
                breakdown.append({"reason": f"use_soon:{canonical}", "points": 8})
                use_soon.append(display)

            if status in AVAILABLE_STATUSES:
                if role == "required":
                    score += 5
                    breakdown.append(
                        {"reason": f"required_available:{canonical}", "points": 5}
                    )
                    available_required.append(display)
                else:
                    score += 2
                    breakdown.append(
                        {"reason": f"optional_available:{canonical}", "points": 2}
                    )
                    available_optional.append(display)
            elif status == "maybe":
                score -= 2
                breakdown.append({"reason": f"maybe:{canonical}", "points": -2})
                maybe.append(display)
            elif status == "out":
                points = MISSING_REQUIRED_PENALTY if role == "required" else -1
                score += points
                breakdown.append({"reason": f"out:{canonical}", "points": points})
                out.append(display)
                if role == "required":
                    missing_required.append(display)
            elif role == "required":
                score += MISSING_REQUIRED_PENALTY
                breakdown.append(
                    {
                        "reason": f"missing_required:{canonical}",
                        "points": MISSING_REQUIRED_PENALTY,
                    }
                )
                missing_required.append(display)

        if request_filters.get("effort") and meal.get("effort") != request_filters["effort"]:
            score -= 3
            breakdown.append({"reason": "effort_mismatch", "points": -3})

        required_tag = request_filters.get("tag")
        if required_tag and required_tag not in meal.get("tags", []):
            score -= 4
            breakdown.append({"reason": f"missing_tag:{required_tag}", "points": -4})

        days = _days_since(meal.get("last_made_at"))
        if days is not None and days < 3:
            score -= 4
            breakdown.append({"reason": "recently_made", "points": -4})

        results.append(
            {
                "meal_id": meal["id"],
                "meal_name": meal["name"],
                "score": score,
                "available_required_ingredients": available_required,
                "missing_required_ingredients": missing_required,
                "available_optional_ingredients": available_optional,
                "use_soon_ingredients": use_soon,
                "maybe_ingredients": maybe,
                "out_ingredients": out,
                "score_breakdown": breakdown,
            }
        )

    return sorted(results, key=lambda result: result["score"], reverse=True)


def generate_shopping_items_for_meals(
    *, meals: list[dict], inventory: list[dict]
) -> list[dict]:
    inventory_map = _inventory_by_name(inventory)
    pending: dict[str, dict] = {}

    for meal in meals:
        for ingredient in meal.get("ingredients", []):
            if ingredient["role"] != "required":
                continue
            inv = inventory_map.get(ingredient["canonical_name"])
            if inv and inv["status"] in AVAILABLE_STATUSES:
                continue

            canonical = ingredient["canonical_name"]
            if canonical not in pending:
                pending[canonical] = {
                    "canonical_name": canonical,
                    "display_name": ingredient["display_name"],
                    "source": "meal_plan",
                    "linked_meal_ids": [],
                }
            if meal["id"] not in pending[canonical]["linked_meal_ids"]:
                pending[canonical]["linked_meal_ids"].append(meal["id"])

    return sorted(pending.values(), key=lambda item: item["display_name"].lower())
