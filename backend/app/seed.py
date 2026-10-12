"""
Load the BuildBattle 2026 official dataset into the database on first boot.

Dataset facts that shape this loader:
  • 7,000 rows but only 320 unique reviews (95.4% exact duplication)
  • labels: 4 categories (domain labels, polarity-independent)
  • NO timestamps — so trend analysis only lights up for dated imports
  • English only

Exact duplicates are flagged AT INGEST (keeping the first occurrence) because
that is a verifiable fact about the rows, not a model inference. Near-duplicate
collapsing and enrichment belong to the Adaption refinery, which runs after.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, func, select

from . import analysis, models
from .database import engine
from .official import classify_official

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_CSV = ROOT / "sample_data" / "official_dataset.csv"
LEGACY_CSV = ROOT / "sample_data" / "feedback.csv"


def _norm_key(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def load_csv(path: Path, *, flag_exact_duplicates: bool = True) -> dict:
    """Import a feedback CSV, flagging exact duplicates as they are seen."""
    imported = duplicates = 0
    seen: set[str] = set()

    with Session(engine) as session:
        with path.open(encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                text = (row.get("review") or row.get("text") or "").strip()
                if not text:
                    continue

                key = _norm_key(text)
                is_dup = flag_exact_duplicates and key in seen
                if is_dup:
                    duplicates += 1
                else:
                    seen.add(key)

                source_date = None
                raw_date = str(row.get("date") or "").strip()
                if raw_date:
                    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
                        try:
                            source_date = datetime.strptime(raw_date[:19], fmt)
                            break
                        except ValueError:
                            continue

                fb = models.Feedback(
                    text=text,
                    author=row.get("author") or "Customer",
                    source_date=source_date,
                    channel=(row.get("channel") or "import").strip().lower(),
                    product=row.get("product") or "",
                    rating=float(row["rating"]) if str(row.get("rating") or "").strip() else None,
                    official_category=(row.get("category") or "").strip() or None,
                    is_duplicate=is_dup,
                )
                if not is_dup:  # only analyse the rows that survive dedup
                    res = analysis.analyze_text(fb.text, fb.rating)
                    for k, v in res.items():
                        setattr(fb, k, v)
                    fb.predicted_category = classify_official(fb.text)
                    fb.analyzed = True
                session.add(fb)
                imported += 1
        session.commit()

    return {"imported": imported, "duplicates": duplicates, "unique": imported - duplicates}


def seed_if_empty(force: bool = False) -> dict:
    with Session(engine) as session:
        count = session.exec(select(func.count()).select_from(models.Feedback)).one()
        if count and not force:
            return {"seeded": 0, "reason": "database already has rows"}

    if OFFICIAL_CSV.exists():
        stats = load_csv(OFFICIAL_CSV)
        return {
            "seeded": stats["imported"],
            "unique": stats["unique"],
            "duplicates_flagged": stats["duplicates"],
            "source": OFFICIAL_CSV.name,
            "reason": "BuildBattle 2026 official dataset loaded",
        }

    if LEGACY_CSV.exists():  # fallback: the multilingual sample feed
        stats = load_csv(LEGACY_CSV)
        return {"seeded": stats["imported"], "source": LEGACY_CSV.name, "reason": "sample feed loaded"}

    return {"seeded": 0, "reason": "no dataset found"}
