from fastapi import APIRouter, HTTPException, Request
from app.models.food import FoodCreate, FoodUpdate
from app.repositories.foods import FoodRepository
from app.services.food_search import FoodSearchService

router = APIRouter(prefix="/foods", tags=["foods"])


def _repo(request: Request) -> FoodRepository:
    return FoodRepository(request.app.state.db)


def _search_svc(request: Request) -> FoodSearchService:
    return FoodSearchService(_repo(request))


@router.get("/search")
def search_foods(
    request: Request, q: str, source: str = "all", limit: int = 20, offset: int = 0
):
    return _search_svc(request).search(q, source=source, limit=limit, offset=offset)


@router.get("/barcode/{barcode}")
def get_by_barcode(request: Request, barcode: str):
    food = _repo(request).get_by_barcode(barcode)
    if not food:
        raise HTTPException(404, "Food not found")
    return food


@router.get("/{food_id}")
def get_food(request: Request, food_id: int):
    food = _repo(request).get(food_id)
    if not food:
        raise HTTPException(404, "Food not found")
    return food


@router.post("", status_code=201)
def create_food(request: Request, body: FoodCreate):
    repo = _repo(request)
    nutrients = body.nutrients.model_dump()
    data = body.model_dump(exclude={"nutrients"})
    data.update(nutrients)
    food_id = repo.create(**data)
    return repo.get(food_id)


@router.patch("/{food_id}")
def update_food(request: Request, food_id: int, body: FoodUpdate):
    repo = _repo(request)
    if not repo.get(food_id):
        raise HTTPException(404, "Food not found")
    updates = body.model_dump(exclude_unset=True)
    if "nutrients" in updates and updates["nutrients"] is not None:
        nutrients = updates.pop("nutrients")
        updates.update(nutrients)
    elif "nutrients" in updates:
        updates.pop("nutrients")
    repo.update(food_id, **updates)
    return repo.get(food_id)


@router.delete("/{food_id}", status_code=204)
def delete_food(request: Request, food_id: int):
    repo = _repo(request)
    if not repo.delete(food_id):
        raise HTTPException(404, "Food not found")
