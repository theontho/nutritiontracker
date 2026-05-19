from pydantic import BaseModel


class StepImportRequest(BaseModel):
    source: str
    observed_at: str
    period_start: str
    period_end: str
    steps_total_today: int
    timezone: str


class DailyActivity(BaseModel):
    id: int
    user_id: int
    date: str
    source: str
    steps: int
    last_observed_at: str
    anomaly_flag: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ActivitySummary(BaseModel):
    steps: int
    source: str
    last_observed_at: str
    anomaly_flag: bool
