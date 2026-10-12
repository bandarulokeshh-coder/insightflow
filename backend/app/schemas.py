"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    text: str
    author: str = "Anonymous"
    channel: str = "form"
    product: str = ""
    rating: Optional[float] = None


class FeedbackOut(BaseModel):
    id: int
    text: str
    adapted_text: Optional[str] = None
    display_text: str
    author: str
    channel: str
    product: str
    rating: Optional[float]
    source_date: Optional[datetime]
    created_at: datetime
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    topic: Optional[str]
    complaint: Optional[str]
    urgency: int
    detected_language: Optional[str]
    official_category: Optional[str]
    predicted_category: Optional[str]
    adaption_action: Optional[str]
    reasoning_trace: Optional[str]
    is_duplicate: bool
    analyzed: bool


class Page(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[FeedbackOut]


class RunRequest(BaseModel):
    mode: str = "auto"                       # auto | live | demo
    max_rows: int = 200
    recipes: dict = {}
    blueprint: str = ""


class IssueCreate(BaseModel):
    title: str
    topic: str = ""
    description: str = ""
    priority: int = 0
    priority_label: str = "medium"
    evidence: str = ""
    owner: str = ""


class IssueUpdate(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    title: Optional[str] = None
    priority: Optional[int] = None
    priority_label: Optional[str] = None
