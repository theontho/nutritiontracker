from fastapi import APIRouter, HTTPException, Request
from app.models.weight import WeightEntryCreate, WeightEntryUpdate
from app.repositories.weight import WeightRepository
from app.config import settings

router = APIRouter(prefix="/weight", tags=["weight"])


def _repo(request: Request) -> WeightRepository:
    return WeightRepository(request.app.state.db)


@router.post("", status_code=201)
def create_weight(request: Request, body: WeightEntryCreate):
    repo = _repo(request)
    wid = repo.create(
        user_id=settings.default_user_id,
        date=body.date, weight_kg=body.weight_kg, notes=body.notes,
    )
    return repo.get(wid)


@router.get("")
def list_weight(
    request: Request, date: str | None = None,
    start: str | None = None, end: str | None = None,
):
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


@router.patch("/{entry_id}")
def update_weight(request: Request, entry_id: int, body: WeightEntryUpdate):
    repo = _repo(request)
    if not repo.get(entry_id):
        raise HTTPException(404, "Weight entry not found")
    updates = body.model_dump(exclude_unset=True)
    repo.update(entry_id, **updates)
    return repo.get(entry_id)


@router.delete("/{entry_id}", status_code=204)
def delete_weight(request: Request, entry_id: int):
    if not _repo(request).delete(entry_id):
        raise HTTPException(404, "Weight entry not found")
