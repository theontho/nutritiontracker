from fastapi import APIRouter, HTTPException, Request
from app.models.food import FoodCreate, FoodUpdate, FoodOut
from app.repositories.foods import FoodRepository
from app.services.food_search import FoodSearchService

router = APIRouter(prefix="/foods", tags=["foods"])


def _repo(request: Request) -> FoodRepository:
    return FoodRepository(request.app.state.db)


def _search_svc(request: Request) -> FoodSearchService:
    return FoodSearchService(_repo(request))


@router.get("/search", response_model=list[FoodOut], summary="Search foods")
def search_foods(
    request: Request, q: str, source: str = "all", limit: int = 20, offset: int = 0
):
    """Search the food database by name or brand. Supports prefix matching ('chick' matches 'chicken breast').
    Deduplicates results when the same food appears in multiple sources — prefers the record with more complete nutrient data.
    Filter by source: `all`, `custom`, `open_food_facts`, `food_data_central`."""
    return _search_svc(request).search(q, source=source, limit=limit, offset=offset)


@router.get("/barcode/{barcode}", response_model=FoodOut, summary="Look up food by barcode")
def get_by_barcode(request: Request, barcode: str):
    """Look up a food by EAN or UPC barcode."""
    food = _repo(request).get_by_barcode(barcode)
    if not food:
        raise HTTPException(404, "Food not found")
    return food


@router.get("/{food_id}", response_model=FoodOut, summary="Get food by ID")
def get_food(request: Request, food_id: int):
    """Retrieve a single food record by its ID."""
    food = _repo(request).get(food_id)
    if not food:
        raise HTTPException(404, "Food not found")
    return food


@router.post("", status_code=201, response_model=FoodOut, summary="Create custom food")
def create_food(request: Request, body: FoodCreate):
    """Create a custom food entry. Provide name, source='custom', and nutrient values per 100g."""
    repo = _repo(request)
    nutrients = body.nutrients.model_dump()
    data = body.model_dump(exclude={"nutrients"})
    data.update(nutrients)
    food_id = repo.create(**data)
    return repo.get(food_id)


@router.patch("/{food_id}", response_model=FoodOut, summary="Update custom food")
def update_food(request: Request, food_id: int, body: FoodUpdate):
    """Update fields on a custom food record."""
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


@router.delete("/{food_id}", status_code=204, summary="Delete custom food")
def delete_food(request: Request, food_id: int):
    """Delete a custom food record. Only custom foods can be deleted."""
    repo = _repo(request)
    if not repo.delete(food_id):
        raise HTTPException(404, "Food not found")
