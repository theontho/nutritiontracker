from typing import Optional
from pydantic import BaseModel
from app.models.food import NutrientsPer100
from app.models.activity import ActivitySummary


class MealStats(NutrientsPer100):
    pass


class DailyStats(BaseModel):
    date: str
    total: NutrientsPer100
    activity: Optional[ActivitySummary] = None
    meals: dict[str, MealStats]
    entry_count: int


class RangeDailyStats(BaseModel):
    date: str
    total: NutrientsPer100
    entry_count: int
