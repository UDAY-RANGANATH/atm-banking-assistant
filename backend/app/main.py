from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes
from app.api import scanner_routes
from app.api import form_routes
from app.api import pdf_routes
from app.api import ai_routes
from app.core.config import get_settings
from app.db.database import init_db

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

_allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api")
app.include_router(scanner_routes.router, prefix="/api")
app.include_router(form_routes.router, prefix="/api")
app.include_router(pdf_routes.router, prefix="/api")
app.include_router(ai_routes.router, prefix="/api")


# ---------------------------------------------------------------------------
# Optional single-origin deployment (Phase 8)
# ---------------------------------------------------------------------------
# SERVE_FRONTEND_DIST=1 mounts the built kiosk UI (frontend/dist) on this same
# origin so production deployments need no CORS/proxy setup. This is static
# file serving only - all banking operations still run in the deterministic
# backend services below.
def _mount_frontend() -> None:
    if not settings.SERVE_FRONTEND_DIST:
        return
    from pathlib import Path

    dist = Path(settings.FRONTEND_DIST_PATH)
    if not dist.is_absolute():
        dist = (Path(__file__).resolve().parent.parent / dist).resolve()
    if not (dist / "index.html").exists():
        return
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(dist), html=True), name="kiosk")


_mount_frontend()


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "AI Banking Assistant API", "version": settings.APP_VERSION}
