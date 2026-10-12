"""
FREE cost quote for a live Adaption run on the official dataset.

Uploads the 290 deduplicated rows, validates our exact production config
(column mapping, recipes, brand controls), asks Adaption to quote the run,
then deletes the uploaded dataset so the account is left as we found it.

    adapt(estimate=True) = validate + quote, NO credits, NO run started.

Run:  cd backend && python scripts/adaption_estimate.py
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from adaption import Adaption  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app import models  # noqa: E402
from app.adaption_service import BLUEPRINT_DEFAULT  # noqa: E402
from app.database import engine  # noqa: E402


def main() -> None:
    key = os.environ.get("ADAPTION_API_KEY", "")
    assert key, "ADAPTION_API_KEY missing"
    client = Adaption(api_key=key)

    with Session(engine) as session:
        rows = list(session.exec(
            select(models.Feedback).where(models.Feedback.is_duplicate == False)  # noqa: E712
        ).all())

    out = Path("/tmp/insightflow_estimate_input.csv")
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["feedback_id", "text", "channel", "product", "rating", "category"])
        w.writeheader()
        for r in rows:
            w.writerow({
                "feedback_id": r.id, "text": r.text, "channel": r.channel,
                "product": r.product, "rating": r.rating or "",
                "category": r.official_category or "",
            })
    print(f"exported {len(rows)} unique rows → {out}")

    upload = client.datasets.upload_file(str(out), name="insightflow-estimate-quote")
    ds_id = upload.dataset_id
    print("uploaded dataset:", ds_id, "(upload only — no adaptation)")

    column_mapping = {"prompt": "text", "context": ["channel", "product", "category"]}
    job_specification = {"max_rows": len(rows)}

    # same config the app uses in live mode (English-only corpus → no language_expansion)
    base = dict(
        dataset_id=ds_id,
        column_mapping=column_mapping,
        job_specification=job_specification,
    )

    configs = {
        "A · dedupe + rephrase only": {
            "recipe_specification": {"recipes": {"deduplication": True, "prompt_rephrase": True}},
        },
        "B · dedupe + rephrase + reasoning traces (app default)": {
            "recipe_specification": {"recipes": {
                "deduplication": True, "prompt_rephrase": True, "reasoning_traces": True,
            }},
            "brand_controls": {"blueprint": BLUEPRINT_DEFAULT},
        },
    }

    print()
    for name, extra in configs.items():
        try:
            est = client.datasets.adapt(**base, estimate=True, **extra)
            print(f"  {name}")
            print(f"     credits: {est.estimated_credits_consumed}   minutes: {est.estimated_minutes}")
        except Exception as exc:
            print(f"  {name}\n     ERROR: {type(exc).__name__}: {str(exc)[:220]}")
        print()

    # leave the account tidy
    try:
        client.datasets.delete(ds_id)
        print("cleaned up: uploaded dataset deleted (account left as found)")
    except Exception as exc:
        print(f"note: could not delete {ds_id} ({type(exc).__name__}) — remove it manually if you wish")


if __name__ == "__main__":
    main()
