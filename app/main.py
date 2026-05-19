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

from app.routes.foods import router as foods_router
app.include_router(foods_router)

from app.routes.diary import router as diary_router
app.include_router(diary_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.api_version}
