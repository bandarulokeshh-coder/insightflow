"""Database setup — SQLite via SQLModel. Zero-config for the hackathon."""
from __future__ import annotations

import os

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./insightflow.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def init_db() -> None:
    # Import models so SQLModel knows the tables before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
