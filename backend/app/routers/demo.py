"""Import the bundled multilingual sample feed (demo: ingestion + language normalization)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from .. import seed
from ..database import get_session

router = APIRouter(prefix="/api/demo", tags=["demo"])

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "sample_data" / "feedback.csv"


@router.post("/import-sample")
def import_sample(session: Session = Depends(get_session)):
    """
    One-click import of the multilingual, timestamped sample feed.
    Used in the demo to show: (a) crowded-out news feeds arriving later,
    (b) language normalization, (c) a populated trend chart.
    """
    if not SAMPLE.exists():
        raise HTTPException(404, "sample_data/feedback.csv not found")
    stats = seed.load_csv(SAMPLE)
    return {**stats, "file": SAMPLE.name}


@router.get("/dataset-info")
def dataset_info():
    return {
        "official_dataset_present": seed.OFFICIAL_CSV.exists(),
        "official_dataset_path": str(seed.OFFICIAL_CSV),
        "sample_feed_present": SAMPLE.exists(),
    }
