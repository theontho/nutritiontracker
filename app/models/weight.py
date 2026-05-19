from datetime import datetime
from pydantic import BaseModel


class WeightEntryCreate(BaseModel):
    date: str
    weight_kg: float
    notes: str | None = None


class WeightEntryUpdate(BaseModel):
    weight_kg: float | None = None
    notes: str | None = None


class WeightEntry(BaseModel):
    id: int
    user_id: int
    date: str
    weight_kg: float
    notes: str | None
    created_at: datetime
    updated_at: datetime
