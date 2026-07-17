"""AQUA-SENSE FastAPI application."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routes.auth import router as auth_router
from app.routes.complaints import router as complaints_router
from app.routes.admin_complaints import router as admin_complaints_router
from app.routes.pipelines import router as pipelines_router

app = FastAPI(
    title="AQUA-SENSE API",
    description="Backend API for the AQUA-SENSE citizen water-complaint system and simulated pipeline failure-risk map.",
    version="0.1.0",
)

# ---- CORS ----
origins = [
    origin.strip()
    for origin in settings.FRONTEND_ORIGIN.split(",")
    if origin.strip()
]
for dev_origin in [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]:
    if dev_origin not in origins:
        origins.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(admin_complaints_router)
app.include_router(pipelines_router)

# ---- Static Files (uploads) ----
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ---- Health check ----
@app.get("/health", tags=["Health"])
def health_check() -> dict:
    return {"status": "ok"}
