"""InsightFlow API — FastAPI application entrypoint."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from .database import init_db  # noqa: E402
from .routers import adaption, analytics, demo, feedback, issues, reports  # noqa: E402

app = FastAPI(
    title="InsightFlow API",
    description="Intelligent Customer Feedback & Decision Platform — with Adaption at the data layer.",
    version="0.1.0",
)

origins = os.getenv("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if origins.strip() == "*" else [o.strip() for o in origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feedback.router)
app.include_router(analytics.router)
app.include_router(adaption.router)
app.include_router(issues.router)
app.include_router(reports.router)
app.include_router(demo.router)


@app.on_event("startup")
def _startup():
    init_db()
    from .seed import seed_if_empty

    seed_if_empty()


@app.get("/api/health")
def health():
    from .adaption_service import refinery_status

    return {"ok": True, "refinery": refinery_status()}
