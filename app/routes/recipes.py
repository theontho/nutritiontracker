from fastapi import APIRouter, HTTPException, Request
from app.models.recipe import RecipeCreate, RecipeUpdate
from app.repositories.recipes import RecipeRepository
from app.repositories.foods import FoodRepository
from app.services.recipe_nutrition import compute_recipe_nutrients
from app.services.unit_conversion import convert_to_grams
from app.services.diary import build_food_snapshot
from app.config import settings

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _recipe_repo(request: Request) -> RecipeRepository:
    return RecipeRepository(request.app.state.db)


def _food_repo(request: Request) -> FoodRepository:
    return FoodRepository(request.app.state.db)


def _resolve_ingredients(food_repo: FoodRepository, ingredients_input: list) -> list[dict]:
    resolved = []
    for ing in ingredients_input:
        food = food_repo.get(ing.food_id)
        if not food:
            raise HTTPException(404, f"Food {ing.food_id} not found")
        conversion = convert_to_grams(
            ing.amount, ing.unit,
            density_g_per_ml=food.get("density_g_per_ml"),
            serving_quantity=food.get("serving_quantity"),
            serving_unit=food.get("serving_unit"),
        )
        resolved.append({
            "food_id": ing.food_id,
            "food_snapshot": build_food_snapshot(food),
            "amount": ing.amount,
            "unit": ing.unit,
            "grams": conversion.grams,
        })
    return resolved


@router.post("", status_code=201)
def create_recipe(request: Request, body: RecipeCreate):
    food_repo = _food_repo(request)
    recipe_repo = _recipe_repo(request)

    resolved = _resolve_ingredients(food_repo, body.ingredients)
    per_100, per_serving = compute_recipe_nutrients(
        resolved, body.total_weight_g, body.servings
    )

    recipe_id = recipe_repo.create(
        user_id=settings.default_user_id,
        name=body.name, servings=body.servings,
        total_weight_g=body.total_weight_g,
        ingredients=resolved,
        nutrients_per_100=per_100,
        nutrients_per_serving=per_serving,
    )
    return recipe_repo.get(recipe_id)


@router.get("")
def list_recipes(request: Request, limit: int = 20, offset: int = 0):
    return _recipe_repo(request).list_all(
        user_id=settings.default_user_id, limit=limit, offset=offset
    )


@router.get("/{recipe_id}")
def get_recipe(request: Request, recipe_id: int):
    recipe = _recipe_repo(request).get(recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    return recipe


@router.patch("/{recipe_id}")
def update_recipe(request: Request, recipe_id: int, body: RecipeUpdate):
    recipe_repo = _recipe_repo(request)
    recipe = recipe_repo.get(recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    updates = body.model_dump(exclude_unset=True)
    if "ingredients" in updates:
        food_repo = _food_repo(request)
        resolved = _resolve_ingredients(food_repo, body.ingredients)
        total_weight = updates.get("total_weight_g", recipe["total_weight_g"])
        servings = updates.get("servings", recipe["servings"])
        per_100, per_serving = compute_recipe_nutrients(resolved, total_weight, servings)
        updates["ingredients"] = resolved
        updates["nutrients_per_100"] = per_100
        updates["nutrients_per_serving"] = per_serving

    recipe_repo.update(recipe_id, **updates)
    return recipe_repo.get(recipe_id)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(request: Request, recipe_id: int):
    if not _recipe_repo(request).delete(recipe_id):
        raise HTTPException(404, "Recipe not found")
