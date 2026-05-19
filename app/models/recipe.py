from datetime import datetime
from pydantic import BaseModel


class RecipeIngredientInput(BaseModel):
    food_id: int
    amount: float
    unit: str


class RecipeIngredient(RecipeIngredientInput):
    food_snapshot: dict
    grams: float


class RecipeCreate(BaseModel):
    name: str
    servings: float
    total_weight_g: float
    ingredients: list[RecipeIngredientInput]


class RecipeUpdate(BaseModel):
    name: str | None = None
    servings: float | None = None
    total_weight_g: float | None = None
    ingredients: list[RecipeIngredientInput] | None = None


class Recipe(BaseModel):
    id: int
    user_id: int
    name: str
    servings: float
    total_weight_g: float
    ingredients: list[RecipeIngredient]
    nutrients_per_100: dict
    nutrients_per_serving: dict
    created_at: datetime
    updated_at: datetime
