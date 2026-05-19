from app.repositories.activity import ActivityRepository


def import_steps(*, repo: ActivityRepository, user_id: int, source: str,
                 observed_at: str, period_start: str, period_end: str,
                 steps_total_today: int, timezone: str,
                 raw_payload: dict) -> dict:
    # observed_at is expected to be the local timestamp as sent by the client (e.g. Apple Shortcuts).
    # The date portion of the string is therefore the correct local date.
    local_date = observed_at[:10]

    # Always store the observation
    repo.create_observation(
        user_id=user_id,
        source=source,
        observed_at=observed_at,
        local_date=local_date,
        period_start=period_start,
        period_end=period_end,
        steps_total_today=steps_total_today,
        timezone=timezone,
        raw_payload=raw_payload,
    )

    existing = repo.get_daily(user_id=user_id, date=local_date)

    if existing is None:
        repo.upsert_daily(
            user_id=user_id,
            date=local_date,
            source=source,
            steps=steps_total_today,
            last_observed_at=observed_at,
            anomaly_flag=False,
        )
    elif observed_at > existing["last_observed_at"]:
        # Newer observation
        anomaly = steps_total_today < existing["steps"]
        new_steps = existing["steps"] if anomaly else steps_total_today
        new_last_observed_at = existing["last_observed_at"] if anomaly else observed_at
        repo.upsert_daily(
            user_id=user_id,
            date=local_date,
            source=source,
            steps=new_steps,
            last_observed_at=new_last_observed_at,
            anomaly_flag=anomaly,
        )
    # else: older observation — already stored, skip daily update

    return repo.get_daily(user_id=user_id, date=local_date)
