from fastapi import APIRouter, Request
from app.models.food import NutrientsPer100
from app.repositories.diary import DiaryRepository
from app.config import settings

router = APIRouter(prefix="/stats", tags=["stats"])

NUTRIENT_FIELDS = list(NutrientsPer100.model_fields.keys())
MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def _zero_nutrients() -> dict:
    return {f: 0.0 for f in NUTRIENT_FIELDS}


def _sum_nutrients(a: dict, b: dict) -> dict:
    return {f: round(a.get(f, 0) + b.get(f, 0), 2) for f in NUTRIENT_FIELDS}


def _compute_daily(entries: list[dict], date: str) -> dict:
    meals = {m: _zero_nutrients() for m in MEAL_TYPES}
    for entry in entries:
        nt = entry.get("nutrients_total", {})
        meal = entry["meal_type"]
        meals[meal] = _sum_nutrients(meals[meal], nt)
    total = _zero_nutrients()
    for m_nutrients in meals.values():
        total = _sum_nutrients(total, m_nutrients)
    return {
        "date": date,
        "total": total,
        "meals": meals,
        "entry_count": len(entries),
    }


@router.get("/daily/{date}")
def daily_stats(request: Request, date: str):
    diary = DiaryRepository(request.app.state.db)
    entries = diary.list_by_date(user_id=settings.default_user_id, date=date)
    return _compute_daily(entries, date)


@router.get("/range")
def range_stats(request: Request, start: str, end: str):
    diary = DiaryRepository(request.app.state.db)
    rows = request.app.state.db.execute(
        """SELECT DISTINCT date FROM diary_entries
           WHERE user_id = ? AND date >= ? AND date <= ?
           ORDER BY date""",
        (settings.default_user_id, start, end),
    ).fetchall()
    results = []
    for row in rows:
        date = row["date"]
        entries = diary.list_by_date(user_id=settings.default_user_id, date=date)
        daily = _compute_daily(entries, date)
        daily.pop("meals")
        results.append(daily)
    return results
