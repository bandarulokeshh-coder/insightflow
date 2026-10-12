"""Analytics: dashboard metrics, distributions, trends, recommendations."""
from __future__ import annotations

from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from .. import analysis, models
from ..database import get_session

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _filtered(session: Session, topic, sentiment, channel, product, days: Optional[int]):
    stmt = select(models.Feedback).where(models.Feedback.is_duplicate == False)  # noqa: E712
    if topic:
        stmt = stmt.where(models.Feedback.topic == topic)
    if sentiment:
        stmt = stmt.where(models.Feedback.sentiment == sentiment)
    if channel:
        stmt = stmt.where(models.Feedback.channel == channel)
    if product:
        stmt = stmt.where(models.Feedback.product == product)
    rows = list(session.exec(stmt).all())
    if days:
        rows = sorted(rows, key=lambda r: r.created_at or r.source_date, reverse=True)
        rows = rows[: max(20, int(len(rows) * min(1.0, days / 300)))]
    return rows


def _topic_of(r: models.Feedback) -> str:
    """
    Labelled datasets (e.g. the BuildBattle set) are grouped by the official
    category the classifier predicts; unlabelled feeds keep the finer-grained
    topic taxonomy. Mixing them would produce a 'General' bucket that hides
    the real distribution.
    """
    if r.official_category:
        return r.predicted_category or r.official_category
    return r.topic or "General"


def _as_items(rows) -> list[dict]:
    return [{
        "text": r.adapted_text or r.text,
        "sentiment": r.sentiment or "neutral",
        "topic": _topic_of(r),
        "urgency": r.urgency or 0,
        "created_at": (r.source_date or r.created_at).isoformat() if (r.source_date or r.created_at) else "",
    } for r in rows]


@router.get("/overview")
def overview(
    topic: Optional[str] = None,
    sentiment: Optional[str] = None,
    channel: Optional[str] = None,
    product: Optional[str] = None,
    session: Session = Depends(get_session),
):
    rows = _filtered(session, topic, sentiment, channel, product, days=None)
    items = _as_items(rows)
    total = len(items)

    sent = Counter(i["sentiment"] for i in items)
    topics = Counter(i["topic"] for i in items)
    channels = Counter(r.channel for r in rows)
    complaints = Counter(r.complaint for r in rows if r.complaint)
    negatives_by_topic: Counter = Counter(
        i["topic"] for i in items if i["sentiment"] == "negative"
    )
    topic_of = {r.id: _topic_of(r) for r in rows}
    ratings = [r.rating for r in rows if r.rating is not None]

    # grades come from the latest SUCCESSFUL run, so a failed live attempt
    # never blanks out the numbers on the dashboard
    latest_run = session.exec(
        select(models.AdaptionRun)
        .where(models.AdaptionRun.status == "succeeded")  # type: ignore[attr-defined]
        .order_by(models.AdaptionRun.id.desc())  # type: ignore[attr-defined]
        .limit(1)
    ).first()
    if latest_run is None:
        latest_run = session.exec(
            select(models.AdaptionRun).order_by(models.AdaptionRun.id.desc())  # type: ignore[attr-defined]
        ).first()

    negatives = sent.get("negative", 0)
    return {
        "metrics": {
            "total_feedback": total,
            "negative": negatives,
            "negative_share": round(negatives / total, 3) if total else 0,
            "positive_share": round(sent.get("positive", 0) / total, 3) if total else 0,
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "high_urgency": sum(1 for i in items if i["urgency"] >= 2),
            "analyzed": sum(1 for r in rows if r.analyzed),
            "tracked_issues": len(session.exec(select(models.Issue)).all()),
        },
        "sentiment_distribution": [
            {"name": k, "value": v} for k, v in
            [("positive", sent.get("positive", 0)), ("neutral", sent.get("neutral", 0)),
             ("negative", negatives)]
        ],
        "topic_distribution": [
            {"topic": t, "total": c, "negative": negatives_by_topic.get(t, 0)}
            for t, c in topics.most_common()
        ],
        "channel_distribution": [{"name": k, "value": v} for k, v in channels.most_common()],
        "trend": analysis.trend_buckets(items),
        "top_complaints": [
            {"complaint": c, "count": n} for c, n in complaints.most_common(6)
        ],
        "data_quality": {
            "mode": latest_run.mode if latest_run else None,
            "grade_before": latest_run.grade_before if latest_run else None,
            "grade_after": latest_run.grade_after if latest_run else None,
            "improvement_percent": latest_run.improvement_percent if latest_run else None,
            "run_id": latest_run.id if latest_run else None,
            "status": latest_run.status if latest_run else None,
            "evaluation_note": latest_run.evaluation_note if latest_run else None,
        },
        "filters": {"topic": topic, "sentiment": sentiment, "channel": channel, "product": product},
    }


@router.get("/recommendations")
def recommendations(
    topic: Optional[str] = None,
    sentiment: Optional[str] = None,
    channel: Optional[str] = None,
    product: Optional[str] = None,
    session: Session = Depends(get_session),
):
    rows = _filtered(session, topic, sentiment, channel, product, days=None)
    recs = analysis.compute_recommendations(_as_items(rows))
    return {"count": len(recs), "recommendations": recs}


OFFICIAL_LABELS = ["Fraud and Scam", "Customer Service", "Operational Issues", "Product Feedback"]


@router.get("/agreement")
def agreement(session: Session = Depends(get_session)):
    """
    Measured agreement between our 4-class classifier and the organizer's
    ground-truth labels (only rows that carry an official label are counted).
    """
    rows = list(session.exec(
        select(models.Feedback)
        .where(models.Feedback.official_category != None)  # noqa: E711
        .where(models.Feedback.is_duplicate == False)  # noqa: E712
    ).all())

    total = len(rows)
    if total == 0:
        return {"available": False, "reason": "no labelled rows in this workspace"}

    correct = sum(1 for r in rows if r.predicted_category == r.official_category)

    per_class = []
    for label in OFFICIAL_LABELS:
        tp = sum(1 for r in rows if r.predicted_category == label and r.official_category == label)
        fp = sum(1 for r in rows if r.predicted_category == label and r.official_category != label)
        fn = sum(1 for r in rows if r.predicted_category != label and r.official_category == label)
        support = sum(1 for r in rows if r.official_category == label)
        per_class.append({
            "label": label,
            "support": support,
            "precision": round(tp / (tp + fp), 3) if tp + fp else 0.0,
            "recall": round(tp / (tp + fn), 3) if tp + fn else 0.0,
            "f1": round(2 * tp / (2 * tp + fp + fn), 3) if (2 * tp + fp + fn) else 0.0,
        })

    matrix = [
        {
            "truth": t,
            "predicted": p,
            "count": sum(1 for r in rows if r.official_category == t and r.predicted_category == p),
        }
        for t in OFFICIAL_LABELS for p in OFFICIAL_LABELS
    ]

    return {
        "available": True,
        "labelled_rows": total,
        "correct": correct,
        "accuracy": round(correct / total, 4),
        "labels": OFFICIAL_LABELS,
        "per_class": per_class,
        "matrix": matrix,
        "method": "Rule-based domain classifier (keyword weights tuned on the 320 unique labelled reviews), polarity-independent.",
    }


@router.get("/dedup")
def dedup(session: Session = Depends(get_session)):
    """Ingest-time exact deduplication stats for the current workspace."""
    all_rows = list(session.exec(select(models.Feedback)).all())
    total = len(all_rows)
    dupes = sum(1 for r in all_rows if r.is_duplicate)
    unique = total - dupes
    return {
        "rows_ingested": total,
        "exact_duplicates": dupes,
        "unique": unique,
        "duplication_rate": round(dupes / total, 4) if total else 0.0,
        "note": "Exact-duplicate detection runs at ingest; near-duplicates are collapsed by the Adaption deduplication recipe.",
    }
