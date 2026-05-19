#!/bin/sh
set -e

DB_PATH="${NT_DB_PATH:-data/nutrition.db}"
mkdir -p "$(dirname "$DB_PATH")"

if [ ! -f "$DB_PATH" ] || [ "${NT_FORCE_SEED:-0}" = "1" ]; then
    echo "Seeding database..."

    if [ -n "$USDA_DATA_PATH" ] && [ -f "$USDA_DATA_PATH" ]; then
        echo "Importing USDA FoodData Central from $USDA_DATA_PATH..."
        python -m scripts.import_usda "$USDA_DATA_PATH"
    else
        echo "USDA_DATA_PATH not set or file not found, skipping USDA import."
    fi

    if [ -n "$OFF_DATA_PATH" ] && [ -f "$OFF_DATA_PATH" ]; then
        echo "Importing OpenFoodFacts from $OFF_DATA_PATH..."
        python -m scripts.import_off "$OFF_DATA_PATH"
    else
        echo "OFF_DATA_PATH not set or file not found, skipping OFF import."
    fi
else
    echo "Database already exists at $DB_PATH, skipping seed."
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
