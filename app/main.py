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
