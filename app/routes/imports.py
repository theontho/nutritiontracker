from fastapi import APIRouter, Request
from app.models.activity import StepImportRequest, DailyActivity
from app.repositories.activity import ActivityRepository
from app.services.activity_import import import_steps
from app.config import settings

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/activity/steps", response_model=DailyActivity, summary="Import hourly step count from Apple Shortcuts")
def import_activity_steps(request: Request, body: StepImportRequest):
    """Receive cumulative day-to-date step count from Apple Shortcuts automation.
    Stores every observation and updates the daily total when the new count is newer and valid.
    Sets anomaly_flag=True when a later observation reports a lower total."""
    repo = ActivityRepository(request.app.state.db)
    return import_steps(
        repo=repo,
        user_id=settings.default_user_id,
        source=body.source,
        observed_at=body.observed_at,
        period_start=body.period_start,
        period_end=body.period_end,
        steps_total_today=body.steps_total_today,
        timezone=body.timezone,
        raw_payload=body.model_dump(),
    )
