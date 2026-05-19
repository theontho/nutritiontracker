from datetime import datetime
from pydantic import BaseModel
from typing import Literal

MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class DiaryEntryCreate(BaseModel):
    food_id: int
    amount: float
    unit: str
    meal_type: MealType


class DiaryEntryUpdate(BaseModel):
    amount: float | None = None
    unit: str | None = None
    meal_type: MealType | None = None


class DiaryEntry(BaseModel):
    id: int
    user_id: int
    date: str
    meal_type: MealType
    food_id: int
    food_snapshot: dict
    amount: float
    unit: str
    grams: float
    nutrients_total: dict
    created_at: datetime
    updated_at: datetime
