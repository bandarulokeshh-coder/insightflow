"""Feedback CRUD, search/filter/sort, and CSV import."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, func, select

from .. import analysis, models, schemas
from ..official import classify_official
from ..database import get_session

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

TEXT_HEADERS = ["text", "feedback", "comment", "review", "message", "content", "body"]
RATING_HEADERS = ["rating", "score", "stars", "star"]
CHANNEL_HEADERS = ["channel", "source", "type", "medium"]
AUTHOR_HEADERS = ["author", "name", "customer", "user", "reviewer"]
PRODUCT_HEADERS = ["product", "sku", "item", "category"]
DATE_HEADERS = ["date", "created_at", "timestamp", "time", "created"]
CATEGORY_HEADERS = ["category", "label", "class", "type_of_issue"]


def _pick(row: dict, candidates: list[str]) -> Optional[str]:
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for c in candidates:
        if c in lowered and str(lowered[c]).strip():
            return str(lowered[c]).strip()
    return None


def _to_out(fb: models.Feedback) -> schemas.FeedbackOut:
    return schemas.FeedbackOut(
        id=fb.id, text=fb.text, adapted_text=fb.adapted_text,
        display_text=fb.adapted_text or fb.text,
        author=fb.author, channel=fb.channel, product=fb.product,
        rating=fb.rating, source_date=fb.source_date, created_at=fb.created_at,
        sentiment=fb.sentiment, sentiment_score=fb.sentiment_score,
        topic=fb.topic, complaint=fb.complaint, urgency=fb.urgency,
        detected_language=fb.detected_language,
        official_category=fb.official_category, predicted_category=fb.predicted_category,
        adaption_action=fb.adaption_action,
        reasoning_trace=fb.reasoning_trace,
        is_duplicate=fb.is_duplicate, analyzed=fb.analyzed,
    )


@router.get("", response_model=schemas.Page)
def list_feedback(
    q: Optional[str] = None,
    sentiment: Optional[str] = None,
    topic: Optional[str] = None,
    channel: Optional[str] = None,
    product: Optional[str] = None,
    include_duplicates: bool = False,
    sort: str = Query("newest", pattern="^(newest|oldest|most_negative|most_positive)$"),
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
):
    stmt = select(models.Feedback)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            models.Feedback.text.ilike(like) | models.Feedback.adapted_text.ilike(like)  # type: ignore[attr-defined]
        )
    if sentiment:
        stmt = stmt.where(models.Feedback.sentiment == sentiment)
    if topic:
        stmt = stmt.where(
            (models.Feedback.topic == topic)
            | (models.Feedback.predicted_category == topic)  # type: ignore[attr-defined]
            | (models.Feedback.official_category == topic)    # type: ignore[attr-defined]
        )
    if channel:
        stmt = stmt.where(models.Feedback.channel == channel)
    if product:
        stmt = stmt.where(models.Feedback.product == product)
    if not include_duplicates:
        stmt = stmt.where(models.Feedback.is_duplicate == False)  # noqa: E712

    order = {
        "newest": models.Feedback.created_at.desc(),
        "oldest": models.Feedback.created_at.asc(),
        "most_negative": models.Feedback.sentiment_score.asc(),
        "most_positive": models.Feedback.sentiment_score.desc(),
    }[sort]
    stmt = stmt.order_by(order)

    total = len(session.exec(stmt).all())
    items = session.exec(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return schemas.Page(total=total, page=page, page_size=page_size, items=[_to_out(f) for f in items])


@router.post("", response_model=schemas.FeedbackOut, status_code=201)
def create_feedback(payload: schemas.FeedbackCreate, session: Session = Depends(get_session)):
    fb = models.Feedback(**payload.model_dump(), analyzed=False)
    res = analysis.analyze_text(fb.text, fb.rating)
    for k, v in res.items():
        setattr(fb, k, v)
    fb.analyzed = True
    session.add(fb)
    session.commit()
    session.refresh(fb)
    return _to_out(fb)


@router.get("/facets")
def facets(session: Session = Depends(get_session)):
    """Distinct values for filter dropdowns."""
    rows = session.exec(select(models.Feedback)).all()
    topics = set()
    for r in rows:
        if r.official_category:                       # labelled dataset → official taxonomy
            if r.predicted_category:
                topics.add(r.predicted_category)
        elif r.topic:
            topics.add(r.topic)
    return {
        "topics": sorted(topics),
        "channels": sorted({r.channel for r in rows if r.channel}),
        "products": sorted({r.product for r in rows if r.product}),
        "sentiments": ["positive", "neutral", "negative"],
    }


@router.post("/import")
async def import_csv(file: UploadFile = File(...), session: Session = Depends(get_session)):
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "CSV has no header row.")

    imported, skipped = 0, 0
    for row in reader:
        body = _pick(row, TEXT_HEADERS)
        if not body:
            skipped += 1
            continue
        rating = None
        r = _pick(row, RATING_HEADERS)
        if r:
            try:
                rating = float(str(r).split()[0])
            except ValueError:
                rating = None
        date = None
        d = _pick(row, DATE_HEADERS)
        if d:
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
                try:
                    date = datetime.strptime(d[:19], fmt)
                    break
                except ValueError:
                    continue

        fb = models.Feedback(
            text=body,
            author=_pick(row, AUTHOR_HEADERS) or "Anonymous",
            channel=(_pick(row, CHANNEL_HEADERS) or "form").lower(),
            product=_pick(row, PRODUCT_HEADERS) or "",
            rating=rating,
            source_date=date,
            official_category=_pick(row, CATEGORY_HEADERS),
        )
        res = analysis.analyze_text(fb.text, fb.rating)
        for k, v in res.items():
            setattr(fb, k, v)
        fb.predicted_category = classify_official(fb.text)
        fb.analyzed = True
        session.add(fb)
        imported += 1

    session.commit()
    return {"imported": imported, "skipped": skipped, "filename": file.filename}


@router.get("/{feedback_id}", response_model=schemas.FeedbackOut)
def get_feedback(feedback_id: int, session: Session = Depends(get_session)):
    fb = session.get(models.Feedback, feedback_id)
    if not fb:
        raise HTTPException(404, "Feedback not found")
    return _to_out(fb)


@router.delete("/{feedback_id}", status_code=204)
def delete_feedback(feedback_id: int, session: Session = Depends(get_session)):
    fb = session.get(models.Feedback, feedback_id)
    if not fb:
        raise HTTPException(404, "Feedback not found")
    session.delete(fb)
    session.commit()


@router.post("/reanalyze")
def reanalyze(session: Session = Depends(get_session)):
    """Re-run the analysis engine over every row (uses adapted text when present)."""
    rows = session.exec(select(models.Feedback)).all()
    for fb in rows:
        res = analysis.analyze_text(fb.adapted_text or fb.text, fb.rating)
        for k, v in res.items():
            setattr(fb, k, v)
        fb.predicted_category = classify_official(fb.adapted_text or fb.text)
        fb.analyzed = True
        session.add(fb)
    session.commit()
    return {"analyzed": len(rows)}
