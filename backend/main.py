import logging
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.config import API_HOST, API_PORT, CORS_ORIGINS, CORS_ORIGIN_REGEX
from backend.database import init_db
from backend.routers import auth_router, records_router, reports_router, public_router

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
FRONTEND_INDEX = FRONTEND_DIR / "index.html"
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

limiter = Limiter(key_func=get_remote_address, default_limits=["30/second"])

app = FastAPI(title="Real Estate CRM API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(records_router.router)
app.include_router(reports_router.router)
app.include_router(public_router.router)

logger = logging.getLogger("realestate_crm")


@app.on_event("startup")
def on_startup():
    init_db()
    from backend.database import SessionLocal
    from backend.models import User
    from backend.auth import hash_password
    from backend.config import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL
    from backend.backup import start_daily_backup_scheduler
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if not existing:
            db.add(User(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                full_name="System Administrator",
                email=ADMIN_EMAIL,
                role="Super Admin",
                is_active=True,
            ))
            db.commit()
    finally:
        db.close()
    start_daily_backup_scheduler()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


# Serve frontend SPA — catch-all for non-API routes
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    file_path = FRONTEND_DIR / full_path
    if file_path.is_file():
        return FileResponse(str(file_path), headers=NO_CACHE_HEADERS)
    if FRONTEND_INDEX.is_file():
        return FileResponse(str(FRONTEND_INDEX), headers=NO_CACHE_HEADERS)
    return JSONResponse(status_code=404, content={"detail": "Not found"})
