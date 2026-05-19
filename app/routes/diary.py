from fastapi import APIRouter, HTTPException, Request
from app.models.diary import DiaryEntryCreate, DiaryEntryUpdate
from app.repositories.diary import DiaryRepository
from app.repositories.foods import FoodRepository
from app.services.diary import compute_entry_nutrients, build_food_snapshot
from app.services.unit_conversion import convert_to_grams
from app.config import settings

router = APIRouter(tags=["diary"])


def _diary_repo(request: Request) -> DiaryRepository:
    return DiaryRepository(request.app.state.db)


def _food_repo(request: Request) -> FoodRepository:
    return FoodRepository(request.app.state.db)


@router.get("/diary/{date}")
def list_entries(request: Request, date: str):
    return _diary_repo(request).list_by_date(
        user_id=settings.default_user_id, date=date
    )


@router.post("/diary/{date}/entries", status_code=201)
def create_entry(request: Request, date: str, body: DiaryEntryCreate):
    food_repo = _food_repo(request)
    food = food_repo.get(body.food_id)
    if not food:
        raise HTTPException(404, "Food not found")

    conversion = convert_to_grams(
        body.amount, body.unit,
        density_g_per_ml=food.get("density_g_per_ml"),
        serving_quantity=food.get("serving_quantity"),
        serving_unit=food.get("serving_unit"),
    )
    nutrients = compute_entry_nutrients(food, conversion.grams)
    snapshot = build_food_snapshot(food)

    diary_repo = _diary_repo(request)
    entry_id = diary_repo.create(
        user_id=settings.default_user_id, date=date,
        meal_type=body.meal_type, food_id=body.food_id,
        food_snapshot=snapshot, amount=body.amount,
        unit=body.unit, grams=conversion.grams,
        nutrients_total=nutrients,
    )
    return diary_repo.get(entry_id)


@router.patch("/diary/entries/{entry_id}")
def update_entry(request: Request, entry_id: int, body: DiaryEntryUpdate):
    diary_repo = _diary_repo(request)
    entry = diary_repo.get(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")

    updates = body.model_dump(exclude_unset=True)
    if "amount" in updates or "unit" in updates:
        food = entry["food_snapshot"]
        amount = updates.get("amount", entry["amount"])
        unit = updates.get("unit", entry["unit"])
        conversion = convert_to_grams(
            amount, unit,
            density_g_per_ml=food.get("density_g_per_ml"),
            serving_quantity=food.get("serving_quantity"),
            serving_unit=food.get("serving_unit"),
        )
        updates["grams"] = conversion.grams
        updates["nutrients_total"] = compute_entry_nutrients(food, conversion.grams)

    diary_repo.update(entry_id, **updates)
    return diary_repo.get(entry_id)


@router.delete("/diary/entries/{entry_id}", status_code=204)
def delete_entry(request: Request, entry_id: int):
    if not _diary_repo(request).delete(entry_id):
        raise HTTPException(404, "Entry not found")
