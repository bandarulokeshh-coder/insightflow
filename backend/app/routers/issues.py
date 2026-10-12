"""Issue tracking endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import models, schemas
from ..database import get_session

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.get("")
def list_issues(status: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(models.Issue).order_by(models.Issue.priority.desc())  # type: ignore[attr-defined]
    if status:
        stmt = stmt.where(models.Issue.status == status)
    return {"issues": [i.model_dump() for i in session.exec(stmt).all()]}


@router.post("", status_code=201)
def create_issue(payload: schemas.IssueCreate, session: Session = Depends(get_session)):
    issue = models.Issue(**payload.model_dump())
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return issue.model_dump()


@router.patch("/{issue_id}")
def update_issue(issue_id: int, payload: schemas.IssueUpdate, session: Session = Depends(get_session)):
    issue = session.get(models.Issue, issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(issue, k, v)
    issue.updated_at = datetime.now(timezone.utc)
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return issue.model_dump()


@router.delete("/{issue_id}", status_code=204)
def delete_issue(issue_id: int, session: Session = Depends(get_session)):
    issue = session.get(models.Issue, issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found")
    session.delete(issue)
    session.commit()
