from fastapi import APIRouter, HTTPException, Request
from app.models.weight import WeightEntryCreate, WeightEntryUpdate, WeightEntry
from app.repositories.weight import WeightRepository
from app.config import settings

router = APIRouter(prefix="/weight", tags=["weight"])


def _repo(request: Request) -> WeightRepository:
    return WeightRepository(request.app.state.db)


@router.post("", status_code=201, response_model=WeightEntry, summary="Log body weight")
def create_weight(request: Request, body: WeightEntryCreate):
    """Log a body weight measurement for a date."""
    repo = _repo(request)
    wid = repo.create(
        user_id=settings.default_user_id,
        date=body.date, weight_kg=body.weight_kg, notes=body.notes,
    )
    return repo.get(wid)


@router.get("", response_model=list[WeightEntry], summary="Get weight entries")
def list_weight(
    request: Request, date: str | None = None,
    start: str | None = None, end: str | None = None,
):
    """Get weight entries by date (?date=YYYY-MM-DD) or date range (?start=&end=)."""
    repo = _repo(request)
    if date:
        return repo.list_by_date_range(
            user_id=settings.default_user_id, start=date, end=date
        )
    if start and end:
        return repo.list_by_date_range(
            user_id=settings.default_user_id, start=start, end=end
        )
    raise HTTPException(400, "Provide date or start+end parameters")


@router.patch("/{entry_id}", response_model=WeightEntry, summary="Update weight entry")
def update_weight(request: Request, entry_id: int, body: WeightEntryUpdate):
    """Update a weight entry."""
    repo = _repo(request)
    if not repo.get(entry_id):
        raise HTTPException(404, "Weight entry not found")
    updates = body.model_dump(exclude_unset=True)
    repo.update(entry_id, **updates)
    return repo.get(entry_id)


@router.delete("/{entry_id}", status_code=204, summary="Delete weight entry")
def delete_weight(request: Request, entry_id: int):
    """Delete a weight entry."""
    if not _repo(request).delete(entry_id):
        raise HTTPException(404, "Weight entry not found")
