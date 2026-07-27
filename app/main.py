from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from setproctitle import setproctitle

from app.auth import require_auth
from app.config import settings
from app.database import get_connection, init_schema
from app.repositories.foods import FoodRepository
from app.routes.activity import router as activity_router
from app.routes.diary import router as diary_router
from app.routes.foods import router as foods_router
from app.routes.imports import router as imports_router
from app.routes.journal import router as journal_router
from app.routes.kitchen import router as kitchen_router
from app.routes.recipes import router as recipes_router
from app.routes.stats import router as stats_router
from app.routes.weight import router as weight_router

FAVICON_PATH = Path(__file__).parent / "static" / "favicon.svg"


@asynccontextmanager
async def lifespan(app: FastAPI):
    setproctitle("Nutrition Tracker Service")
    conn = get_connection()
    init_schema(conn)
    FoodRepository(conn).ensure_fts()
    app.state.db = conn
    yield
    conn.close()


app = FastAPI(
    title="Nutrition Tracker",
    version=settings.api_version,
    description="""Open-source REST API for nutrition tracking.

Designed to be called by AI agents to log and query nutrition data.

**Data sources:** Pre-loaded USDA FoodData Central and OpenFoodFacts databases.

**Key endpoints:**
- `/foods/search` — search 500k+ foods by name with prefix matching
- `/foods/barcode/{barcode}` — look up by EAN/UPC barcode
- `/diary/{date}/entries` — log what you ate
- `/stats/daily/{date}` — get today's nutrition totals
- `/weight` — track body weight
- `/recipes` — build recipes with auto-computed nutrition math

**Schema:** Full OpenAPI 3.0 schema at `/openapi.json`.
""",
    lifespan=lifespan,
)

_auth = [Depends(require_auth)]
app.include_router(foods_router, dependencies=_auth)
app.include_router(diary_router, dependencies=_auth)
app.include_router(stats_router, dependencies=_auth)
app.include_router(journal_router, dependencies=_auth)
app.include_router(weight_router, dependencies=_auth)
app.include_router(recipes_router, dependencies=_auth)
app.include_router(kitchen_router, dependencies=_auth)
app.include_router(activity_router, dependencies=_auth)
app.include_router(imports_router, dependencies=_auth)


@app.api_route(
    "/", methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False
)
def root():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nutrition Tracker Service</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
      background: #07140d;
      color: #ecfdf5;
    }
    * { box-sizing: border-box; }
    body {
      min-height: 100vh;
      margin: 0;
      display: grid;
      place-items: center;
      padding: 24px;
      background:
        radial-gradient(circle at top left, #166534 0, transparent 42%),
        radial-gradient(circle at bottom right, #14532d 0, transparent 36%),
        #07140d;
    }
    main {
      width: min(100%, 680px);
      padding: clamp(28px, 6vw, 52px);
      border: 1px solid #ffffff1f;
      border-radius: 24px;
      background: #0b1f14e8;
      box-shadow: 0 24px 80px #0008;
      backdrop-filter: blur(12px);
    }
    header { display: flex; align-items: center; gap: 18px; }
    header img { width: 64px; height: 64px; }
    h1 { margin: 0; font-size: clamp(1.8rem, 5vw, 2.7rem); line-height: 1.05; }
    .eyebrow {
      margin: 0 0 6px;
      color: #86efac;
      font-size: .75rem;
      font-weight: 700;
      letter-spacing: .14em;
      text-transform: uppercase;
    }
    .summary { margin: 24px 0; color: #bbd6c5; font-size: 1.05rem; line-height: 1.65; }
    .ai-note {
      margin: 0 0 26px;
      padding: 16px 18px;
      border-left: 3px solid #4ade80;
      border-radius: 0 12px 12px 0;
      background: #14532d66;
      color: #dcfce7;
      line-height: 1.5;
    }
    nav { display: flex; flex-wrap: wrap; gap: 12px; }
    a {
      color: #ecfdf5;
      font-weight: 700;
      text-decoration: none;
    }
    nav a {
      padding: 11px 16px;
      border: 1px solid #ffffff24;
      border-radius: 10px;
      background: #ffffff0d;
    }
    nav a:first-child { border-color: #4ade80; background: #166534; }
    nav a:hover { border-color: #86efac; background: #166534; }
  </style>
</head>
<body>
  <main>
    <header>
      <img src="/favicon.svg" alt="">
      <div>
        <p class="eyebrow">Local API</p>
        <h1>Nutrition Tracker Service</h1>
      </div>
    </header>
    <p class="summary">
      A personal API for searching foods and tracking meals, nutrition,
      activity, weight, recipes, and kitchen inventory.
    </p>
    <p class="ai-note">
      <strong>Designed for AI clients.</strong> Give your assistant the
      OpenAPI schema so it can search foods, log entries, and answer questions
      using your nutrition data.
    </p>
    <nav>
      <a href="/docs">Explore API</a>
      <a href="/health">Service health</a>
      <a href="https://github.com/gregmushen/nutritiontracker"
         target="_blank" rel="noreferrer">GitHub ↗</a>
    </nav>
  </main>
</body>
</html>"""


@app.api_route("/favicon.svg", methods=["GET", "HEAD"], include_in_schema=False)
def favicon():
    return FileResponse(FAVICON_PATH, media_type="image/svg+xml")


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.api_version}
