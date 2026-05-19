from typing import Optional
from pydantic import BaseModel, Field


class JournalEntryCreate(BaseModel):
    date: str
    body: str
    tags: list[str] = Field(default_factory=list)
    mood_score: Optional[int] = Field(default=None, ge=1, le=10)
    stress_score: Optional[int] = Field(default=None, ge=1, le=10)
    sleep_quality: Optional[int] = Field(default=None, ge=1, le=10)


class JournalEntryUpdate(BaseModel):
    body: Optional[str] = None
    tags: Optional[list[str]] = None
    mood_score: Optional[int] = Field(default=None, ge=1, le=10)
    stress_score: Optional[int] = Field(default=None, ge=1, le=10)
    sleep_quality: Optional[int] = Field(default=None, ge=1, le=10)


class JournalEntry(BaseModel):
    id: int
    user_id: int
    date: str
    body: str
    tags: list[str]
    mood_score: Optional[int]
    stress_score: Optional[int]
    sleep_quality: Optional[int]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
