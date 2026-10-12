"""Adaption (Feedback Refinery) endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import adaption_service, models, schemas
from ..database import get_session

router = APIRouter(prefix="/api/adaption", tags=["adaption"])


@router.get("/status")
def status():
    return adaption_service.refinery_status()


@router.post("/runs", status_code=202)
def start_run(payload: schemas.RunRequest, session: Session = Depends(get_session)):
    if payload.mode not in ("auto", "live", "demo"):
        raise HTTPException(400, "mode must be auto | live | demo")
    run = adaption_service.launch_run(
        session, payload.mode, payload.max_rows, payload.recipes, payload.blueprint
    )
    return {"run_id": run.id, "mode": run.mode, "status": run.status}


@router.get("/runs")
def list_runs(session: Session = Depends(get_session)):
    runs = session.exec(
        select(models.AdaptionRun).order_by(models.AdaptionRun.id.desc())  # type: ignore[attr-defined]
    ).all()
    return {"runs": [r.model_dump() for r in runs]}


@router.get("/runs/{run_id}")
def get_run(run_id: int, session: Session = Depends(get_session)):
    run = session.get(models.AdaptionRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run.model_dump()
