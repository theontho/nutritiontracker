from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

EventMeasurementKind = Literal["generic", "bristol_stool", "urine_color", "mood"]
MOOD_CATEGORIES = (
    "happy",
    "amused",
    "excited",
    "hopeful",
    "inspired",
    "proud",
    "calm",
    "content",
    "grateful",
    "relieved",
    "affectionate",
    "connected",
    "compassionate",
    "sad",
    "disappointed",
    "grieving",
    "low",
    "tired",
    "lonely",
    "bored",
    "anxious",
    "afraid",
    "insecure",
    "angry",
    "frustrated",
    "resentful",
    "overwhelmed",
    "disgusted",
    "embarrassed",
    "ashamed",
    "guilty",
    "surprised",
    "awed",
    "confused",
)
MoodCategory = Literal[
    "happy",
    "amused",
    "excited",
    "hopeful",
    "inspired",
    "proud",
    "calm",
    "content",
    "grateful",
    "relieved",
    "affectionate",
    "connected",
    "compassionate",
    "sad",
    "disappointed",
    "grieving",
    "low",
    "tired",
    "lonely",
    "bored",
    "anxious",
    "afraid",
    "insecure",
    "angry",
    "frustrated",
    "resentful",
    "overwhelmed",
    "disgusted",
    "embarrassed",
    "ashamed",
    "guilty",
    "surprised",
    "awed",
    "confused",
]
MoodCaptureMode = Literal["spontaneous", "scheduled", "reconstructed"]
MoodDimensionSource = Literal["reported", "legacy_inferred"]
MoodRegulation = Literal[
    "situation_selection",
    "situation_change",
    "attention_shift",
    "reappraisal",
    "response_support",
]
MoodPleasantness = Literal[-3, -2, -1, 0, 1, 2, 3]
MoodEnergy = Literal[-2, -1, 0, 1, 2]

_LEGACY_DIMENSIONS: dict[MoodCategory, tuple[MoodPleasantness, MoodEnergy]] = {
    "happy": (2, 1),
    "excited": (2, 2),
    "hopeful": (2, 1),
    "proud": (2, 1),
    "calm": (2, -1),
    "content": (2, -1),
    "grateful": (2, -1),
    "relieved": (2, -1),
    "sad": (-2, -1),
    "low": (-2, -2),
    "tired": (-1, -2),
    "lonely": (-2, -1),
    "bored": (-1, -2),
    "anxious": (-2, 2),
    "angry": (-2, 2),
    "overwhelmed": (-2, 2),
    "disgusted": (-2, 1),
    "surprised": (0, 2),
    "confused": (-1, -1),
}


class MoodLabel(BaseModel):
    category: MoodCategory
    intensity: Literal[1, 2, 3] = 2


class MoodState(BaseModel):
    version: Literal[2] = 2
    pleasantness: MoodPleasantness
    energy: MoodEnergy
    capture_mode: MoodCaptureMode = "spontaneous"
    dimension_source: MoodDimensionSource = "reported"
    labels: list[MoodLabel] = Field(default_factory=list, max_length=6)
    stress: Literal[0, 1, 2, 3, 4] | None = None
    motivation: Literal[-2, -1, 0, 1, 2] | None = None
    functional_impact: Literal[0, 1, 2, 3] | None = None
    context_tags: list[Annotated[str, Field(max_length=40)]] = Field(
        default_factory=list, max_length=8
    )
    body_cues: list[Annotated[str, Field(max_length=40)]] = Field(
        default_factory=list, max_length=8
    )
    regulation: list[MoodRegulation] = Field(default_factory=list, max_length=5)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_mood(cls, value: object) -> object:
        if not isinstance(value, dict) or "primary" not in value:
            return value
        primary = value["primary"]
        if primary not in _LEGACY_DIMENSIONS:
            return value
        intensity = value.get("intensity", 2)
        labels = [{"category": primary, "intensity": intensity}]
        secondary = value.get("secondary")
        if secondary is not None:
            labels.append({"category": secondary, "intensity": intensity})
        pleasantness, energy = _LEGACY_DIMENSIONS[primary]
        return {
            "version": 2,
            "pleasantness": pleasantness,
            "energy": energy,
            "capture_mode": "spontaneous",
            "dimension_source": "legacy_inferred",
            "labels": labels,
        }

    @model_validator(mode="after")
    def _validate_collections(self) -> "MoodState":
        categories = [label.category for label in self.labels]
        if len(categories) != len(set(categories)):
            raise ValueError("mood labels must be unique")
        for field in ("context_tags", "body_cues"):
            values = getattr(self, field)
            normalized = [item.strip() for item in values]
            if any(not item for item in normalized):
                raise ValueError(f"{field} must not contain blank values")
            if len({item.casefold() for item in normalized}) != len(normalized):
                raise ValueError(f"{field} must contain unique values")
            setattr(self, field, normalized)
        if len(self.regulation) != len(set(self.regulation)):
            raise ValueError("regulation strategies must be unique")
        return self


def _require_content(value: str, field: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field} must not be blank")
    return stripped


def _validate_time_of_day(value: str) -> str:
    """Accept HH:MM or HH:MM:SS, local wall-clock, matching `date`.

    Left as a plain local time rather than a timestamp: attaching a UTC offset
    to something the user reported as "3pm" is how entries end up filed under
    the wrong day.
    """
    from datetime import time as time_cls

    try:
        return time_cls.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError("at must be a local time, HH:MM or HH:MM:SS") from None


def _validate_iso_date(value: str) -> str:
    from datetime import date as date_cls

    try:
        date_cls.fromisoformat(value)
    except ValueError:
        raise ValueError("date must be YYYY-MM-DD") from None
    return value


class EventTypeCreate(BaseModel):
    name: str = Field(max_length=200)
    unit: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = None
    is_private: bool = False
    measurement_kind: EventMeasurementKind = "generic"

    @field_validator("name")
    @classmethod
    def _name_has_content(cls, value: str) -> str:
        return _require_content(value, "name")

    @field_validator("unit")
    @classmethod
    def _unit_is_absent_or_meaningful(cls, value: Optional[str]) -> Optional[str]:
        # A whitespace-only unit reads as "unitless" but stores as a value that
        # is not None, which would defeat every "was a unit given?" check.
        if value is None:
            return None
        return _require_content(value, "unit")


class EventTypeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    unit: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = None
    is_private: Optional[bool] = None
    measurement_kind: EventMeasurementKind | None = None

    @field_validator("name")
    @classmethod
    def _name_has_content(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _require_content(value, "name")


class EventType(BaseModel):
    id: int
    user_id: int
    name: str
    unit: Optional[str]
    notes: Optional[str]
    is_private: bool
    measurement_kind: EventMeasurementKind
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    event_type_id: int
    date: str
    at: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = None
    mood: MoodState | None = None

    @field_validator("date")
    @classmethod
    def _date_is_iso(cls, value: str) -> str:
        return _validate_iso_date(value)

    @field_validator("at")
    @classmethod
    def _at_is_a_local_time(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else _validate_time_of_day(value)


class EventUpdate(BaseModel):
    date: Optional[str] = None
    at: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = None
    mood: MoodState | None = None

    @field_validator("date")
    @classmethod
    def _date_is_iso(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else _validate_iso_date(value)

    @field_validator("at")
    @classmethod
    def _at_is_a_local_time(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else _validate_time_of_day(value)


class Event(BaseModel):
    id: int
    user_id: int
    event_type_id: int
    event_type_name: str
    event_type_is_private: bool
    event_type_measurement_kind: EventMeasurementKind
    date: str
    at: Optional[str]
    value: Optional[float]
    unit: Optional[str]
    notes: Optional[str]
    mood: MoodState | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class EventSummaryRow(BaseModel):
    event_type_id: int
    event_type_name: str
    event_type_is_private: bool
    unit: Optional[str]
    count: int
    unmeasured_count: int
    total_value: Optional[float]

    model_config = {"from_attributes": True}
