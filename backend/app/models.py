"""Database models — feedback, Adaption runs, issues, and analysis results."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Feedback(SQLModel, table=True):
    """A single piece of customer feedback, raw + analyzed."""

    id: Optional[int] = Field(default=None, primary_key=True)

    # --- raw fields -------------------------------------------------
    text: str
    author: str = "Anonymous"
    channel: str = "survey"          # review | survey | support | app_store | social | form
    product: str = ""
    rating: Optional[float] = None   # 1..5 when the source provides it
    source_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)

    # --- adaption (Feedback Refinery) fields -------------------------
    adaption_run_id: Optional[int] = None
    adapted_text: Optional[str] = None       # rephrased / normalized / translated
    detected_language: Optional[str] = None
    is_duplicate: bool = False
    reasoning_trace: Optional[str] = None    # the "why" behind the adaptation

    # --- analysis fields ---------------------------------------------
    sentiment: Optional[str] = None          # positive | negative | neutral
    sentiment_score: Optional[float] = None  # -1..1
    topic: Optional[str] = None              # Delivery | Refund | ...
    complaint: Optional[str] = None          # extracted complaint clause
    urgency: int = 0                         # 0..3 escalation signal
    analyzed: bool = False

    # --- official taxonomy (BuildBattle 2026 dataset) -----------------
    official_category: Optional[str] = None  # ground-truth label from the CSV, when present
    predicted_category: Optional[str] = None # our 4-class classifier output

    # --- live Adaption output -----------------------------------------
    adaption_action: Optional[str] = None    # recommended_action returned by the platform

    @property
    def display_text(self) -> str:
        return self.adapted_text or self.text


class AdaptionRun(SQLModel, table=True):
    """One execution of the Feedback Refinery (Adaption)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    run_ref: Optional[str] = None            # Adaption run_id / dataset_id when live
    mode: str = "demo"                       # live | demo
    status: str = "pending"                  # pending | running | succeeded | failed

    max_rows: int = 200
    recipes: str = "{}"                      # JSON string of enabled recipes
    blueprint: str = ""

    rows_in: int = 0
    rows_out: int = 0
    duplicates_removed: int = 0
    languages_normalized: int = 0
    credits_estimate: Optional[float] = None
    credits_consumed: Optional[float] = None

    grade_before: Optional[float] = None     # data-quality score out of 100
    grade_after: Optional[float] = None
    improvement_percent: Optional[float] = None

    evaluation_note: str = ""
    log: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    finished_at: Optional[datetime] = None


class Issue(SQLModel, table=True):
    """A tracked issue — created from a recommendation or manually."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    topic: str = ""
    description: str = ""
    priority: int = 0                        # 0..100 priority score
    priority_label: str = "medium"           # critical | high | medium | low
    status: str = "open"                     # open | in_progress | resolved
    evidence: str = ""                       # JSON: example quotes + counts
    owner: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
