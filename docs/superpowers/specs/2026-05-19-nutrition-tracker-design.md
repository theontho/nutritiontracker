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
| nutrients_per_100 | FK | Link to NutrientsPer100 |

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

### RecipeIngredient

| Field | Type | Notes |
|---|---|---|
| food_snapshot | JSON | Food data at time of creation |
| amount | float | Quantity |
| unit | str | Unit of measurement |
| grams | float | Converted weight in grams |

### Recipe Computation

```
for each ingredient:
  grams = convert_to_grams(amount, unit, serving_quantity_if_needed)
  nutrient_total += food.nutrients_per_100 * grams / 100

recipe_nutrients_per_100 = nutrient_total * 100 / total_weight_g
recipe_nutrients_per_serving = nutrient_total / servings
```

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

### Endpoints

```
GET /foods/search?q=banana&source=all
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

### Stats

```
GET /stats/daily/{date}
```

Returns rolled-up nutrient totals for all diary entries on a given date.

### Recipes

```
POST   /recipes
GET    /recipes
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
    routes/
      foods.py
      diary.py
      recipes.py
      stats.py
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

## Deferred

- User profile / nutrition targets (BMR, TDEE, macro goals)
- CLI interface
- Recovery-plan integration (meals, hydration, protein targets, caffeine/alcohol/sleep notes)

## Product Direction

Treat nutrition tracking as a practical logging tool. The API should make logging frictionless and surface useful daily patterns. Designed to be driven by AI agents.
