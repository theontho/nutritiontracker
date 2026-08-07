from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


InventoryStatus = Literal["have", "use_soon", "maybe", "out", "staple"]
KitchenLocation = Literal["fridge", "freezer", "pantry", "other"]
IngredientRole = Literal["required", "optional", "substitution"]
EffortLevel = Literal["low", "medium", "high"]
ShoppingSource = Literal[
    "manual", "meal_plan", "inventory", "staple_refresh", "suggestion"
]


class InventoryItemCreate(BaseModel):
    name: str
    status: InventoryStatus = "have"
    location: KitchenLocation | None = None
    category: str | None = None
    notes: str | None = None


class InventoryItem(BaseModel):
    id: int
    user_id: int
    canonical_name: str
    display_name: str
    status: InventoryStatus
    location: KitchenLocation | None = None
    category: str | None = None
    notes: str | None = None
    last_confirmed_at: datetime
    created_at: datetime
    updated_at: datetime


class FavoriteMealIngredientInput(BaseModel):
    name: str
    role: IngredientRole = "required"
    category: str | None = None


class FavoriteMealIngredient(BaseModel):
    id: int | None = None
    meal_id: int | None = None
    canonical_name: str
    display_name: str
    role: IngredientRole
    category: str | None = None


class FavoriteMealCreate(BaseModel):
    name: str
    is_private: bool = False
    tags: list[str] = Field(default_factory=list)
    prep_time_minutes: int | None = None
    effort: EffortLevel | None = None
    favorite_score: int = 0
    nutrition_template_id: int | None = None
    ingredients: list[FavoriteMealIngredientInput] = Field(default_factory=list)


class FavoriteMealUpdate(BaseModel):
    is_private: bool


class FavoriteMeal(BaseModel):
    id: int
    user_id: int
    is_private: bool
    name: str
    tags: list[str]
    prep_time_minutes: int | None = None
    effort: EffortLevel | None = None
    favorite_score: int
    nutrition_template_id: int | None = None
    last_made_at: datetime | None = None
    times_made: int
    ingredients: list[FavoriteMealIngredient]
    created_at: datetime
    updated_at: datetime


class MealMatch(BaseModel):
    meal_id: int
    meal_name: str
    score: int
    available_required_ingredients: list[str]
    missing_required_ingredients: list[str]
    available_optional_ingredients: list[str]
    use_soon_ingredients: list[str]
    maybe_ingredients: list[str]
    out_ingredients: list[str]
    score_breakdown: list[dict]


class MealMatchRequest(BaseModel):
    effort: EffortLevel | None = None
    tag: str | None = None


class ShoppingListItemCreate(BaseModel):
    name: str
    source: ShoppingSource = "manual"
    linked_meal_ids: list[int] = Field(default_factory=list)
    notes: str | None = None


class ShoppingListItem(BaseModel):
    id: int
    user_id: int
    canonical_name: str
    display_name: str
    checked: bool
    source: ShoppingSource
    linked_meal_ids: list[int]
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
