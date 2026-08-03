from fastapi import APIRouter, Request

from app.auth import current_user_id
from app.models.stats import DailyStats, RangeDailyStats
from app.repositories.activity import ActivityRepository
from app.repositories.diary import DiaryRepository
from app.services.nutrients import sum_nutrients

router = APIRouter(prefix="/stats", tags=["stats"])

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def _compute_daily(entries: list[dict], date: str) -> dict:
    meals = {
        meal: sum_nutrients(
            (
                entry.get("nutrients_total", {})
                for entry in entries
                if entry["meal_type"] == meal
            ),
            empty_is_zero=True,
        )
        for meal in MEAL_TYPES
    }
    total = sum_nutrients(
        (entry.get("nutrients_total", {}) for entry in entries),
        empty_is_zero=True,
    )
    return {
        "date": date,
        "total": total,
        "meals": meals,
        "entry_count": len(entries),
    }


@router.get(
    "/daily/{date}", response_model=DailyStats, summary="Daily nutrition summary"
)
def daily_stats(request: Request, date: str):
    """Get total nutrients and per-meal breakdown for a given date. All four meal types (breakfast, lunch, dinner, snack) are always included — meals with no entries show zero values."""
    diary = DiaryRepository(request.app.state.db)
    user_id = current_user_id(request)
    entries = diary.list_by_date(user_id=user_id, date=date)
    result = _compute_daily(entries, date)

    activity_repo = ActivityRepository(request.app.state.db)
    activity_row = activity_repo.get_daily(user_id=user_id, date=date)
    if activity_row:
        result["activity"] = {
            "steps": activity_row["steps"],
            "source": activity_row["source"],
            "last_observed_at": activity_row["last_observed_at"],
            "anomaly_flag": bool(activity_row["anomaly_flag"]),
        }
    return result


@router.get(
    "/range",
    response_model=list[RangeDailyStats],
    summary="Nutrition summary over a date range",
)
def range_stats(request: Request, start: str, end: str):
    """Get daily nutrition totals for a date range (YYYY-MM-DD). Only days with diary entries are included. Useful for trend analysis."""
    diary = DiaryRepository(request.app.state.db)
    rows = request.app.state.db.execute(
        """SELECT DISTINCT date FROM diary_entries
           WHERE user_id = ? AND date >= ? AND date <= ?
           ORDER BY date""",
        (current_user_id(request), start, end),
    ).fetchall()
    results = []
    for row in rows:
        date = row["date"]
        entries = diary.list_by_date(user_id=current_user_id(request), date=date)
        daily = _compute_daily(entries, date)
        daily.pop("meals")
        results.append(daily)
    return results
