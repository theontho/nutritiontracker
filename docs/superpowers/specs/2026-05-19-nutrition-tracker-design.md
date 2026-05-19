# Nutrition Tracker API — Design Spec

## Overview

An open-source REST API for nutrition tracking, built with FastAPI and SQLite. Uses pre-loaded USDA FoodData Central and OpenFoodFacts databases for food lookup. Designed to be called by AI agents to log and query nutrition data.

## Core Data Model

### Food

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| source | enum | custom, open_food_facts, food_data_central, recipe |
| source_code | str | External ID from source |
| name | str | Food name |
| brand | str | Nullable, for packaged foods |
| barcode | str | Nullable, EAN/UPC |
| image_url | str | Nullable |
| serving_quantity | float | e.g. 1 |
| serving_unit | str | e.g. "cup", "slice" |
| serving_size_text | str | Human-readable serving description |
| base_quantity | float | Always 100 |
| base_unit | str | g or ml |
| density_g_per_ml | float | Nullable, for volume-to-weight conversion |
| nutrients_per_100 | FK | Link to NutrientsPer100 |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

### NutrientsPer100

| Field | Type |
|---|---|
| calories_kcal | float |
| protein_g | float |
| carbs_g | float |
| fat_g | float |
| sugar_g | float |
| saturated_fat_g | float |
| fiber_g | float |
| sodium_mg | float |
| potassium_mg | float |
| calcium_mg | float |
| iron_mg | float |
| magnesium_mg | float |
| zinc_mg | float |
| phosphorus_mg | float |
| vitamin_a_ug | float |
| vitamin_c_mg | float |
| vitamin_d_ug | float |
| vitamin_b6_mg | float |
| vitamin_b12_ug | float |
| niacin_mg | float |

### DiaryEntry

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| user_id | int | User reference |
| date | date | Entry date |
| meal_type | enum | breakfast, lunch, dinner, snack |
| food_id | int | FK to Food |
| food_snapshot | JSON | Full food data at time of logging |
| amount | float | How much was consumed |
| unit | str | Unit of measurement |
| grams | float | Converted weight in grams |
| nutrients_total | JSON | Computed nutrients for this entry |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

The food_snapshot captures the full food record at time of logging. Historical diary entries do not change when an external source updates a label.

### Recipe

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| user_id | int | User reference |
| name | str | Recipe name |
| servings | float | Number of servings |
| total_weight_g | float | Total weight |
| ingredients | list | List of RecipeIngredient |
| nutrients_per_100 | JSON | Computed per 100g |
| nutrients_per_serving | JSON | Computed per serving |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

### RecipeIngredient

| Field | Type | Notes |
|---|---|---|
| food_id | int | FK to source Food |
| food_snapshot | JSON | Food data at time of creation |
| amount | float | Quantity |
| unit | str | Unit of measurement |
| grams | float | Converted weight in grams |

### WeightEntry

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| user_id | int | User reference |
| date | date | Entry date |
| weight_kg | float | Body weight in kg |
| notes | str | Nullable |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

### Recipe Computation

```
for each ingredient:
  grams = convert_to_grams(amount, unit, serving_quantity_if_needed)
  nutrient_total += food.nutrients_per_100 * grams / 100

recipe_nutrients_per_100 = nutrient_total * 100 / total_weight_g
recipe_nutrients_per_serving = nutrient_total / servings
```

## Unit Conversion

Supported units for diary entries and recipe ingredients:

- **Weight:** g, kg, oz, lb
- **Volume:** ml, l, cup, tbsp, tsp, fl_oz
- **Portions:** serving, piece, slice

Weight units convert directly. Volume-to-weight conversion uses a density lookup per food (stored as an optional field or derived from serving data). If density is unavailable, fall back to water density (1 g/ml) and flag the conversion as approximate. "Serving" uses the food's `serving_quantity` and `serving_unit` to resolve to grams.

## External Data Sources

### Pre-loaded Databases

Both USDA FoodData Central and OpenFoodFacts data are bulk-imported into SQLite at setup time via import scripts. No live API calls are made at query time.

### Provider Normalization

Each source has a normalization module that transforms raw bulk data into the internal Food model during import. External data shapes do not leak past the provider layer.

- `providers/open_food_facts.py` — normalizes OFF CSV/JSONL dump
- `providers/food_data_central.py` — normalizes USDA CSV/JSON

## Food Search

SQLite FTS5 full-text search index on food name and brand fields.

- Prefix matching ("chick" finds "chicken breast")
- Ranked results by relevance
- Trigram similarity for fuzzy/close matches (typos, alternate spellings)
- Filterable by source
- Deduplication: when the same food exists in both USDA and OpenFoodFacts (matched by barcode, source_code, or normalized name), search results are deduplicated. Prefer the record with more complete nutrient data; surface source as metadata so the caller knows the origin.

### Endpoints

```
GET /foods/search?q=banana&source=all&limit=20&offset=0
GET /foods/search?q=banana&source=open_food_facts
GET /foods/search?q=banana&source=food_data_central
GET /foods/barcode/{barcode}
GET /foods/{id}
```

## API Endpoints

### Foods

```
GET  /foods/search?q={query}&source={source}&limit={n}
GET  /foods/barcode/{barcode}
GET  /foods/{id}
POST /foods                    # custom food
PATCH /foods/{id}              # update custom food
DELETE /foods/{id}             # delete custom food
```

### Diary

```
GET    /diary/{date}
POST   /diary/{date}/entries
PATCH  /diary/entries/{entry_id}
DELETE /diary/entries/{entry_id}
```

### Weight

```
POST   /weight
GET    /weight?date={date}
GET    /weight?start={date}&end={date}
PATCH  /weight/{id}
DELETE /weight/{id}
```

### Stats

```
GET /stats/daily/{date}
GET /stats/range?start={date}&end={date}
```

`/stats/daily/{date}` response shape:

```json
{
  "date": "2026-05-19",
  "total": { "calories_kcal": 2100, "protein_g": 150, ... },
  "meals": {
    "breakfast": { "calories_kcal": 500, "protein_g": 30, ... },
    "lunch": { "calories_kcal": 700, "protein_g": 45, ... },
    "dinner": { "calories_kcal": 800, "protein_g": 60, ... },
    "snack": { "calories_kcal": 100, "protein_g": 15, ... }
  },
  "entry_count": 8
}
```

Each nutrient object contains all 20 NutrientsPer100 fields. Meals with no entries are included with zeroed values.

`/stats/range` returns an array of daily totals (same shape as above, without per-meal breakdown) for trend analysis by AI agents.

### Recipes

```
POST   /recipes
GET    /recipes?limit={n}&offset={n}
GET    /recipes/{recipe_id}
PATCH  /recipes/{recipe_id}
DELETE /recipes/{recipe_id}
```

## Project Structure

```
nutritiontracker/
  app/
    main.py
    config.py
    models/
      food.py
      nutrients.py
      diary.py
      recipe.py
      weight.py
    providers/
      open_food_facts.py
      food_data_central.py
    services/
      food_search.py
      diary.py
      recipe_nutrition.py
    repositories/
      foods.py
      diary.py
      recipes.py
      weight.py
    routes/
      foods.py
      diary.py
      recipes.py
      stats.py
      weight.py
  scripts/
    import_usda.py
    import_off.py
  data/
  tests/
```

## Tech Stack

- **Framework:** FastAPI
- **Database:** SQLite
- **Search:** SQLite FTS5 + trigram similarity
- **Food Data:** Pre-loaded USDA FoodData Central + OpenFoodFacts

## MVP Build Order

1. Normalized food and nutrient models
2. Bulk import scripts (USDA + OpenFoodFacts)
3. FTS5 search with fuzzy matching
4. Diary CRUD with daily totals
5. Recipe math
6. Custom foods

## Design Decisions

- **No caching layer.** The reference architecture includes a remote search cache with TTLs. Since all food data is pre-loaded locally, there are no remote API calls to cache. SQLite queries against FTS5 indexes are fast enough without an additional cache layer.
- **user_id handling in MVP.** User auth is deferred. In MVP, `user_id` defaults to 1 (single-user mode). Diary and recipe endpoints accept an optional `user_id` parameter to keep the schema ready for multi-user, but no auth middleware is applied.
- **Health check.** `GET /health` returns API version and database status.

## Deferred

- User profile / nutrition targets (BMR, TDEE, macro goals)
- User authentication and multi-user support
- CLI interface
- Recovery-plan integration (meals, hydration, protein targets, caffeine/alcohol/sleep notes)

## Product Direction

Treat nutrition tracking as a practical logging tool. The API should make logging frictionless and surface useful daily patterns. Designed to be driven by AI agents.
