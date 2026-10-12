"""
Recover / apply a live Adaption run by dataset id.

Useful if the API server restarts while a long run is in flight: the job keeps
running on Adaption's side, and this script re-attaches to it, waits, downloads
the adapted rows, maps them, and writes a proper run row + results into the DB.

    cd backend && python scripts/adaption_apply_live.py <dataset_id> [--run-id N]

No extra credits are consumed — the adaptation job has already been paid for.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from adaption import Adaption  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app import models  # noqa: E402
from app.adaption_service import (  # noqa: E402
    ARTIFACT_DIR, _append_log, _apply_rows, _finish_run, _map_live_row, _num,
)
from app.database import engine  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset_id")
    ap.add_argument("--run-id", type=int, default=None, help="existing AdaptionRun row to update")
    ap.add_argument("--timeout", type=int, default=7200)
    args = ap.parse_args()

    client = Adaption(api_key=os.environ["ADAPTION_API_KEY"])
    ds_id = args.dataset_id

    run_id = args.run_id
    if run_id is None:
        with Session(engine) as session:
            run = models.AdaptionRun(mode="live", status="running", max_rows=0,
                                     log=f"Recovered live run for dataset {ds_id}\n")
            session.add(run)
            session.commit()
            session.refresh(run)
            run_id = run.id
    print(f"run id: {run_id} | dataset: {ds_id}")

    deadline = time.time() + args.timeout
    last = None
    while time.time() < deadline:
        st = client.datasets.get_status(ds_id)
        status = getattr(st, "status", None)
        prog = getattr(st, "progress", None)
        line = f"  status={status} progress={prog}"
        if line != last:
            print(line, flush=True)
            _append_log(run_id, line)
            last = line
        if status == "failed":
            _finish_run(run_id, "failed", evaluation_note=f"Adaption reported failure: {getattr(st, 'error_data', None)}")
            print("run failed on Adaption's side")
            return
        if status == "succeeded":
            break
        time.sleep(30)
    else:
        print("timed out waiting — rerun this script to keep waiting (no extra credits)")
        return

    # evaluation (may lag)
    grade_before = grade_after = improvement = None
    note = ""
    for _ in range(30):
        ds = client.datasets.get(ds_id)
        summary = getattr(ds, "evaluation_summary", None)
        if summary is None:
            try:
                summary = client.datasets.get_evaluation(ds_id)
            except Exception:
                summary = None
        if summary is not None:
            grade_after = _num(getattr(summary, "score_after", None))
            if grade_after is not None:
                grade_before = _num(getattr(summary, "score_before", None))
                improvement = _num(getattr(summary, "improvement_percent", None))
                note = (f"Adaptive Data: {getattr(summary, 'grade_before', '?')} → "
                        f"{getattr(summary, 'grade_after', '?')} "
                        f"(score {grade_before} → {grade_after}, +{improvement}%)")
                break
        time.sleep(10)

    export = client.datasets.download(ds_id, file_format="jsonl")
    path = str(ARTIFACT_DIR / f"adapted_{ds_id}.jsonl")
    export.write_to_file(path)
    print(f"downloaded → {path}")

    adapted = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    adapted.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if adapted:
        print("output keys:", sorted({k for r in adapted for k in r}))
    mapped = [_map_live_row(r) for r in adapted]
    unmatched = sum(1 for m in mapped if not m.get("feedback_id"))
    if unmatched:
        print(f"WARNING: {unmatched} rows unmatched (no feedback_id)")

    with Session(engine) as session:
        run = session.get(models.AdaptionRun, run_id)
        session.add(run)
    stats = _apply_rows(run_id, mapped, lambda line: (print(line), _append_log(run_id, line)))
    _finish_run(
        run_id, "succeeded",
        run_ref=ds_id, rows_out=stats["applied"],
        duplicates_removed=stats["duplicates"], languages_normalized=stats["languages"],
        grade_before=grade_before, grade_after=grade_after, improvement_percent=improvement,
        evaluation_note=note or "Live Adaptive Data run (recovered).",
    )
    print(f"applied {stats['applied']} rows | grades: {grade_before} → {grade_after} (+{improvement}%)")


if __name__ == "__main__":
    main()
