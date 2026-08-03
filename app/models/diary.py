from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, field_validator

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
    food_name: str
    amount: float
    unit: str
    grams: float
    nutrients_total: dict
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
