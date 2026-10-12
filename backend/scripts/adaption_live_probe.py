"""
LIVE probe — validates the Adaption integration against the real API.

Uploads a 5-row feedback sample, checks the credit estimate, runs a minimal
Adaptive Data job, and prints the exact output schema so the mapper in
`app/adaption_service.py` can be verified against reality.

Run:  cd backend && python scripts/adaption_live_probe.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from adaption import Adaption  # noqa: E402

KEY = os.environ.get("ADAPTION_API_KEY", "")
assert KEY, "ADAPTION_API_KEY missing"

BLUEPRINT = (
    "You are an analyst working for an Indian quick-commerce company. "
    "For every piece of customer feedback, return STRICT JSON only: "
    '{"sentiment": "positive|negative|neutral", "score": -1..1, '
    '"topic": "Delivery|App Bug|Refund|Billing|Support|Product Quality|Packaging|App UX|Performance|Payments|General", '
    '"complaint": "the core complaint in one clause, or empty if none", '
    '"urgency": 0-3, "recommended_action": "one concrete, owner-assignable action", '
    '"normalized_text": "the feedback rewritten in clear business English"} '
    "Keep normalized_text faithful to the original meaning."
)

ROWS = [
    {"feedback_id": 1, "text": "Delivery was 45 minutes late and the food arrived cold.", "channel": "app_store", "product": "Groceries"},
    {"feedback_id": 2, "text": "Naaku refund ravatam ledu, 10 days ayyindi. Money back ivvandi please.", "channel": "support", "product": "Dairy & Bakery"},
    {"feedback_id": 3, "text": "App crashes every time I open the cart. pls fix 🙏", "channel": "review", "product": "Groceries"},
    {"feedback_id": 4, "text": "Milk packet leaked inside the bag and spoiled other groceries.", "channel": "survey", "product": "Dairy & Bakery"},
    {"feedback_id": 5, "text": "Delivery was 45 minutes late and the food arrived cold.", "channel": "app_store", "product": "Groceries"},  # exact duplicate on purpose
]


def main() -> None:
    client = Adaption(api_key=KEY)

    probe = Path("/tmp/insightflow_probe.csv")
    with probe.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["feedback_id", "text", "channel", "product"])
        w.writeheader()
        w.writerows(ROWS)
    print(f"probe CSV: {probe} ({len(ROWS)} rows)")

    upload = client.datasets.upload_file(str(probe), name="insightflow-probe")
    ds_id = upload.dataset_id
    print("uploaded dataset:", ds_id)

    while True:
        st = client.datasets.get_status(ds_id)
        print("  status:", getattr(st, "status", None), "| rows:", getattr(st, "row_count", None))
        if getattr(st, "status", None) == "failed":
            print("  ERROR:", getattr(st, "error_data", None))
            return
        if getattr(st, "row_count", None):
            break
        time.sleep(3)

    column_mapping = {"prompt": "text", "context": ["channel", "product"]}
    job_specification = {"max_rows": 5}
    recipe_specification = {"recipes": {"deduplication": True, "prompt_rephrase": True, "reasoning_traces": True}}
    brand_controls = {"blueprint": BLUEPRINT}

    est = client.datasets.adapt(
        ds_id, column_mapping=column_mapping, job_specification=job_specification,
        recipe_specification=recipe_specification, brand_controls=brand_controls, estimate=True,
    )
    print(f"\nESTIMATE → credits: {est.estimated_credits_consumed} | minutes: {est.estimated_minutes}")

    run = client.datasets.adapt(
        ds_id, column_mapping=column_mapping, job_specification=job_specification,
        recipe_specification=recipe_specification, brand_controls=brand_controls,
    )
    print("run started:", run.run_id)

    t0 = time.time()
    status = client.datasets.wait_for_completion(ds_id, timeout=1800)
    print(f"completed in {round(time.time() - t0)}s → status: {getattr(status, 'status', None)}")

    # evaluation (may lag completion)
    for attempt in range(20):
        try:
            ev = client.datasets.get_evaluation(ds_id)
            if getattr(ev, "improvement_percent", None) is not None or getattr(ev, "score_after", None) is not None:
                print("evaluation:", ev.model_dump() if hasattr(ev, "model_dump") else ev)
                break
        except Exception as exc:
            print("  (evaluation not ready:", str(exc)[:80], ")")
        time.sleep(10)
    else:
        ds = client.datasets.get(ds_id)
        print("dataset.evaluation_summary:", getattr(ds, "evaluation_summary", None))

    export = client.datasets.download(ds_id, file_format="jsonl")
    out = Path("/tmp/insightflow_probe_out.jsonl")
    export.write_to_file(str(out))
    print(f"\ndownloaded → {out}")

    with out.open(encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    print(f"output rows: {len(lines)}")
    if lines:
        print("\nOUTPUT SCHEMA (first row keys):", sorted(lines[0].keys()))
        print("\nFIRST ROW:")
        print(json.dumps(lines[0], indent=2)[:2200])

    print("\nPROBE DATASET ID (delete manually if desired):", ds_id)


if __name__ == "__main__":
    main()
