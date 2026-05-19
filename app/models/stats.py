from pydantic import BaseModel
from app.models.food import NutrientsPer100


class MealStats(NutrientsPer100):
    pass


class DailyStats(BaseModel):
    date: str
    total: NutrientsPer100
    meals: dict[str, MealStats]
    entry_count: int


class RangeDailyStats(BaseModel):
    date: str
    total: NutrientsPer100
    entry_count: int
