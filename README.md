# Nutrition Tracker

FastAPI nutrition tracking API for agent-driven food logging, daily stats, recipes, body weight, step imports, and lightweight journal notes.

The project is designed as a deterministic system of record. Agents can handle messy inputs such as photos, meal descriptions, menu screenshots, or conversational coaching, while this API handles normalized storage, nutrient math, and reporting.

## Features

- Food search over preloaded USDA FoodData Central and Open Food Facts data.
- Barcode lookup for packaged foods.
- Custom food CRUD.
- Diary entries with food snapshots so historical logs do not change when source food data changes.
- Daily and range nutrition stats with per-meal breakdowns.
- Recipe builder with unit conversion and computed nutrition per 100g and per serving.
- Weight tracking.
- Hourly Apple Shortcuts step import using cumulative day-to-date steps.
- Lightweight journal entries with optional mood, stress, sleep-quality, and tags.
- Optional Bearer-token auth for private deployment.
- Docker, docker-compose, Woodpecker CI, and Kamal deployment support.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

The API is available at:

```text
http://127.0.0.1:8000
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

Interactive docs:

```text
http://127.0.0.1:8000/docs
```

## Configuration

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

Environment variables:

```text
NT_DB_PATH=data/nutrition.db
NT_BEARER_TOKEN=replace-with-a-long-random-token
CLOUDFLARE_TUNNEL_TOKEN=your-cloudflare-tunnel-token
```

`NT_BEARER_TOKEN` is optional for local development. If set, all endpoints require:

```text
Authorization: Bearer <token>
```

Generate a token:

```bash
openssl rand -hex 32
```

## Docker

```bash
docker compose up -d --build
```

The API listens on local port `8000`:

```text
http://127.0.0.1:8000
```

The compose file also includes a `cloudflared` service for a Cloudflare Tunnel when `CLOUDFLARE_TUNNEL_TOKEN` is configured.

## Import Food Data

The API uses local SQLite data. Import source datasets before relying on food search.

USDA FoodData Central JSON:

```bash
python -m scripts.import_usda /path/to/usda.json
```

Open Food Facts JSONL:

```bash
python -m scripts.import_off /path/to/openfoodfacts-products.jsonl
```

FoodData Central downloads:

```text
https://fdc.nal.usda.gov/download-datasets
```

Open Food Facts data:

```text
https://world.openfoodfacts.org/data
```

## API Overview

Foods:

```text
GET    /foods/search?q={query}&source={source}&limit={n}&offset={n}
GET    /foods/barcode/{barcode}
GET    /foods/{id}
POST   /foods
PATCH  /foods/{id}
DELETE /foods/{id}
```

Diary:

```text
GET    /diary/{date}
POST   /diary/{date}/entries
PATCH  /diary/entries/{entry_id}
DELETE /diary/entries/{entry_id}
```

Stats:

```text
GET /stats/daily/{date}
GET /stats/range?start={date}&end={date}
```

Recipes:

```text
POST   /recipes
GET    /recipes?limit={n}&offset={n}
GET    /recipes/{recipe_id}
PATCH  /recipes/{recipe_id}
DELETE /recipes/{recipe_id}
```

Weight:

```text
POST   /weight
GET    /weight?date={date}
GET    /weight?start={date}&end={date}
PATCH  /weight/{id}
DELETE /weight/{id}
```

Activity:

```text
POST /imports/activity/steps
GET  /activity/daily/{date}
GET  /activity/range?start={date}&end={date}
```

Journal:

```text
POST   /journal
GET    /journal/{date}
GET    /journal?start={date}&end={date}
PATCH  /journal/{id}
DELETE /journal/{id}
```

## Apple Shortcuts Step Import

Use an hourly iOS Shortcuts automation to send cumulative day-to-date steps.

Endpoint:

```text
POST /imports/activity/steps
```

Payload:

```json
{
  "source": "apple_shortcuts",
  "observed_at": "2026-05-19T14:00:00-07:00",
  "period_start": "2026-05-19T00:00:00-07:00",
  "period_end": "2026-05-19T14:00:00-07:00",
  "steps_total_today": 5234,
  "timezone": "America/Los_Angeles"
}
```

Important: send the cumulative current total for the day, not hourly deltas. The API stores every observation and updates the daily total idempotently.

## Journal Example

```json
{
  "date": "2026-05-19",
  "body": "Good food day. Anxiety spiked in the afternoon, but walking helped.",
  "tags": ["recovery", "walk"],
  "mood_score": 6,
  "stress_score": 7,
  "sleep_quality": 5
}
```

## Tests And Lint

```bash
pytest
ruff check app/ tests/ scripts/
```

## Deployment Notes

Woodpecker CI runs lint, secret scanning, tests, and deployment on pushes to `main`.

Kamal configuration lives in `.kamal/`.

Cloudflare Tunnel can be run through Docker Compose or as a Kamal accessory. Keep the API protected with `NT_BEARER_TOKEN` when exposed outside localhost.

## License

The application code is licensed under the MIT License. See `LICENSE`.

Dataset licensing is separate:

- USDA FoodData Central data is public domain.
- Open Food Facts database content is available under the Open Database License (ODbL). If distributing imported Open Food Facts data or a derived database, preserve required attribution and ODbL obligations.

