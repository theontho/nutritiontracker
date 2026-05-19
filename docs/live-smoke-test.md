# Nutrition Tracker — Live Smoke Test Plan

**Base URL:** `https://n.paracosmlab.com`  
**Auth:** `Authorization: Bearer <NT_BEARER_TOKEN>`

---

## 1. Health (unauthenticated)

Verifies the app is running and `/health` is publicly accessible.

```bash
curl -s https://n.paracosmlab.com/health
```

**Expected:** `{"status":"ok","version":"0.1.0"}`

---

## 2. Auth enforcement

Verifies protected endpoints reject unauthenticated requests.

```bash
curl -s -o /dev/null -w "%{http_code}" https://n.paracosmlab.com/foods/search?q=chicken
```

**Expected:** `401`

---

## 3. Foods — create a custom food

Diary, recipes, and stats all require `food_id`. Since USDA/OpenFoodFacts data isn't seeded yet, we create a custom food first.

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Apple",
    "base_quantity": 100,
    "base_unit": "g",
    "nutrients": {
      "calories_kcal": 52,
      "protein_g": 0.3,
      "carbs_g": 14,
      "fat_g": 0.2
    }
  }' \
  "https://n.paracosmlab.com/foods"
```

**Expected:** Returns `FoodOut` with an `id` field. Capture this ID for subsequent tests.

---

## 4. Foods search

Verifies full-text search finds the food we just created.

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://n.paracosmlab.com/foods/search?q=apple&limit=5"
```

**Expected:** JSON array containing the Test Apple entry.

---

## 5. Diary — log entry and retrieve

Uses the `food_id` from step 3. `amount` and `unit` refer to the quantity eaten.

```bash
# POST entry
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"food_id": <ID>, "amount": 150, "unit": "g", "meal_type": "snack"}' \
  "https://n.paracosmlab.com/diary/2026-05-19/entries"

# GET entries for the day
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://n.paracosmlab.com/diary/2026-05-19"
```

**Expected:** POST returns `DiaryEntry` with `id`. GET returns array containing it.

---

## 6. Stats — daily totals

Verifies nutrition rollup for the diary entries logged above.

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://n.paracosmlab.com/stats/daily/2026-05-19"
```

**Expected:** `DailyStats` with non-zero `calories`, `protein_g`, `carbs_g`, `fat_g`.

---

## 7. Weight — log and retrieve

```bash
# POST
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-05-19", "weight_kg": 80.5, "notes": "morning"}' \
  "https://n.paracosmlab.com/weight"

# GET range
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://n.paracosmlab.com/weight?start=2026-05-19&end=2026-05-19"
```

**Expected:** POST returns `WeightEntry` with `id`. GET returns array containing it.

---

## 8. Journal — create with scores and retrieve

```bash
# POST
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-05-19",
    "body": "Felt good today, ate well.",
    "mood_score": 8,
    "stress_score": 3,
    "sleep_quality": 7,
    "tags": ["test"]
  }' \
  "https://n.paracosmlab.com/journal"

# GET by date
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://n.paracosmlab.com/journal/2026-05-19"
```

**Expected:** POST returns `JournalEntry` with `id` and all scores. GET returns same entry.

---

## 9. Steps / Activity — import and retrieve

Verifies step count sync and cumulative-day logic. A second import with a lower count should set `anomaly_flag: true`.

```bash
# First import
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "observed_at": "2026-05-19T12:00:00",
    "period_start": "2026-05-19T00:00:00",
    "period_end": "2026-05-19T12:00:00",
    "steps_total_today": 6500,
    "timezone": "America/Los_Angeles"
  }' \
  "https://n.paracosmlab.com/imports/activity/steps"

# Second import — lower count should trigger anomaly
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "observed_at": "2026-05-19T13:00:00",
    "period_start": "2026-05-19T00:00:00",
    "period_end": "2026-05-19T13:00:00",
    "steps_total_today": 3000,
    "timezone": "America/Los_Angeles"
  }' \
  "https://n.paracosmlab.com/imports/activity/steps"

# GET today's summary
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://n.paracosmlab.com/activity/daily/2026-05-19"
```

**Expected:**
- Both POSTs return `{"status": "ok"}`.
- GET returns `steps: 6500` (anomaly preserved original count) and `anomaly_flag: true`.

---

## 10. Recipes — create with ingredients

Uses `food_id` from step 3. Verifies nutrition math.

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Snack",
    "servings": 1,
    "total_weight_g": 200,
    "ingredients": [
      {"food_id": <ID>, "amount": 200, "unit": "g"}
    ]
  }' \
  "https://n.paracosmlab.com/recipes"
```

**Expected:** Returns `Recipe` with computed `total_calories: 104` (52 kcal/100g × 200g).

---

## 11. OpenAPI schema accessible

Verifies the schema endpoint is live (useful for AI agents).

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  https://n.paracosmlab.com/openapi.json
```

**Expected:** `200`
