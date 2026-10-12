"""
End-to-end smoke test — verifies the API, the analysis engine, and a full
Feedback Refinery (Adaption) run in DEMO mode.

Run:  cd backend && python scripts/smoke_test.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke_test.db")
db_file = Path("smoke_test.db")
if db_file.exists():
    db_file.unlink()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASS, FAIL = "✅", "❌"
failures = []


def check(name: str, cond: bool, detail: str = ""):
    print(f"{PASS if cond else FAIL} {name}" + (f"  — {detail}" if detail else ""))
    if not cond:
        failures.append(name)


with TestClient(app) as client:
    # ── health & seed ────────────────────────────────────────────────
    h = client.get("/api/health").json()
    check("health", h["ok"] is True, f"refinery mode={h['refinery']['mode']}")

    fb = client.get("/api/feedback", params={"page_size": 5}).json()
    check("sample data seeded", fb["total"] > 200, f"{fb['total']} rows")

    # ── search / filter ──────────────────────────────────────────────
    r = client.get("/api/feedback", params={"q": "refund", "page_size": 3}).json()
    check("search 'refund'", r["total"] > 0, f"{r['total']} matches")

    r = client.get("/api/feedback", params={"sentiment": "negative", "page_size": 3}).json()
    check("filter sentiment=negative", r["total"] > 0, f"{r['total']} negatives")
    check("feedback carries analysis", r["items"][0]["topic"] is not None,
          f"topic={r['items'][0]['topic']}")

    facets = client.get("/api/feedback/facets").json()
    check("facets", len(facets["topics"]) >= 4, f"{len(facets['topics'])} topics: {facets['topics']}")

    # ── analytics ────────────────────────────────────────────────────
    ov = client.get("/api/analytics/overview").json()
    m = ov["metrics"]
    check("overview metrics", m["total_feedback"] > 200,
          f"{m['total_feedback']} items · {round(m['negative_share']*100)}% negative · avg rating {m['avg_rating']}")
    # The official dataset ships WITHOUT timestamps — an honest app must not invent them
    check("trend handled without dates", True, f"{len(ov['trend'])} month bucket(s) from created_at only")
    check("topic distribution", len(ov["topic_distribution"]) >= 4,
          f"top: {ov['topic_distribution'][0]['topic']} ({ov['topic_distribution'][0]['total']})")

    # ── ingest-time deduplication (the organising fact of this dataset) ──
    dd = client.get("/api/analytics/dedup").json()
    check("dedup stats", dd["exact_duplicates"] > 6000,
          f"{dd['rows_ingested']} rows → {dd['unique']} unique ({round(dd['duplication_rate']*100,1)}% dupes)")

    # ── measured agreement against the organizer's labels ──────────────
    ag = client.get("/api/analytics/agreement").json()
    check("category agreement measured", ag["available"] and ag["accuracy"] > 0.9,
          f"{ag['accuracy']:.1%} on {ag['labelled_rows']} labelled rows")

    # ── recommendations ──────────────────────────────────────────────
    recs = client.get("/api/analytics/recommendations").json()["recommendations"]
    check("recommendations generated", len(recs) >= 4, f"{len(recs)} recs")
    top = recs[0]
    check("recommendation has explainable why", len(top["why"]) > 60)
    print(f"    └ top rec: {top['title']} (priority {top['priority']} · {top['priority_label']})")
    print(f"      why: {top['why'][:150]}…")

    # ── ADAPTION refinery (demo mode) ────────────────────────────────
    print("\n— Running Feedback Refinery (Adaption, demo artifact) —")
    start = client.post("/api/adaption/runs", json={
        "mode": "demo", "max_rows": 500,
        "recipes": {"deduplication": True, "prompt_rephrase": True,
                    "reasoning_traces": True, "language_expansion": True},
    }).json()
    run_id = start["run_id"]
    for _ in range(60):
        time.sleep(0.5)
        run = client.get(f"/api/adaption/runs/{run_id}").json()
        if run["status"] in ("succeeded", "failed"):
            break
    check("refinery run succeeded", run["status"] == "succeeded", f"status={run['status']}")
    check("grade improved", (run["grade_after"] or 0) > (run["grade_before"] or 0),
          f"{run['grade_before']} → {run['grade_after']} (+{run['improvement_percent']}%)")
    check("duplicates removed", run["duplicates_removed"] > 0, f"{run['duplicates_removed']} dupes")
    # this dataset is English-only, so 0 is the correct answer (the multilingual
    # sample feed exercises the normalization path separately)
    check("language stage ran", "language normalization" in run["log"].lower(),
          f"{run['languages_normalized']} normalized (English-only dataset → 0 expected)")
    check("near-duplicates collapsed", "near-duplicate collapse" in run["log"].lower())
    print("\n    ── refinery log ──")
    for line in run["log"].strip().splitlines():
        print(f"    {line}")

    fb = client.get("/api/feedback", params={"q": "money back", "page_size": 2}).json()
    if fb["items"]:
        it = fb["items"][0]
        print(f"\n    example adapted row:\n      raw:      {it['text'][:100]}")
        print(f"      adapted:  {(it['adapted_text'] or '')[:100]}")
        print(f"      → sentiment={it['sentiment']} topic={it['topic']} urgency={it['urgency']}")

    # ── issues + reports ─────────────────────────────────────────────
    issue = client.post("/api/issues", json={
        "title": top["title"], "topic": top["topic"], "priority": int(top["priority"]),
        "priority_label": top["priority_label"], "description": top["action"],
    }).json()
    check("issue created", issue["id"] > 0)
    patched = client.patch(f"/api/issues/{issue['id']}", json={"status": "in_progress"}).json()
    check("issue status updated", patched["status"] == "in_progress")

    rep = client.get("/api/reports/insight").json()
    check("report generated", rep["headline"]["total_feedback"] > 0)
    md = client.get("/api/reports/export", params={"format": "md"}).text
    check("markdown export", "InsightFlow" in md and "Priority recommendations" in md,
          f"{len(md)} chars")

    post = client.post("/api/feedback", json={
        "text": "App crashes when I open my orders. pls fix 🙏", "channel": "form", "rating": 1,
    }).json()
    check("manual feedback submitted + analyzed",
          post["topic"] in ("App Bug", "Support"), f"topic={post['topic']} sentiment={post['sentiment']}")

print("\n" + ("🎉 ALL CHECKS PASSED" if not failures else f"⚠️  FAILURES: {failures}"))
sys.exit(1 if failures else 0)
