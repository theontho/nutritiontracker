# Nutrition Tracker API Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI REST API for nutrition tracking with pre-loaded USDA and OpenFoodFacts databases, diary logging, recipe math, weight tracking, and daily stats.

**Architecture:** FastAPI app with SQLite backend using a repository pattern. Food data is bulk-imported from USDA FoodData Central and OpenFoodFacts via normalization scripts. FTS5 provides full-text search with fuzzy matching. Diary entries snapshot food data at log time for historical integrity.

**Tech Stack:** Python 3.12+, FastAPI, SQLite (FTS5), Pydantic v2, uvicorn, pytest

**Design note:** The spec defines NutrientsPer100 as a separate entity with FK on Food. This plan flattens all 20 nutrient columns directly into the `foods` table. This avoids JOINs and is the pragmatic choice for SQLite. The Pydantic `NutrientsPer100` model still exists for validation and serialization.

---

## File Structure

```
nutritiontracker/
  app/
    __init__.py
    main.py                          # FastAPI app, router registration, health check
    config.py                        # Settings (DB path, defaults)
    database.py                      # SQLite connection management, schema init
    models/
      __init__.py
      food.py                        # Food, NutrientsPer100 Pydantic models
      diary.py                       # DiaryEntry Pydantic models
      recipe.py                      # Recipe, RecipeIngredient Pydantic models
      weight.py                      # WeightEntry Pydantic models
    providers/
      __init__.py
      base.py                        # Base normalizer interface
      open_food_facts.py             # OFF CSV/JSONL → Food normalizer
      food_data_central.py           # USDA CSV/JSON → Food normalizer
    services/
      __init__.py
      food_search.py                 # FTS5 search + fuzzy matching + dedup
      diary.py                       # Diary business logic + nutrient computation
      recipe_nutrition.py            # Recipe math (per-100g, per-serving)
      unit_conversion.py             # Unit → grams conversion with density
    repositories/
      __init__.py
      foods.py                       # Food CRUD + FTS5 queries
      diary.py                       # DiaryEntry CRUD
      recipes.py                     # Recipe CRUD
      weight.py                      # WeightEntry CRUD
    routes/
      __init__.py
      foods.py                       # /foods endpoints
      diary.py                       # /diary endpoints
      recipes.py                     # /recipes endpoints
      stats.py                       # /stats endpoints
      weight.py                      # /weight endpoints
  scripts/
    import_usda.py                   # Bulk import USDA FoodData Central
    import_off.py                    # Bulk import OpenFoodFacts
  tests/
    __init__.py
    conftest.py                      # Shared fixtures (test DB, client)
    test_models.py                   # Model validation tests
    test_unit_conversion.py          # Unit conversion tests
    test_food_repository.py          # Food repo + FTS5 tests
    test_food_search.py              # Search service tests
    test_diary.py                    # Diary CRUD + stats tests
    test_recipes.py                  # Recipe CRUD + nutrition math tests
    test_weight.py                   # Weight CRUD tests
    test_routes_foods.py             # Food endpoint integration tests
    test_routes_diary.py             # Diary endpoint integration tests
    test_routes_recipes.py           # Recipe endpoint integration tests
    test_routes_stats.py             # Stats endpoint integration tests
    test_routes_weight.py            # Weight endpoint integration tests
    test_providers_usda.py           # USDA normalizer tests
    test_providers_off.py            # OFF normalizer tests
  pyproject.toml
  README.md
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Create: `app/database.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "nutritiontracker"
version = "0.1.0"
description = "Open-source nutrition tracker REST API"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create app/config.py**

```python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    db_path: Path = Path("data/nutrition.db")
    default_user_id: int = 1
    api_version: str = "0.1.0"

    model_config = {"env_prefix": "NT_"}


settings = Settings()
```

- [ ] **Step 3: Create app/database.py**

```python
import sqlite3
from pathlib import Path
from app.config import settings


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL CHECK(source IN ('custom','open_food_facts','food_data_central','recipe')),
            source_code TEXT,
            name TEXT NOT NULL,
            brand TEXT,
            barcode TEXT,
            image_url TEXT,
            serving_quantity REAL,
            serving_unit TEXT,
            serving_size_text TEXT,
            base_quantity REAL NOT NULL DEFAULT 100,
            base_unit TEXT NOT NULL DEFAULT 'g',
            density_g_per_ml REAL,
            calories_kcal REAL DEFAULT 0,
            protein_g REAL DEFAULT 0,
            carbs_g REAL DEFAULT 0,
            fat_g REAL DEFAULT 0,
            sugar_g REAL DEFAULT 0,
            saturated_fat_g REAL DEFAULT 0,
            fiber_g REAL DEFAULT 0,
            sodium_mg REAL DEFAULT 0,
            potassium_mg REAL DEFAULT 0,
            calcium_mg REAL DEFAULT 0,
            iron_mg REAL DEFAULT 0,
            magnesium_mg REAL DEFAULT 0,
            zinc_mg REAL DEFAULT 0,
            phosphorus_mg REAL DEFAULT 0,
            vitamin_a_ug REAL DEFAULT 0,
            vitamin_c_mg REAL DEFAULT 0,
            vitamin_d_ug REAL DEFAULT 0,
            vitamin_b6_mg REAL DEFAULT 0,
            vitamin_b12_ug REAL DEFAULT 0,
            niacin_mg REAL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            meal_type TEXT NOT NULL CHECK(meal_type IN ('breakfast','lunch','dinner','snack')),
            food_id INTEGER NOT NULL REFERENCES foods(id),
            food_snapshot TEXT NOT NULL,
            amount REAL NOT NULL,
            unit TEXT NOT NULL,
            grams REAL NOT NULL,
            nutrients_total TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            name TEXT NOT NULL,
            servings REAL NOT NULL,
            total_weight_g REAL NOT NULL,
            ingredients TEXT NOT NULL,
            nutrients_per_100 TEXT NOT NULL,
            nutrients_per_serving TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS weight_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_foods_barcode ON foods(barcode);
        CREATE INDEX IF NOT EXISTS idx_foods_source ON foods(source);
        CREATE INDEX IF NOT EXISTS idx_foods_source_code ON foods(source, source_code);
        CREATE INDEX IF NOT EXISTS idx_diary_user_date ON diary_entries(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_weight_user_date ON weight_entries(user_id, date);
    """)
```

- [ ] **Step 4: Create app/main.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.database import get_connection, init_schema
from app.repositories.foods import FoodRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    init_schema(conn)
    FoodRepository(conn).ensure_fts()
    app.state.db = conn
    yield
    conn.close()


app = FastAPI(title="Nutrition Tracker", version=settings.api_version, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.api_version}
```

- [ ] **Step 5: Create app/__init__.py and tests/__init__.py**

Both empty files.

- [ ] **Step 6: Create tests/conftest.py**

```python
import pytest
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_schema


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db):
    app.state.db = db
    with TestClient(app) as c:
        yield c
```

- [ ] **Step 7: Install dependencies and run health check test**

```bash
cd ~/work/code/nutritiontracker
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Write a quick smoke test in `tests/test_health.py`:

```python
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

Run: `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml app/ tests/
git commit -m "feat: project scaffolding with FastAPI, SQLite schema, health check"
```

---

### Task 2: Pydantic Models

**Files:**
- Create: `app/models/__init__.py`
- Create: `app/models/food.py`
- Create: `app/models/diary.py`
- Create: `app/models/recipe.py`
- Create: `app/models/weight.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing model validation tests**

```python
# tests/test_models.py
import pytest
from app.models.food import NutrientsPer100, Food, FoodCreate
from app.models.diary import DiaryEntryCreate
from app.models.recipe import RecipeCreate, RecipeIngredientInput
from app.models.weight import WeightEntryCreate


def test_nutrients_defaults_to_zeros():
    n = NutrientsPer100()
    assert n.calories_kcal == 0
    assert n.protein_g == 0
    assert n.niacin_mg == 0


def test_food_create_minimal():
    f = FoodCreate(name="Banana", source="custom")
    assert f.name == "Banana"
    assert f.brand is None


def test_food_create_rejects_invalid_source():
    with pytest.raises(ValueError):
        FoodCreate(name="X", source="invalid")


def test_diary_entry_create():
    e = DiaryEntryCreate(food_id=1, amount=1.5, unit="cup", meal_type="breakfast")
    assert e.meal_type == "breakfast"


def test_diary_entry_rejects_invalid_meal_type():
    with pytest.raises(ValueError):
        DiaryEntryCreate(food_id=1, amount=1, unit="g", meal_type="brunch")


def test_recipe_create():
    r = RecipeCreate(
        name="Oatmeal",
        servings=2,
        total_weight_g=400,
        ingredients=[
            RecipeIngredientInput(food_id=1, amount=100, unit="g"),
            RecipeIngredientInput(food_id=2, amount=200, unit="ml"),
        ],
    )
    assert len(r.ingredients) == 2


def test_weight_entry_create():
    w = WeightEntryCreate(weight_kg=85.5, date="2026-05-19")
    assert w.weight_kg == 85.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — import errors

- [ ] **Step 3: Implement app/models/food.py**

```python
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class NutrientsPer100(BaseModel):
    calories_kcal: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    sugar_g: float = 0
    saturated_fat_g: float = 0
    fiber_g: float = 0
    sodium_mg: float = 0
    potassium_mg: float = 0
    calcium_mg: float = 0
    iron_mg: float = 0
    magnesium_mg: float = 0
    zinc_mg: float = 0
    phosphorus_mg: float = 0
    vitamin_a_ug: float = 0
    vitamin_c_mg: float = 0
    vitamin_d_ug: float = 0
    vitamin_b6_mg: float = 0
    vitamin_b12_ug: float = 0
    niacin_mg: float = 0


SourceType = Literal["custom", "open_food_facts", "food_data_central", "recipe"]


class FoodCreate(BaseModel):
    source: SourceType = "custom"
    source_code: str | None = None
    name: str
    brand: str | None = None
    barcode: str | None = None
    image_url: str | None = None
    serving_quantity: float | None = None
    serving_unit: str | None = None
    serving_size_text: str | None = None
    base_quantity: float = 100
    base_unit: str = "g"
    density_g_per_ml: float | None = None
    nutrients: NutrientsPer100 = Field(default_factory=NutrientsPer100)


class Food(FoodCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class FoodUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    barcode: str | None = None
    image_url: str | None = None
    serving_quantity: float | None = None
    serving_unit: str | None = None
    serving_size_text: str | None = None
    density_g_per_ml: float | None = None
    nutrients: NutrientsPer100 | None = None
```

- [ ] **Step 4: Implement app/models/diary.py**

```python
from datetime import datetime
from pydantic import BaseModel
from typing import Literal

MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class DiaryEntryCreate(BaseModel):
    food_id: int
    amount: float
    unit: str
    meal_type: MealType


class DiaryEntryUpdate(BaseModel):
    amount: float | None = None
    unit: str | None = None
    meal_type: MealType | None = None


class DiaryEntry(BaseModel):
    id: int
    user_id: int
    date: str
    meal_type: MealType
    food_id: int
    food_snapshot: dict
    amount: float
    unit: str
    grams: float
    nutrients_total: dict
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 5: Implement app/models/recipe.py**

```python
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
```

- [ ] **Step 6: Implement app/models/weight.py**

```python
from datetime import datetime
from pydantic import BaseModel


class WeightEntryCreate(BaseModel):
    date: str
    weight_kg: float
    notes: str | None = None


class WeightEntryUpdate(BaseModel):
    weight_kg: float | None = None
    notes: str | None = None


class WeightEntry(BaseModel):
    id: int
    user_id: int
    date: str
    weight_kg: float
    notes: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 7: Create app/models/__init__.py**

Empty file.

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add app/models/ tests/test_models.py
git commit -m "feat: add Pydantic models for food, diary, recipe, weight"
```

---

### Task 3: Unit Conversion Service

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/unit_conversion.py`
- Create: `tests/test_unit_conversion.py`

- [ ] **Step 1: Write failing unit conversion tests**

```python
# tests/test_unit_conversion.py
import pytest
from app.services.unit_conversion import convert_to_grams, ConversionResult


def test_grams_identity():
    r = convert_to_grams(100, "g")
    assert r.grams == 100
    assert r.approximate is False


def test_kg_to_grams():
    r = convert_to_grams(1, "kg")
    assert r.grams == 1000


def test_oz_to_grams():
    r = convert_to_grams(1, "oz")
    assert abs(r.grams - 28.3495) < 0.01


def test_lb_to_grams():
    r = convert_to_grams(1, "lb")
    assert abs(r.grams - 453.592) < 0.1


def test_ml_with_density():
    r = convert_to_grams(100, "ml", density_g_per_ml=1.03)
    assert r.grams == 103
    assert r.approximate is False


def test_ml_without_density_uses_water():
    r = convert_to_grams(100, "ml")
    assert r.grams == 100
    assert r.approximate is True


def test_cup_to_grams():
    r = convert_to_grams(1, "cup", density_g_per_ml=1.0)
    assert abs(r.grams - 236.588) < 0.1


def test_tbsp():
    r = convert_to_grams(1, "tbsp", density_g_per_ml=1.0)
    assert abs(r.grams - 14.787) < 0.01


def test_tsp():
    r = convert_to_grams(1, "tsp", density_g_per_ml=1.0)
    assert abs(r.grams - 4.929) < 0.01


def test_fl_oz():
    r = convert_to_grams(1, "fl_oz", density_g_per_ml=1.0)
    assert abs(r.grams - 29.574) < 0.01


def test_serving_with_quantity():
    r = convert_to_grams(2, "serving", serving_quantity=50, serving_unit="g")
    assert r.grams == 100
    assert r.approximate is False


def test_serving_without_quantity_raises():
    with pytest.raises(ValueError, match="serving"):
        convert_to_grams(1, "serving")


def test_unknown_unit_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        convert_to_grams(1, "bushel")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_unit_conversion.py -v`
Expected: FAIL — import errors

- [ ] **Step 3: Implement unit conversion**

```python
# app/services/unit_conversion.py
from dataclasses import dataclass

WEIGHT_TO_GRAMS = {
    "g": 1.0,
    "kg": 1000.0,
    "oz": 28.3495,
    "lb": 453.592,
}

VOLUME_TO_ML = {
    "ml": 1.0,
    "l": 1000.0,
    "cup": 236.588,
    "tbsp": 14.787,
    "tsp": 4.929,
    "fl_oz": 29.574,
}

PORTION_UNITS = {"serving", "piece", "slice"}


@dataclass
class ConversionResult:
    grams: float
    approximate: bool


def convert_to_grams(
    amount: float,
    unit: str,
    density_g_per_ml: float | None = None,
    serving_quantity: float | None = None,
    serving_unit: str | None = None,
) -> ConversionResult:
    unit = unit.lower().strip()

    if unit in WEIGHT_TO_GRAMS:
        return ConversionResult(grams=amount * WEIGHT_TO_GRAMS[unit], approximate=False)

    if unit in VOLUME_TO_ML:
        ml = amount * VOLUME_TO_ML[unit]
        if density_g_per_ml is not None:
            return ConversionResult(grams=ml * density_g_per_ml, approximate=False)
        return ConversionResult(grams=ml * 1.0, approximate=True)

    if unit in PORTION_UNITS:
        if serving_quantity is None or serving_unit is None:
            raise ValueError(
                f"Cannot convert '{unit}' without serving_quantity and serving_unit on the food"
            )
        per_serving = convert_to_grams(serving_quantity, serving_unit, density_g_per_ml)
        return ConversionResult(
            grams=amount * per_serving.grams,
            approximate=per_serving.approximate,
        )

    raise ValueError(f"Unsupported unit: '{unit}'")
```

- [ ] **Step 4: Create app/services/__init__.py**

Empty file.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_unit_conversion.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/services/ tests/test_unit_conversion.py
git commit -m "feat: add unit conversion service with weight, volume, portion support"
```

---

### Task 4: Food Repository + FTS5 Search

**Files:**
- Create: `app/repositories/__init__.py`
- Create: `app/repositories/foods.py`
- Create: `tests/test_food_repository.py`

- [ ] **Step 1: Write failing food repository tests**

```python
# tests/test_food_repository.py
import json
import pytest
from app.repositories.foods import FoodRepository


@pytest.fixture
def repo(db):
    r = FoodRepository(db)
    r.ensure_fts()
    return r


def test_create_and_get(repo):
    food_id = repo.create(
        source="custom", name="Banana", calories_kcal=89, protein_g=1.1,
        carbs_g=22.8, fat_g=0.3,
    )
    food = repo.get(food_id)
    assert food["name"] == "Banana"
    assert food["calories_kcal"] == 89


def test_get_nonexistent_returns_none(repo):
    assert repo.get(9999) is None


def test_search_by_name(repo):
    repo.create(source="custom", name="Chicken Breast Grilled")
    repo.create(source="custom", name="Chicken Thigh")
    repo.create(source="custom", name="Banana")
    results = repo.search("chicken")
    assert len(results) == 2


def test_search_prefix(repo):
    repo.create(source="custom", name="Broccoli")
    results = repo.search("broc")
    assert len(results) == 1
    assert results[0]["name"] == "Broccoli"


def test_search_with_source_filter(repo):
    repo.create(source="open_food_facts", name="Oats OFF")
    repo.create(source="food_data_central", name="Oats USDA")
    results = repo.search("oats", source="food_data_central")
    assert len(results) == 1
    assert results[0]["name"] == "Oats USDA"


def test_search_limit_offset(repo):
    for i in range(10):
        repo.create(source="custom", name=f"Apple Variety {i}")
    results = repo.search("apple", limit=3, offset=0)
    assert len(results) == 3
    results2 = repo.search("apple", limit=3, offset=3)
    assert len(results2) == 3
    assert results[0]["id"] != results2[0]["id"]


def test_barcode_lookup(repo):
    repo.create(source="open_food_facts", name="Granola Bar", barcode="1234567890")
    food = repo.get_by_barcode("1234567890")
    assert food["name"] == "Granola Bar"


def test_update_food(repo):
    food_id = repo.create(source="custom", name="Old Name")
    repo.update(food_id, name="New Name", protein_g=25)
    food = repo.get(food_id)
    assert food["name"] == "New Name"
    assert food["protein_g"] == 25


def test_delete_food(repo):
    food_id = repo.create(source="custom", name="To Delete")
    repo.delete(food_id)
    assert repo.get(food_id) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_food_repository.py -v`
Expected: FAIL — import errors

- [ ] **Step 3: Implement food repository**

```python
# app/repositories/foods.py
import sqlite3
from datetime import datetime


class FoodRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def ensure_fts(self):
        self.conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS foods_fts USING fts5(
                name, brand, content='foods', content_rowid='id',
                tokenize='porter unicode61'
            );

            CREATE TRIGGER IF NOT EXISTS foods_ai AFTER INSERT ON foods BEGIN
                INSERT INTO foods_fts(rowid, name, brand)
                VALUES (new.id, new.name, new.brand);
            END;

            CREATE TRIGGER IF NOT EXISTS foods_ad AFTER DELETE ON foods BEGIN
                INSERT INTO foods_fts(foods_fts, rowid, name, brand)
                VALUES ('delete', old.id, old.name, old.brand);
            END;

            CREATE TRIGGER IF NOT EXISTS foods_au AFTER UPDATE ON foods BEGIN
                INSERT INTO foods_fts(foods_fts, rowid, name, brand)
                VALUES ('delete', old.id, old.name, old.brand);
                INSERT INTO foods_fts(rowid, name, brand)
                VALUES (new.id, new.name, new.brand);
            END;
        """)

    def create(self, *, source: str, name: str, **kwargs) -> int:
        nutrient_fields = [
            "calories_kcal", "protein_g", "carbs_g", "fat_g", "sugar_g",
            "saturated_fat_g", "fiber_g", "sodium_mg", "potassium_mg",
            "calcium_mg", "iron_mg", "magnesium_mg", "zinc_mg", "phosphorus_mg",
            "vitamin_a_ug", "vitamin_c_mg", "vitamin_d_ug", "vitamin_b6_mg",
            "vitamin_b12_ug", "niacin_mg",
        ]
        other_fields = [
            "source_code", "brand", "barcode", "image_url", "serving_quantity",
            "serving_unit", "serving_size_text", "base_quantity", "base_unit",
            "density_g_per_ml",
        ]
        all_fields = other_fields + nutrient_fields
        fields = ["source", "name"]
        values = [source, name]
        for f in all_fields:
            if f in kwargs:
                fields.append(f)
                values.append(kwargs[f])
        placeholders = ", ".join(["?"] * len(values))
        cols = ", ".join(fields)
        cur = self.conn.execute(
            f"INSERT INTO foods ({cols}) VALUES ({placeholders})", values
        )
        self.conn.commit()
        return cur.lastrowid

    def create_no_commit(self, **kwargs) -> int:
        """Same as create() but without committing — caller manages transactions for bulk imports."""
        source = kwargs.pop("source")
        name = kwargs.pop("name")
        nutrient_fields = [
            "calories_kcal", "protein_g", "carbs_g", "fat_g", "sugar_g",
            "saturated_fat_g", "fiber_g", "sodium_mg", "potassium_mg",
            "calcium_mg", "iron_mg", "magnesium_mg", "zinc_mg", "phosphorus_mg",
            "vitamin_a_ug", "vitamin_c_mg", "vitamin_d_ug", "vitamin_b6_mg",
            "vitamin_b12_ug", "niacin_mg",
        ]
        other_fields = [
            "source_code", "brand", "barcode", "image_url", "serving_quantity",
            "serving_unit", "serving_size_text", "base_quantity", "base_unit",
            "density_g_per_ml",
        ]
        all_fields = other_fields + nutrient_fields
        fields = ["source", "name"]
        values = [source, name]
        for f in all_fields:
            if f in kwargs:
                fields.append(f)
                values.append(kwargs[f])
        placeholders = ", ".join(["?"] * len(values))
        cols = ", ".join(fields)
        cur = self.conn.execute(
            f"INSERT INTO foods ({cols}) VALUES ({placeholders})", values
        )
        return cur.lastrowid

    def get(self, food_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM foods WHERE id = ?", (food_id,)).fetchone()
        return dict(row) if row else None

    def get_by_barcode(self, barcode: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM foods WHERE barcode = ?", (barcode,)
        ).fetchone()
        return dict(row) if row else None

    def search(
        self, query: str, *, source: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        fts_query = " ".join(f"{term}*" for term in query.strip().split())
        if source and source != "all":
            rows = self.conn.execute(
                """SELECT f.* FROM foods_fts fts
                   JOIN foods f ON f.id = fts.rowid
                   WHERE foods_fts MATCH ? AND f.source = ?
                   ORDER BY rank
                   LIMIT ? OFFSET ?""",
                (fts_query, source, limit, offset),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT f.* FROM foods_fts fts
                   JOIN foods f ON f.id = fts.rowid
                   WHERE foods_fts MATCH ?
                   ORDER BY rank
                   LIMIT ? OFFSET ?""",
                (fts_query, limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]

    def update(self, food_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [food_id]
        self.conn.execute(
            f"UPDATE foods SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete(self, food_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM foods WHERE id = ?", (food_id,))
        self.conn.commit()
        return cur.rowcount > 0
```

- [ ] **Step 4: Create app/repositories/__init__.py**

Empty file.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_food_repository.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/repositories/ tests/test_food_repository.py
git commit -m "feat: add food repository with FTS5 search, CRUD, barcode lookup"
```

---

### Task 4b: Food Search Service (Deduplication)

**Files:**
- Create: `app/services/food_search.py`
- Create: `tests/test_food_search.py`

- [ ] **Step 1: Write failing search dedup tests**

```python
# tests/test_food_search.py
from app.repositories.foods import FoodRepository
from app.services.food_search import FoodSearchService


def test_dedup_by_barcode(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    repo.create(source="open_food_facts", name="Banana", barcode="123", calories_kcal=89, protein_g=1.1)
    repo.create(source="food_data_central", name="Banana, raw", barcode="123", calories_kcal=89, protein_g=1.1, fiber_g=2.6)
    svc = FoodSearchService(repo)
    results = svc.search("banana")
    # Should deduplicate — prefer FDC because it has more nutrient data (fiber_g)
    assert len(results) == 1
    assert results[0]["fiber_g"] == 2.6


def test_dedup_by_name(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    repo.create(source="open_food_facts", name="Chicken Breast", calories_kcal=165)
    repo.create(source="food_data_central", name="Chicken Breast", calories_kcal=165, protein_g=31)
    svc = FoodSearchService(repo)
    results = svc.search("chicken breast")
    assert len(results) == 1


def test_no_dedup_different_foods(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    repo.create(source="open_food_facts", name="Banana")
    repo.create(source="food_data_central", name="Banana Chips")
    svc = FoodSearchService(repo)
    results = svc.search("banana")
    assert len(results) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_food_search.py -v`
Expected: FAIL

- [ ] **Step 3: Implement food search service**

```python
# app/services/food_search.py
from app.repositories.foods import FoodRepository
from app.models.food import NutrientsPer100

NUTRIENT_FIELDS = list(NutrientsPer100.model_fields.keys())


def _nutrient_completeness(food: dict) -> int:
    return sum(1 for f in NUTRIENT_FIELDS if (food.get(f) or 0) > 0)


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().strip().split())


class FoodSearchService:
    def __init__(self, repo: FoodRepository):
        self.repo = repo

    def search(
        self, query: str, *, source: str | None = None,
        limit: int = 20, offset: int = 0,
    ) -> list[dict]:
        # Fetch extra results to allow for dedup shrinkage
        raw = self.repo.search(query, source=source, limit=limit * 2, offset=offset)
        deduped = self._deduplicate(raw)
        return deduped[:limit]

    def _deduplicate(self, foods: list[dict]) -> list[dict]:
        seen_barcodes: dict[str, int] = {}
        seen_names: dict[str, int] = {}
        result: list[dict] = []

        for food in foods:
            barcode = food.get("barcode")
            norm_name = _normalize_name(food.get("name", ""))
            dup_idx = None

            if barcode and barcode in seen_barcodes:
                dup_idx = seen_barcodes[barcode]
            elif norm_name in seen_names:
                dup_idx = seen_names[norm_name]

            if dup_idx is not None:
                existing = result[dup_idx]
                if _nutrient_completeness(food) > _nutrient_completeness(existing):
                    result[dup_idx] = food
                continue

            idx = len(result)
            if barcode:
                seen_barcodes[barcode] = idx
            seen_names[norm_name] = idx
            result.append(food)

        return result
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_food_search.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/food_search.py tests/test_food_search.py
git commit -m "feat: add food search service with deduplication by barcode and name"
```

---

### Task 5: Food Routes

**Files:**
- Create: `app/routes/__init__.py`
- Create: `app/routes/foods.py`
- Create: `tests/test_routes_foods.py`

- [ ] **Step 1: Write failing food route tests**

```python
# tests/test_routes_foods.py
from app.repositories.foods import FoodRepository


def _seed_food(db, name="Banana", **kwargs):
    repo = FoodRepository(db)
    repo.ensure_fts()
    return repo.create(source="custom", name=name, **kwargs)


def test_search_foods(client, db):
    _seed_food(db, "Chicken Breast", protein_g=31)
    _seed_food(db, "Chicken Thigh", protein_g=26)
    r = client.get("/foods/search?q=chicken")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_food(client, db):
    fid = _seed_food(db, "Banana", calories_kcal=89)
    r = client.get(f"/foods/{fid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Banana"


def test_get_food_404(client):
    r = client.get("/foods/9999")
    assert r.status_code == 404


def test_barcode_lookup(client, db):
    _seed_food(db, "Granola", barcode="12345")
    r = client.get("/foods/barcode/12345")
    assert r.status_code == 200
    assert r.json()["name"] == "Granola"


def test_barcode_404(client):
    r = client.get("/foods/barcode/nope")
    assert r.status_code == 404


def test_create_custom_food(client, db):
    FoodRepository(db).ensure_fts()
    r = client.post("/foods", json={"name": "My Food", "source": "custom",
                                     "nutrients": {"calories_kcal": 100}})
    assert r.status_code == 201
    assert r.json()["name"] == "My Food"


def test_update_custom_food(client, db):
    fid = _seed_food(db, "Old")
    r = client.patch(f"/foods/{fid}", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


def test_delete_custom_food(client, db):
    fid = _seed_food(db, "Gone")
    r = client.delete(f"/foods/{fid}")
    assert r.status_code == 204
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_routes_foods.py -v`
Expected: FAIL

- [ ] **Step 3: Implement food routes**

```python
# app/routes/foods.py
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
```

- [ ] **Step 4: Register router in app/main.py**

Add to `app/main.py` after `app` is created:

```python
from app.routes.foods import router as foods_router
app.include_router(foods_router)
```

- [ ] **Step 5: Create app/routes/__init__.py**

Empty file.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_routes_foods.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add app/routes/ tests/test_routes_foods.py
git commit -m "feat: add food search, CRUD, and barcode lookup endpoints"
```

---

### Task 6: Diary Repository + Routes

**Files:**
- Create: `app/repositories/diary.py`
- Create: `app/services/diary.py`
- Create: `app/routes/diary.py`
- Create: `tests/test_diary.py`
- Create: `tests/test_routes_diary.py`

- [ ] **Step 1: Write failing diary repository tests**

```python
# tests/test_diary.py
import json
import pytest
from app.repositories.foods import FoodRepository
from app.repositories.diary import DiaryRepository


@pytest.fixture
def food_repo(db):
    r = FoodRepository(db)
    r.ensure_fts()
    return r


@pytest.fixture
def diary_repo(db):
    return DiaryRepository(db)


@pytest.fixture
def banana_id(food_repo):
    return food_repo.create(source="custom", name="Banana", calories_kcal=89, protein_g=1.1, carbs_g=22.8, fat_g=0.3)


def test_create_and_get_entry(diary_repo, banana_id):
    entry_id = diary_repo.create(
        user_id=1, date="2026-05-19", meal_type="breakfast",
        food_id=banana_id, food_snapshot={"name": "Banana"},
        amount=1, unit="serving", grams=118,
        nutrients_total={"calories_kcal": 105},
    )
    entry = diary_repo.get(entry_id)
    assert entry is not None
    assert entry["meal_type"] == "breakfast"


def test_list_by_date(diary_repo, banana_id):
    diary_repo.create(
        user_id=1, date="2026-05-19", meal_type="breakfast",
        food_id=banana_id, food_snapshot={}, amount=1, unit="g", grams=100,
        nutrients_total={},
    )
    diary_repo.create(
        user_id=1, date="2026-05-20", meal_type="lunch",
        food_id=banana_id, food_snapshot={}, amount=1, unit="g", grams=100,
        nutrients_total={},
    )
    entries = diary_repo.list_by_date(user_id=1, date="2026-05-19")
    assert len(entries) == 1


def test_update_entry(diary_repo, banana_id):
    entry_id = diary_repo.create(
        user_id=1, date="2026-05-19", meal_type="breakfast",
        food_id=banana_id, food_snapshot={}, amount=1, unit="g", grams=100,
        nutrients_total={},
    )
    diary_repo.update(entry_id, amount=2, grams=200)
    entry = diary_repo.get(entry_id)
    assert entry["amount"] == 2


def test_delete_entry(diary_repo, banana_id):
    entry_id = diary_repo.create(
        user_id=1, date="2026-05-19", meal_type="breakfast",
        food_id=banana_id, food_snapshot={}, amount=1, unit="g", grams=100,
        nutrients_total={},
    )
    diary_repo.delete(entry_id)
    assert diary_repo.get(entry_id) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_diary.py -v`
Expected: FAIL

- [ ] **Step 3: Implement diary repository**

```python
# app/repositories/diary.py
import json
import sqlite3


class DiaryRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, *, user_id: int, date: str, meal_type: str,
               food_id: int, food_snapshot: dict, amount: float,
               unit: str, grams: float, nutrients_total: dict) -> int:
        cur = self.conn.execute(
            """INSERT INTO diary_entries
               (user_id, date, meal_type, food_id, food_snapshot, amount, unit, grams, nutrients_total)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, date, meal_type, food_id,
             json.dumps(food_snapshot), amount, unit, grams,
             json.dumps(nutrients_total)),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, entry_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM diary_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["food_snapshot"] = json.loads(d["food_snapshot"])
        d["nutrients_total"] = json.loads(d["nutrients_total"])
        return d

    def list_by_date(self, *, user_id: int, date: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM diary_entries WHERE user_id = ? AND date = ? ORDER BY created_at",
            (user_id, date),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["food_snapshot"] = json.loads(d["food_snapshot"])
            d["nutrients_total"] = json.loads(d["nutrients_total"])
            results.append(d)
        return results

    def update(self, entry_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        for k in ("food_snapshot", "nutrients_total"):
            if k in kwargs and isinstance(kwargs[k], dict):
                kwargs[k] = json.dumps(kwargs[k])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [entry_id]
        self.conn.execute(
            f"UPDATE diary_entries SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete(self, entry_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cur.rowcount > 0
```

- [ ] **Step 4: Run repository tests**

Run: `pytest tests/test_diary.py -v`
Expected: all PASS

- [ ] **Step 5: Implement diary service**

```python
# app/services/diary.py
import json
from app.models.food import NutrientsPer100
from app.services.unit_conversion import convert_to_grams


def compute_entry_nutrients(food: dict, grams: float) -> dict:
    nutrient_fields = list(NutrientsPer100.model_fields.keys())
    result = {}
    for field in nutrient_fields:
        per_100 = food.get(field, 0) or 0
        result[field] = round(per_100 * grams / 100, 2)
    return result


def build_food_snapshot(food: dict) -> dict:
    exclude = {"created_at", "updated_at"}
    return {k: v for k, v in food.items() if k not in exclude}
```

- [ ] **Step 6: Write failing diary route tests**

```python
# tests/test_routes_diary.py
from app.repositories.foods import FoodRepository


def _seed(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    return repo.create(
        source="custom", name="Banana", calories_kcal=89,
        protein_g=1.1, carbs_g=22.8, fat_g=0.3,
        serving_quantity=118, serving_unit="g",
    )


def test_create_diary_entry(client, db):
    fid = _seed(db)
    r = client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 100, "unit": "g", "meal_type": "breakfast"
    })
    assert r.status_code == 201
    assert r.json()["grams"] == 100
    assert r.json()["nutrients_total"]["calories_kcal"] == 89


def test_list_diary(client, db):
    fid = _seed(db)
    client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 100, "unit": "g", "meal_type": "breakfast"
    })
    r = client.get("/diary/2026-05-19")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_update_diary_entry(client, db):
    fid = _seed(db)
    r = client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 100, "unit": "g", "meal_type": "breakfast"
    })
    eid = r.json()["id"]
    r2 = client.patch(f"/diary/entries/{eid}", json={"amount": 200, "unit": "g"})
    assert r2.status_code == 200
    assert r2.json()["grams"] == 200


def test_delete_diary_entry(client, db):
    fid = _seed(db)
    r = client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 100, "unit": "g", "meal_type": "breakfast"
    })
    eid = r.json()["id"]
    r2 = client.delete(f"/diary/entries/{eid}")
    assert r2.status_code == 204
```

- [ ] **Step 7: Implement diary routes**

```python
# app/routes/diary.py
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
    repo = FoodRepository(request.app.state.db)
    repo.ensure_fts()
    return repo


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
```

- [ ] **Step 8: Register diary router in app/main.py**

```python
from app.routes.diary import router as diary_router
app.include_router(diary_router)
```

- [ ] **Step 9: Run all tests**

Run: `pytest tests/test_diary.py tests/test_routes_diary.py -v`
Expected: all PASS

- [ ] **Step 10: Commit**

```bash
git add app/repositories/diary.py app/services/diary.py app/routes/diary.py tests/test_diary.py tests/test_routes_diary.py app/main.py
git commit -m "feat: add diary entry CRUD with nutrient computation and unit conversion"
```

---

### Task 7: Stats Routes

**Files:**
- Create: `app/routes/stats.py`
- Create: `tests/test_routes_stats.py`

- [ ] **Step 1: Write failing stats route tests**

```python
# tests/test_routes_stats.py
from app.repositories.foods import FoodRepository
from app.repositories.diary import DiaryRepository
from app.services.diary import compute_entry_nutrients, build_food_snapshot


def _seed_entries(db):
    food_repo = FoodRepository(db)
    food_repo.ensure_fts()
    fid = food_repo.create(
        source="custom", name="Banana", calories_kcal=89,
        protein_g=1.1, carbs_g=22.8, fat_g=0.3,
    )
    food = food_repo.get(fid)

    diary = DiaryRepository(db)
    for meal in ["breakfast", "lunch"]:
        nutrients = compute_entry_nutrients(food, 100)
        diary.create(
            user_id=1, date="2026-05-19", meal_type=meal,
            food_id=fid, food_snapshot=build_food_snapshot(food),
            amount=100, unit="g", grams=100,
            nutrients_total=nutrients,
        )
    return fid


def test_daily_stats(client, db):
    _seed_entries(db)
    r = client.get("/stats/daily/2026-05-19")
    assert r.status_code == 200
    data = r.json()
    assert data["date"] == "2026-05-19"
    assert data["entry_count"] == 2
    assert data["total"]["calories_kcal"] == 178
    assert data["meals"]["breakfast"]["calories_kcal"] == 89
    assert data["meals"]["lunch"]["calories_kcal"] == 89
    assert data["meals"]["dinner"]["calories_kcal"] == 0


def test_daily_stats_empty(client, db):
    r = client.get("/stats/daily/2026-05-19")
    assert r.status_code == 200
    assert r.json()["entry_count"] == 0
    assert r.json()["total"]["calories_kcal"] == 0


def test_range_stats(client, db):
    _seed_entries(db)
    r = client.get("/stats/range?start=2026-05-18&end=2026-05-20")
    assert r.status_code == 200
    days = r.json()
    assert len(days) == 1
    assert days[0]["date"] == "2026-05-19"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_routes_stats.py -v`
Expected: FAIL

- [ ] **Step 3: Implement stats routes**

```python
# app/routes/stats.py
from fastapi import APIRouter, Request
from app.models.food import NutrientsPer100
from app.repositories.diary import DiaryRepository
from app.config import settings

router = APIRouter(prefix="/stats", tags=["stats"])

NUTRIENT_FIELDS = list(NutrientsPer100.model_fields.keys())
MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def _zero_nutrients() -> dict:
    return {f: 0.0 for f in NUTRIENT_FIELDS}


def _sum_nutrients(a: dict, b: dict) -> dict:
    return {f: round(a.get(f, 0) + b.get(f, 0), 2) for f in NUTRIENT_FIELDS}


def _compute_daily(entries: list[dict], date: str) -> dict:
    meals = {m: _zero_nutrients() for m in MEAL_TYPES}
    for entry in entries:
        nt = entry.get("nutrients_total", {})
        meal = entry["meal_type"]
        meals[meal] = _sum_nutrients(meals[meal], nt)
    total = _zero_nutrients()
    for m_nutrients in meals.values():
        total = _sum_nutrients(total, m_nutrients)
    return {
        "date": date,
        "total": total,
        "meals": meals,
        "entry_count": len(entries),
    }


@router.get("/daily/{date}")
def daily_stats(request: Request, date: str):
    diary = DiaryRepository(request.app.state.db)
    entries = diary.list_by_date(user_id=settings.default_user_id, date=date)
    return _compute_daily(entries, date)


@router.get("/range")
def range_stats(request: Request, start: str, end: str):
    diary = DiaryRepository(request.app.state.db)
    # Get all entries in range
    rows = request.app.state.db.execute(
        """SELECT DISTINCT date FROM diary_entries
           WHERE user_id = ? AND date >= ? AND date <= ?
           ORDER BY date""",
        (settings.default_user_id, start, end),
    ).fetchall()
    results = []
    for row in rows:
        date = row["date"]
        entries = diary.list_by_date(user_id=settings.default_user_id, date=date)
        daily = _compute_daily(entries, date)
        daily.pop("meals")
        results.append(daily)
    return results
```

- [ ] **Step 4: Register stats router in app/main.py**

```python
from app.routes.stats import router as stats_router
app.include_router(stats_router)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_routes_stats.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/routes/stats.py tests/test_routes_stats.py app/main.py
git commit -m "feat: add daily and range stats endpoints with per-meal breakdown"
```

---

### Task 8: Weight Repository + Routes

**Files:**
- Create: `app/repositories/weight.py`
- Create: `app/routes/weight.py`
- Create: `tests/test_weight.py`
- Create: `tests/test_routes_weight.py`

- [ ] **Step 1: Write failing weight repository tests**

```python
# tests/test_weight.py
import pytest
from app.repositories.weight import WeightRepository


@pytest.fixture
def repo(db):
    return WeightRepository(db)


def test_create_and_get(repo):
    wid = repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    entry = repo.get(wid)
    assert entry["weight_kg"] == 85.5


def test_list_by_date(repo):
    repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    entries = repo.list_by_date_range(user_id=1, start="2026-05-19", end="2026-05-19")
    assert len(entries) == 1


def test_list_by_range(repo):
    repo.create(user_id=1, date="2026-05-18", weight_kg=86)
    repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    repo.create(user_id=1, date="2026-05-20", weight_kg=85)
    entries = repo.list_by_date_range(user_id=1, start="2026-05-18", end="2026-05-20")
    assert len(entries) == 3


def test_update(repo):
    wid = repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    repo.update(wid, weight_kg=84.0)
    assert repo.get(wid)["weight_kg"] == 84.0


def test_delete(repo):
    wid = repo.create(user_id=1, date="2026-05-19", weight_kg=85.5)
    repo.delete(wid)
    assert repo.get(wid) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_weight.py -v`
Expected: FAIL

- [ ] **Step 3: Implement weight repository**

```python
# app/repositories/weight.py
import sqlite3


class WeightRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, *, user_id: int, date: str, weight_kg: float,
               notes: str | None = None) -> int:
        cur = self.conn.execute(
            """INSERT INTO weight_entries (user_id, date, weight_kg, notes)
               VALUES (?, ?, ?, ?)""",
            (user_id, date, weight_kg, notes),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, entry_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM weight_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_by_date_range(self, *, user_id: int, start: str, end: str) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM weight_entries
               WHERE user_id = ? AND date >= ? AND date <= ?
               ORDER BY date""",
            (user_id, start, end),
        ).fetchall()
        return [dict(r) for r in rows]

    def update(self, entry_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [entry_id]
        self.conn.execute(
            f"UPDATE weight_entries SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete(self, entry_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM weight_entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cur.rowcount > 0
```

- [ ] **Step 4: Run repository tests**

Run: `pytest tests/test_weight.py -v`
Expected: all PASS

- [ ] **Step 5: Write failing weight route tests**

```python
# tests/test_routes_weight.py


def test_create_weight(client):
    r = client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    assert r.status_code == 201
    assert r.json()["weight_kg"] == 85.5


def test_get_weight_by_date(client):
    client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    r = client.get("/weight?date=2026-05-19")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_weight_range(client):
    client.post("/weight", json={"date": "2026-05-18", "weight_kg": 86})
    client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    r = client.get("/weight?start=2026-05-18&end=2026-05-19")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_patch_weight(client):
    r = client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    wid = r.json()["id"]
    r2 = client.patch(f"/weight/{wid}", json={"weight_kg": 84.0})
    assert r2.status_code == 200
    assert r2.json()["weight_kg"] == 84.0


def test_delete_weight(client):
    r = client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    wid = r.json()["id"]
    r2 = client.delete(f"/weight/{wid}")
    assert r2.status_code == 204
```

- [ ] **Step 6: Implement weight routes**

```python
# app/routes/weight.py
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
```

- [ ] **Step 7: Register weight router in app/main.py**

```python
from app.routes.weight import router as weight_router
app.include_router(weight_router)
```

- [ ] **Step 8: Run all weight tests**

Run: `pytest tests/test_weight.py tests/test_routes_weight.py -v`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add app/repositories/weight.py app/routes/weight.py tests/test_weight.py tests/test_routes_weight.py app/main.py
git commit -m "feat: add weight tracking with CRUD and date range queries"
```

---

### Task 9: Recipe Repository + Routes

**Files:**
- Create: `app/repositories/recipes.py`
- Create: `app/services/recipe_nutrition.py`
- Create: `app/routes/recipes.py`
- Create: `tests/test_recipes.py`
- Create: `tests/test_routes_recipes.py`

- [ ] **Step 1: Write failing recipe nutrition service tests**

```python
# tests/test_recipes.py
import pytest
from app.services.recipe_nutrition import compute_recipe_nutrients


def test_recipe_nutrients():
    ingredients = [
        {"grams": 100, "food_snapshot": {"calories_kcal": 350, "protein_g": 12, "carbs_g": 60, "fat_g": 6}},
        {"grams": 200, "food_snapshot": {"calories_kcal": 60, "protein_g": 3, "carbs_g": 5, "fat_g": 3}},
    ]
    total_weight_g = 300
    servings = 2

    per_100, per_serving = compute_recipe_nutrients(ingredients, total_weight_g, servings)

    # Total: oats=350cal*1 + milk=60cal*2 = 470 cal
    # Per 100g: 470/300*100 = 156.67
    assert abs(per_100["calories_kcal"] - 156.67) < 0.1
    # Per serving: 470/2 = 235
    assert abs(per_serving["calories_kcal"] - 235) < 0.1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_recipes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement recipe nutrition service**

```python
# app/services/recipe_nutrition.py
from app.models.food import NutrientsPer100

NUTRIENT_FIELDS = list(NutrientsPer100.model_fields.keys())


def compute_recipe_nutrients(
    ingredients: list[dict], total_weight_g: float, servings: float
) -> tuple[dict, dict]:
    totals = {f: 0.0 for f in NUTRIENT_FIELDS}
    for ing in ingredients:
        snapshot = ing["food_snapshot"]
        grams = ing["grams"]
        for f in NUTRIENT_FIELDS:
            per_100 = snapshot.get(f, 0) or 0
            totals[f] += per_100 * grams / 100

    per_100 = {f: round(totals[f] * 100 / total_weight_g, 2) for f in NUTRIENT_FIELDS}
    per_serving = {f: round(totals[f] / servings, 2) for f in NUTRIENT_FIELDS}
    return per_100, per_serving
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_recipes.py -v`
Expected: PASS

- [ ] **Step 5: Implement recipe repository**

```python
# app/repositories/recipes.py
import json
import sqlite3


class RecipeRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, *, user_id: int, name: str, servings: float,
               total_weight_g: float, ingredients: list[dict],
               nutrients_per_100: dict, nutrients_per_serving: dict) -> int:
        cur = self.conn.execute(
            """INSERT INTO recipes
               (user_id, name, servings, total_weight_g, ingredients,
                nutrients_per_100, nutrients_per_serving)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, name, servings, total_weight_g,
             json.dumps(ingredients), json.dumps(nutrients_per_100),
             json.dumps(nutrients_per_serving)),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, recipe_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["ingredients"] = json.loads(d["ingredients"])
        d["nutrients_per_100"] = json.loads(d["nutrients_per_100"])
        d["nutrients_per_serving"] = json.loads(d["nutrients_per_serving"])
        return d

    def list_all(self, *, user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM recipes WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["ingredients"] = json.loads(d["ingredients"])
            d["nutrients_per_100"] = json.loads(d["nutrients_per_100"])
            d["nutrients_per_serving"] = json.loads(d["nutrients_per_serving"])
            results.append(d)
        return results

    def update(self, recipe_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        for k in ("ingredients", "nutrients_per_100", "nutrients_per_serving"):
            if k in kwargs and isinstance(kwargs[k], (dict, list)):
                kwargs[k] = json.dumps(kwargs[k])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [recipe_id]
        self.conn.execute(
            f"UPDATE recipes SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete(self, recipe_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        self.conn.commit()
        return cur.rowcount > 0
```

- [ ] **Step 6: Write failing recipe route tests**

```python
# tests/test_routes_recipes.py
from app.repositories.foods import FoodRepository


def _seed_foods(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    oats = repo.create(source="custom", name="Oats", calories_kcal=350, protein_g=12, carbs_g=60, fat_g=6)
    milk = repo.create(source="custom", name="Milk", calories_kcal=60, protein_g=3, carbs_g=5, fat_g=3)
    return oats, milk


def test_create_recipe(client, db):
    oats, milk = _seed_foods(db)
    r = client.post("/recipes", json={
        "name": "Oatmeal",
        "servings": 2,
        "total_weight_g": 300,
        "ingredients": [
            {"food_id": oats, "amount": 100, "unit": "g"},
            {"food_id": milk, "amount": 200, "unit": "ml"},
        ],
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Oatmeal"
    assert "calories_kcal" in data["nutrients_per_serving"]


def test_list_recipes(client, db):
    oats, milk = _seed_foods(db)
    client.post("/recipes", json={
        "name": "Oatmeal", "servings": 2, "total_weight_g": 300,
        "ingredients": [{"food_id": oats, "amount": 100, "unit": "g"}],
    })
    r = client.get("/recipes")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_recipe(client, db):
    oats, _ = _seed_foods(db)
    r = client.post("/recipes", json={
        "name": "Oatmeal", "servings": 1, "total_weight_g": 100,
        "ingredients": [{"food_id": oats, "amount": 100, "unit": "g"}],
    })
    rid = r.json()["id"]
    r2 = client.get(f"/recipes/{rid}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "Oatmeal"


def test_delete_recipe(client, db):
    oats, _ = _seed_foods(db)
    r = client.post("/recipes", json={
        "name": "Oatmeal", "servings": 1, "total_weight_g": 100,
        "ingredients": [{"food_id": oats, "amount": 100, "unit": "g"}],
    })
    rid = r.json()["id"]
    r2 = client.delete(f"/recipes/{rid}")
    assert r2.status_code == 204
```

- [ ] **Step 7: Implement recipe routes**

```python
# app/routes/recipes.py
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
    repo = FoodRepository(request.app.state.db)
    repo.ensure_fts()
    return repo


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
```

- [ ] **Step 8: Register recipe router in app/main.py**

```python
from app.routes.recipes import router as recipes_router
app.include_router(recipes_router)
```

- [ ] **Step 9: Run all recipe tests**

Run: `pytest tests/test_recipes.py tests/test_routes_recipes.py -v`
Expected: all PASS

- [ ] **Step 10: Commit**

```bash
git add app/repositories/recipes.py app/services/recipe_nutrition.py app/routes/recipes.py tests/test_recipes.py tests/test_routes_recipes.py app/main.py
git commit -m "feat: add recipe builder with nutrition math and CRUD endpoints"
```

---

### Task 10: Provider Normalizers

**Files:**
- Create: `app/providers/__init__.py`
- Create: `app/providers/base.py`
- Create: `app/providers/food_data_central.py`
- Create: `app/providers/open_food_facts.py`
- Create: `tests/test_providers_usda.py`
- Create: `tests/test_providers_off.py`

- [ ] **Step 1: Write failing USDA normalizer tests**

```python
# tests/test_providers_usda.py
from app.providers.food_data_central import normalize_usda_food


def test_normalize_usda_food():
    raw = {
        "fdcId": 12345,
        "description": "Banana, raw",
        "brandName": None,
        "gtinUpc": "",
        "foodNutrients": [
            {"nutrientId": 1008, "value": 89},   # Energy
            {"nutrientId": 1003, "value": 1.1},   # Protein
            {"nutrientId": 1005, "value": 22.8},  # Carbs
            {"nutrientId": 1004, "value": 0.3},   # Fat
        ],
    }
    food = normalize_usda_food(raw)
    assert food["name"] == "Banana, raw"
    assert food["source"] == "food_data_central"
    assert food["source_code"] == "12345"
    assert food["calories_kcal"] == 89
    assert food["protein_g"] == 1.1


def test_normalize_handles_missing_nutrients():
    raw = {
        "fdcId": 99,
        "description": "Mystery food",
        "foodNutrients": [],
    }
    food = normalize_usda_food(raw)
    assert food["calories_kcal"] == 0
    assert food["protein_g"] == 0
```

- [ ] **Step 2: Write failing OFF normalizer tests**

```python
# tests/test_providers_off.py
from app.providers.open_food_facts import normalize_off_food


def test_normalize_off_food():
    raw = {
        "code": "3017620422003",
        "product_name": "Nutella",
        "brands": "Ferrero",
        "image_url": "https://example.com/nutella.jpg",
        "serving_quantity": "15",
        "serving_size": "15 g",
        "nutriments": {
            "energy-kcal_100g": 539,
            "proteins_100g": 6.3,
            "carbohydrates_100g": 57.5,
            "fat_100g": 30.9,
            "sugars_100g": 56.3,
            "saturated-fat_100g": 10.6,
            "fiber_100g": 3.4,
            "sodium_100g": 0.041,
        },
    }
    food = normalize_off_food(raw)
    assert food["name"] == "Nutella"
    assert food["brand"] == "Ferrero"
    assert food["source"] == "open_food_facts"
    assert food["barcode"] == "3017620422003"
    assert food["calories_kcal"] == 539
    assert food["protein_g"] == 6.3
    assert food["sodium_mg"] == 41  # 0.041g * 1000


def test_normalize_handles_missing_fields():
    raw = {
        "code": "000",
        "product_name": "Blank",
        "nutriments": {},
    }
    food = normalize_off_food(raw)
    assert food["calories_kcal"] == 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_providers_usda.py tests/test_providers_off.py -v`
Expected: FAIL

- [ ] **Step 4: Implement base provider**

```python
# app/providers/base.py
from typing import Protocol


class FoodNormalizer(Protocol):
    def __call__(self, raw: dict) -> dict: ...
```

- [ ] **Step 5: Implement USDA normalizer**

```python
# app/providers/food_data_central.py

# USDA nutrient ID → our field name
NUTRIENT_MAP = {
    1008: "calories_kcal",
    1003: "protein_g",
    1005: "carbs_g",
    1004: "fat_g",
    2000: "sugar_g",
    1258: "saturated_fat_g",
    1079: "fiber_g",
    1093: "sodium_mg",
    1092: "potassium_mg",
    1087: "calcium_mg",
    1089: "iron_mg",
    1090: "magnesium_mg",
    1095: "zinc_mg",
    1091: "phosphorus_mg",
    1106: "vitamin_a_ug",
    1162: "vitamin_c_mg",
    1114: "vitamin_d_ug",
    1175: "vitamin_b6_mg",
    1178: "vitamin_b12_ug",
    1167: "niacin_mg",
}


def normalize_usda_food(raw: dict) -> dict:
    nutrients = {}
    for fn in raw.get("foodNutrients", []):
        nid = fn.get("nutrientId")
        if nid in NUTRIENT_MAP:
            nutrients[NUTRIENT_MAP[nid]] = fn.get("value", 0) or 0

    return {
        "source": "food_data_central",
        "source_code": str(raw.get("fdcId", "")),
        "name": raw.get("description", ""),
        "brand": raw.get("brandName") or None,
        "barcode": raw.get("gtinUpc") or None,
        "image_url": None,
        "serving_quantity": None,
        "serving_unit": None,
        "serving_size_text": None,
        **{k: nutrients.get(k, 0) for k in NUTRIENT_MAP.values()},
    }
```

- [ ] **Step 6: Implement OFF normalizer**

```python
# app/providers/open_food_facts.py

NUTRIMENT_MAP = {
    "energy-kcal_100g": "calories_kcal",
    "proteins_100g": "protein_g",
    "carbohydrates_100g": "carbs_g",
    "fat_100g": "fat_g",
    "sugars_100g": "sugar_g",
    "saturated-fat_100g": "saturated_fat_g",
    "fiber_100g": "fiber_g",
    "sodium_100g": "sodium_mg",
    "potassium_100g": "potassium_mg",
    "calcium_100g": "calcium_mg",
    "iron_100g": "iron_mg",
    "magnesium_100g": "magnesium_mg",
    "zinc_100g": "zinc_mg",
    "phosphorus_100g": "phosphorus_mg",
    "vitamin-a_100g": "vitamin_a_ug",
    "vitamin-c_100g": "vitamin_c_mg",
    "vitamin-d_100g": "vitamin_d_ug",
    "vitamin-b6_100g": "vitamin_b6_mg",
    "vitamin-b12_100g": "vitamin_b12_ug",
    "niacin_100g": "niacin_mg",
}


def _parse_serving_quantity(raw: dict) -> float | None:
    val = raw.get("serving_quantity")
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def normalize_off_food(raw: dict) -> dict:
    nutriments = raw.get("nutriments", {})
    # Keys where OFF stores values in grams but we need milligrams
    G_TO_MG_KEYS = {"sodium_mg", "potassium_mg", "calcium_mg", "iron_mg",
                     "magnesium_mg", "zinc_mg", "phosphorus_mg"}

    nutrients = {}
    for off_key, our_key in NUTRIMENT_MAP.items():
        val = nutriments.get(off_key, 0) or 0
        if our_key in G_TO_MG_KEYS:
            val = val * 1000  # OFF stores these in grams per 100g
        nutrients[our_key] = val

    return {
        "source": "open_food_facts",
        "source_code": raw.get("code", ""),
        "name": raw.get("product_name", ""),
        "brand": raw.get("brands") or None,
        "barcode": raw.get("code") or None,
        "image_url": raw.get("image_url") or None,
        "serving_quantity": _parse_serving_quantity(raw),
        "serving_unit": "g",
        "serving_size_text": raw.get("serving_size") or None,
        **nutrients,
    }
```

- [ ] **Step 7: Create app/providers/__init__.py**

Empty file.

- [ ] **Step 8: Run tests**

Run: `pytest tests/test_providers_usda.py tests/test_providers_off.py -v`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add app/providers/ tests/test_providers_usda.py tests/test_providers_off.py
git commit -m "feat: add USDA and OpenFoodFacts data normalizers"
```

---

### Task 11: Bulk Import Scripts

**Files:**
- Create: `scripts/import_usda.py`
- Create: `scripts/import_off.py`

- [ ] **Step 1: Implement USDA import script**

```python
# scripts/import_usda.py
"""
Bulk import USDA FoodData Central data into the nutrition tracker database.

Usage:
    python -m scripts.import_usda <path_to_usda_json>

Download the "FoodData Central Foundation Foods" or "SR Legacy" JSON from:
    https://fdc.nal.usda.gov/download-datasets
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_connection, init_schema
from app.repositories.foods import FoodRepository
from app.providers.food_data_central import normalize_usda_food


def import_usda(file_path: str, db_path: str | None = None):
    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = FoodRepository(conn)
    repo.ensure_fts()

    with open(file_path) as f:
        data = json.load(f)

    foods = data if isinstance(data, list) else data.get("FoundationFoods", data.get("SRLegacyFoods", []))
    count = 0
    batch_size = 1000
    for raw in foods:
        normalized = normalize_usda_food(raw)
        repo.create_no_commit(**normalized)
        count += 1
        if count % batch_size == 0:
            conn.commit()
            print(f"  Imported {count} foods...")
    conn.commit()

    print(f"Done. Imported {count} USDA foods.")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_usda <path_to_usda_json> [db_path]")
        sys.exit(1)
    import_usda(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
```

- [ ] **Step 2: Implement OFF import script**

```python
# scripts/import_off.py
"""
Bulk import OpenFoodFacts data into the nutrition tracker database.

Usage:
    python -m scripts.import_off <path_to_off_jsonl>

Download the data dump from:
    https://world.openfoodfacts.org/data
    (Use the JSONL export)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_connection, init_schema
from app.repositories.foods import FoodRepository
from app.providers.open_food_facts import normalize_off_food


def import_off(file_path: str, db_path: str | None = None):
    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = FoodRepository(conn)
    repo.ensure_fts()

    count = 0
    skipped = 0
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            name = raw.get("product_name", "").strip()
            if not name:
                skipped += 1
                continue

            normalized = normalize_off_food(raw)
            repo.create_no_commit(**normalized)
            count += 1
            if count % 5000 == 0:
                conn.commit()
                print(f"  Imported {count} foods (skipped {skipped})...")
    conn.commit()

    print(f"Done. Imported {count} OpenFoodFacts foods (skipped {skipped}).")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_off <path_to_off_jsonl> [db_path]")
        sys.exit(1)
    import_off(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
```

- [ ] **Step 3: Commit**

```bash
git add scripts/
git commit -m "feat: add bulk import scripts for USDA and OpenFoodFacts data"
```

---

### Task 12: Full Integration Test + Final Wiring

**Files:**
- Create: `tests/test_integration.py`
- Modify: `app/main.py` (ensure all routers registered)

- [ ] **Step 1: Write integration test covering full flow**

```python
# tests/test_integration.py
from app.repositories.foods import FoodRepository


def _seed(db):
    repo = FoodRepository(db)
    repo.ensure_fts()
    return repo.create(
        source="custom", name="Chicken Breast",
        calories_kcal=165, protein_g=31, carbs_g=0, fat_g=3.6,
        serving_quantity=100, serving_unit="g",
    )


def test_full_flow(client, db):
    # Create food
    fid = _seed(db)

    # Search
    r = client.get("/foods/search?q=chicken")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Log diary entry
    r = client.post("/diary/2026-05-19/entries", json={
        "food_id": fid, "amount": 200, "unit": "g", "meal_type": "lunch"
    })
    assert r.status_code == 201
    entry = r.json()
    assert entry["nutrients_total"]["calories_kcal"] == 330
    assert entry["nutrients_total"]["protein_g"] == 62

    # Check daily stats
    r = client.get("/stats/daily/2026-05-19")
    assert r.status_code == 200
    stats = r.json()
    assert stats["total"]["calories_kcal"] == 330
    assert stats["meals"]["lunch"]["protein_g"] == 62
    assert stats["entry_count"] == 1

    # Log weight
    r = client.post("/weight", json={"date": "2026-05-19", "weight_kg": 85.5})
    assert r.status_code == 201

    # Check weight
    r = client.get("/weight?date=2026-05-19")
    assert r.status_code == 200
    assert r.json()[0]["weight_kg"] == 85.5

    # Health check
    r = client.get("/health")
    assert r.status_code == 200
```

- [ ] **Step 2: Ensure all routers are registered in app/main.py**

Verify `app/main.py` includes all routers:

```python
from app.routes.foods import router as foods_router
from app.routes.diary import router as diary_router
from app.routes.stats import router as stats_router
from app.routes.weight import router as weight_router
from app.routes.recipes import router as recipes_router

app.include_router(foods_router)
app.include_router(diary_router)
app.include_router(stats_router)
app.include_router(weight_router)
app.include_router(recipes_router)
```

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py app/main.py
git commit -m "feat: add integration tests, finalize router wiring"
```

- [ ] **Step 5: Run the server and verify manually**

```bash
cd ~/work/code/nutritiontracker
source .venv/bin/activate
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/health` and `http://localhost:8000/docs` to confirm the API is live and the OpenAPI docs look correct.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
```
