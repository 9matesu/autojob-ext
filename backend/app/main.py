"""resuMe Backend Entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import OUTPUT_DIR
from . import db
from .api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(
    title="resuMe Engine",
    description="Background Resume Adaptation & LaTeX Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Mount outputs for previewing PDFs
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
