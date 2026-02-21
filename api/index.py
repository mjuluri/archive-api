from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from archive_api.config import settings
from archive_api.database import engine, get_db
from archive_api.routers import exoplanets, export, statistics

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(exoplanets.router)
app.include_router(statistics.router)
app.include_router(export.router)

_db_ready = False


@app.middleware("http")
async def init_db(request: Request, call_next):
    global _db_ready
    if not _db_ready:
        from archive_api.models import Base
        from archive_api.seed import seed_database

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await seed_database()
        _db_ready = True
    return await call_next(request)


@app.get("/health", tags=["system"])
async def health():
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": settings.app_version,
    }


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "endpoints": ["/api/v1/exoplanets", "/api/v1/statistics", "/api/v1/export", "/health"],
    }


@app.exception_handler(Exception)
async def unhandled_exception(_request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc)},
    )
