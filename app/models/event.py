from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

EventMeasurementKind = Literal["generic", "bristol_stool", "urine_color", "mood"]
MoodValence = Literal["positive", "negative", "mixed"]
MoodEnergy = Literal["high", "low"]
MOOD_CATEGORIES = (
    "happy",
    "excited",
    "hopeful",
    "proud",
    "calm",
    "content",
    "grateful",
    "relieved",
    "sad",
    "low",
    "tired",
    "lonely",
    "bored",
    "anxious",
    "angry",
    "overwhelmed",
    "disgusted",
    "surprised",
    "confused",
)
MoodCategory = Literal[
    "happy",
    "excited",
    "hopeful",
    "proud",
    "calm",
    "content",
    "grateful",
    "relieved",
    "sad",
    "low",
    "tired",
    "lonely",
    "bored",
    "anxious",
    "angry",
    "overwhelmed",
    "disgusted",
    "surprised",
    "confused",
]

_MOOD_DIMENSIONS: dict[MoodCategory, tuple[MoodValence, MoodEnergy]] = {
    "happy": ("positive", "high"),
    "excited": ("positive", "high"),
    "hopeful": ("positive", "high"),
    "proud": ("positive", "high"),
    "calm": ("positive", "low"),
    "content": ("positive", "low"),
    "grateful": ("positive", "low"),
    "relieved": ("positive", "low"),
    "sad": ("negative", "low"),
    "low": ("negative", "low"),
    "tired": ("negative", "low"),
    "lonely": ("negative", "low"),
    "bored": ("negative", "low"),
    "anxious": ("negative", "high"),
    "angry": ("negative", "high"),
    "overwhelmed": ("negative", "high"),
    "disgusted": ("negative", "high"),
    "surprised": ("mixed", "high"),
    "confused": ("mixed", "low"),
}


class MoodState(BaseModel):
    primary: MoodCategory
    secondary: MoodCategory | None = None
    intensity: Literal[1, 2, 3] = 2
    valence: MoodValence | None = None
    energy: MoodEnergy | None = None

    @model_validator(mode="after")
    def _normalize_dimensions(self) -> "MoodState":
        if self.secondary == self.primary:
            raise ValueError("secondary mood must differ from primary mood")
        expected_valence, expected_energy = _MOOD_DIMENSIONS[self.primary]
        if self.valence not in (None, expected_valence):
            raise ValueError("mood valence does not match primary mood")
        if self.energy not in (None, expected_energy):
            raise ValueError("mood energy does not match primary mood")
        self.valence = expected_valence
        self.energy = expected_energy
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
