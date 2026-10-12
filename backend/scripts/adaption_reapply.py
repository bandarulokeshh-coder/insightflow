"""
Re-apply a previously downloaded Adaption artifact to the database.

No credits: the adaptation job is already paid for and the output is cached on
disk. Use this after improving the row mapping, or if the run was interrupted
before results were written.

    cd backend && python scripts/adaption_reapply.py /tmp/adapted_<dataset_id>.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session  # noqa: E402

from app import models  # noqa: E402
from app.adaption_service import _apply_rows, _map_live_row  # noqa: E402
from app.database import engine  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact", help="path to the downloaded .jsonl")
    ap.add_argument("--run-id", type=int, default=None, help="AdaptionRun id to attribute rows to")
    args = ap.parse_args()

    path = Path(args.artifact)
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    print(f"artifact rows: {len(rows)}")

    mapped = [_map_live_row(r) for r in rows]
    unmatched = sum(1 for m in mapped if not m.get("feedback_id"))
    with_action = sum(1 for m in mapped if m.get("recommended_action"))
    with_trace = sum(1 for m in mapped if m.get("reasoning"))
    print(f"mapped: {len(mapped)} | unmatched: {unmatched} | with action: {with_action} | with trace: {with_trace}")

    run_id = args.run_id
    if run_id is None:
        with Session(engine) as session:
            run = session.exec(
                __import__("sqlmodel").select(models.AdaptionRun).order_by(models.AdaptionRun.id.desc())
            ).first()
            run_id = run.id if run else 0
    print(f"applying against run #{run_id}")

    stats = _apply_rows(run_id, mapped, print)
    print("done:", stats)


if __name__ == "__main__":
    main()
