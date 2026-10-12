"""
Feedback Refinery — the Adaption integration.

This module orchestrates the *meaningful* use of Adaption inside
InsightFlow's AI/data workflow:

    raw feedback  ──►  adaption.datasets.upload_file()      (ingest)
                  ──►  datasets.adapt(estimate=True)        (credit quote)
                  ──►  datasets.adapt(recipes, blueprint)   (the refinery run)
                  ──►  wait_for_completion + evaluation      (grade_before → grade_after)
                  ──►  datasets.download()                   (adapted rows flow into analysis)

Recipes used and *why they matter here*:
  • deduplication      — duplicate reviews skew frequency-based priority scoring
  • prompt_rephrase    — turns messy free-text into analysable statements
  • language_expansion — normalizes the Hinglish/Telugu-English mix to English
  • reasoning_traces   — powers the "why" behind every recommendation (§4)
  • blueprint          — injects a per-business analyst persona + JSON schema

When ADAPTION_API_KEY is absent the module falls back to a *cached
artifact* produced by `refinery_demo.py`, so the whole product stays
demonstrable. The Demo Console labels the mode explicitly — never pretend.
"""
from __future__ import annotations

import json
import os
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from . import models
from .database import engine

SDK_AVAILABLE = True
try:
    from adaption import Adaption  # type: ignore
except Exception:  # pragma: no cover - SDK optional
    Adaption = None  # type: ignore
    SDK_AVAILABLE = False

API_KEY = os.getenv("ADAPTION_API_KEY", "").strip()

ARTIFACT_DIR = Path(os.getenv("ADAPTION_ARTIFACT_DIR", "/tmp"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

BLUEPRINT_DEFAULT = (
    "You are an analyst working for an e-commerce marketplace. "
    "For every piece of customer feedback, return STRICT JSON only: "
    '{"sentiment": "positive|negative|neutral", "score": -1..1, '
    '"topic": "Fraud and Scam|Customer Service|Operational Issues|Product Feedback", '
    '"complaint": "the core complaint in one clause, or empty if none", '
    '"urgency": 0-3, '
    '"recommended_action": "one concrete, owner-assignable action"} '
    "Keep the feedback faithful to the original meaning."
)


# ─────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────
def refinery_status() -> dict:
    return {
        "sdk_installed": SDK_AVAILABLE,
        "api_key_present": bool(API_KEY),
        "mode": "live" if (SDK_AVAILABLE and API_KEY) else "demo",
        "blueprint_default": BLUEPRINT_DEFAULT,
        "recipes_catalog": [
            {"key": "deduplication", "label": "Prompt deduplication",
             "why": "Duplicate reviews inflate issue frequency and skew priority scores."},
            {"key": "prompt_rephrase", "label": "Prompt rephrasing",
             "why": "Turns messy, typo-laden free text into analysable statements."},
            {"key": "reasoning_traces", "label": "Reasoning traces",
             "why": "Captures *why* each classification was made — powers explainable recommendations."},
            {"key": "language_expansion", "label": "Language normalization",
             "why": "Rewrites Hinglish / regional-English feedback into one analyzable language."},
            {"key": "hallucination_mitigation", "label": "Hallucination mitigation",
             "why": "Grounds generated analysis in verifiable source text."},
        ],
    }


def launch_run(session: Session, mode: str, max_rows: int, recipes: dict, blueprint: str) -> models.AdaptionRun:
    """Create the run row and start it in a background thread."""
    effective_mode = mode
    if mode == "auto":
        effective_mode = "live" if (SDK_AVAILABLE and API_KEY) else "demo"

    run = models.AdaptionRun(
        mode=effective_mode,
        status="pending",
        max_rows=max_rows,
        recipes=json.dumps(recipes),
        blueprint=blueprint or BLUEPRINT_DEFAULT,
        log="Run queued.\n",
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    target = _run_live if effective_mode == "live" else _run_demo
    threading.Thread(target=target, args=(run.id,), daemon=True).start()
    return run


# ─────────────────────────────────────────────────────────────────────
# Shared: write adapted rows back into the database
# ─────────────────────────────────────────────────────────────────────
def _apply_rows(run_id: int, rows: list[dict], log) -> dict:
    """
    rows: [{feedback_id, adapted_text, sentiment, score, topic, complaint,
            urgency, recommended_action, reasoning}]
    Returns counters.
    """
    applied, langs, dupes = 0, 0, 0
    with Session(engine) as session:
        for r in rows:
            fb = session.get(models.Feedback, r.get("feedback_id"))
            if fb is None:
                continue
            if r.get("is_duplicate"):
                fb.is_duplicate = True
                fb.adaption_run_id = run_id
                dupes += 1
                session.add(fb)
                continue
            fb.adaption_run_id = run_id
            if r.get("adapted_text"):
                fb.adapted_text = r["adapted_text"]
            if r.get("detected_language"):
                fb.detected_language = r["detected_language"]
                if r["detected_language"] not in ("en", "unknown"):
                    langs += 1
            if r.get("sentiment"):
                fb.sentiment = r["sentiment"]
                fb.sentiment_score = float(r.get("score") or 0.0)
            if r.get("topic"):
                fb.topic = r["topic"]
            if r.get("complaint"):
                fb.complaint = r["complaint"]
            if r.get("recommended_action"):
                fb.adaption_action = r["recommended_action"]
            if r.get("urgency") is not None:
                fb.urgency = int(r["urgency"])
            fb.reasoning_trace = r.get("reasoning") or None
            fb.analyzed = True
            session.add(fb)
            applied += 1
        session.commit()
    log(f"Applied adaptation to {applied} rows ({dupes} duplicates flagged, {langs} languages normalized).")
    return {"applied": applied, "duplicates": dupes, "languages": langs}


def _finish_run(run_id: int, status: str, **fields):
    with Session(engine) as session:
        run = session.get(models.AdaptionRun, run_id)
        if not run:
            return
        for k, v in fields.items():
            setattr(run, k, v)
        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        session.add(run)
        session.commit()


def _append_log(run_id: int, line: str):
    with Session(engine) as session:
        run = session.get(models.AdaptionRun, run_id)
        if not run:
            return
        run.log = (run.log or "") + line + "\n"
        session.add(run)
        session.commit()


# ─────────────────────────────────────────────────────────────────────
# DEMO MODE — cached artifact (no credits needed)
# ─────────────────────────────────────────────────────────────────────
def _run_demo(run_id: int):
    from . import refinery_demo

    try:
        with Session(engine) as session:
            run = session.get(models.AdaptionRun, run_id)
            if not run:
                return
            session.add(run)
            run.status = "running"
            session.commit()
            recipes = json.loads(run.recipes or "{}")
            max_rows = run.max_rows
            blueprint = run.blueprint

        # bind run_id into the callbacks the refinery uses
        log = lambda line: _append_log(run_id, line)                          # noqa: E731
        apply_rows = lambda rid, rows, _log: _apply_rows(run_id, rows, log)   # noqa: E731
        finish = lambda rid, status, **kw: _finish_run(run_id, status, **kw)  # noqa: E731

        refinery_demo.execute(run_id, max_rows, recipes, blueprint, log, apply_rows, finish)
    except Exception as exc:  # pragma: no cover
        _append_log(run_id, f"DEMO refinery failed: {exc}\n{traceback.format_exc()}")
        _finish_run(run_id, "failed", evaluation_note=str(exc))


# ─────────────────────────────────────────────────────────────────────
# LIVE MODE — the real Adaption API
# ─────────────────────────────────────────────────────────────────────
def _run_live(run_id: int):  # pragma: no cover - requires API key + network
    try:
        with Session(engine) as session:
            run = session.get(models.AdaptionRun, run_id)
            if not run:
                return
            run.status = "running"
            run.log = "LIVE mode — calling Adaption API.\n"
            session.add(run)
            session.commit()
            recipes = json.loads(run.recipes or "{}")
            max_rows = run.max_rows
            blueprint = run.blueprint
            session.add(run)

        log = lambda line: _append_log(run_id, line)  # noqa: E731
        client = Adaption(api_key=API_KEY)

        # 1) Export current feedback to a CSV for ingestion -----------
        import csv
        import tempfile

        with Session(engine) as session:
            rows = session.exec(
                select(models.Feedback).where(models.Feedback.is_duplicate == False)  # noqa: E712
            ).all()
        rows = rows[: max(10, max_rows)]

        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="")
        writer = csv.DictWriter(
            tmp, fieldnames=["feedback_id", "text", "channel", "product", "rating", "category"]
        )
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "feedback_id": r.id, "text": r.text, "channel": r.channel,
                "product": r.product, "rating": r.rating or "",
                "category": r.official_category or "",
            })
        tmp.close()
        log(f"Exported {len(rows)} feedback rows → {tmp.name}")

        # 2) Ingest ---------------------------------------------------
        upload = client.datasets.upload_file(tmp.name)
        dataset_id = upload.dataset_id
        log(f"Uploaded dataset {dataset_id}. Waiting for ingestion…")

        import time
        while True:
            status = client.datasets.get_status(dataset_id)
            if getattr(status, "status", None) == "failed":
                raise RuntimeError(f"Ingestion failed: {status.error_data}")
            if getattr(status, "row_count", None):
                log(f"Ingested {status.row_count} rows.")
                break
            time.sleep(3)

        column_mapping = {"prompt": "text", "context": ["channel", "product", "category"]}
        # the API rejects samples_to_process > row_count, so clamp to what we sent
        effective_rows = min(max_rows, len(rows))
        job_specification = {"max_rows": effective_rows}
        if effective_rows != max_rows:
            log(f"Note: max_rows clamped {max_rows} → {effective_rows} (rows exported).")

        # 3) Estimate (never burn credits blind) ----------------------
        estimate = client.datasets.adapt(
            dataset_id, column_mapping=column_mapping,
            job_specification=job_specification, estimate=True,
        )
        credits = getattr(estimate, "estimated_credits_consumed", None)
        log(f"Credit estimate: {credits}")

        # 4) Run the refinery ------------------------------------------
        recipe_specification = {"recipes": {
            "deduplication": bool(recipes.get("deduplication", True)),
            "prompt_rephrase": bool(recipes.get("prompt_rephrase", True)),
            "reasoning_traces": bool(recipes.get("reasoning_traces", True)),
        }}
        brand_controls = {"blueprint": blueprint}
        if recipes.get("hallucination_mitigation"):
            brand_controls["hallucination_mitigation"] = True

        adapt_kwargs = {
            "column_mapping": column_mapping,
            "job_specification": job_specification,
            "recipe_specification": recipe_specification,
            "brand_controls": brand_controls,
        }
        # language_expansion is a top-level param in SDK >= 0.14; only send it
        # when the workspace actually contains non-English rows.
        if recipes.get("language_expansion") and any(
            (r.detected_language or "en") != "en" for r in rows
        ):
            adapt_kwargs["language_expansion"] = {
                "type": "translate", "languages": ["en"], "sample_rate": 1.0,
            }

        run_obj = client.datasets.adapt(dataset_id, **adapt_kwargs)
        log(f"Adaptive Data run started: {getattr(run_obj, 'run_id', 'unknown')}")

        import threading as _threading

        _stop_beat = _threading.Event()

        def _progress_beat():
            """Poll the run and write progress into the run log while we block."""
            last = None
            while not _stop_beat.wait(30):
                try:
                    st = client.datasets.get_status(dataset_id)
                    prog = getattr(st, "progress", None)
                    if prog is not None:
                        line = f"  progress: {getattr(prog, 'percent', None)}% ({getattr(prog, 'processed_rows', None)}/{getattr(prog, 'total_rows', None)} rows)"
                    else:
                        line = f"  status: {getattr(st, 'status', None)}"
                    if line != last:
                        _append_log(run_id, line)
                        last = line
                except Exception:
                    pass

        _beat = _threading.Thread(target=_progress_beat, daemon=True)
        _beat.start()
        try:
            client.datasets.wait_for_completion(dataset_id, timeout=5400)
        finally:
            _stop_beat.set()
        log("Adaptation run completed.")

        # Evaluation may lag completion — poll both surfaces for the scores.
        ev, grade_letters = None, ("", "")
        for attempt in range(30):
            dataset = client.datasets.get(dataset_id)
            summary = getattr(dataset, "evaluation_summary", None)
            if summary is None:
                try:
                    summary = client.datasets.get_evaluation(dataset_id)
                except Exception:
                    summary = None
            if summary is not None:
                score_after = _num(getattr(summary, "score_after", None))
                improvement = _num(getattr(summary, "improvement_percent", None))
                if score_after is not None or improvement is not None:
                    ev = summary
                    grade_letters = (
                        str(getattr(summary, "grade_before", "") or ""),
                        str(getattr(summary, "grade_after", "") or ""),
                    )
                    break
            log(f"  waiting for evaluation… ({(attempt + 1) * 10}s)")
            time.sleep(10)

        if ev is None:
            log("Evaluation not available yet — grades will be empty; the adapted rows are still applied.")
            grade_before = grade_after = improvement = None
        else:
            grade_before = _num(getattr(ev, "score_before", None))
            grade_after = _num(getattr(ev, "score_after", None))
            improvement = _num(getattr(ev, "improvement_percent", None))
            log(f"Evaluation: {grade_letters[0] or '?'} → {grade_letters[1] or '?'} "
                f"(score {grade_before} → {grade_after}, +{improvement}%)")

        # 5) Download the adapted dataset ------------------------------
        export = client.datasets.download(dataset_id, file_format="jsonl")
        path = str(ARTIFACT_DIR / f"adapted_{dataset_id}.jsonl")
        export.write_to_file(path)
        log(f"Downloaded adapted dataset → {path}")

        # 6) Parse and apply to our rows -------------------------------
        adapted: list[dict] = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    adapted.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if adapted:
            from collections import Counter as _C
            key_counts = _C(k for row in adapted for k in row.keys())
            log(f"Adaption output schema: {sorted(key_counts)}")
        mapped = [_map_live_row(a) for a in adapted]
        unmatched = sum(1 for m in mapped if not m.get("feedback_id"))
        if unmatched:
            log(f"WARNING: {unmatched} output rows could not be matched back to a feedback_id.")
        stats = _apply_rows(run_id, mapped, log)

        _finish_run(
            run_id, "succeeded",
            run_ref=str(dataset_id),
            rows_in=len(rows), rows_out=stats["applied"],
            duplicates_removed=stats["duplicates"], languages_normalized=stats["languages"],
            credits_estimate=credits,
            credits_consumed=getattr(dataset, "credits_consumed", None) or credits,
            grade_before=grade_before, grade_after=grade_after,
            improvement_percent=improvement,
            evaluation_note=(
                f"Adaption platform evaluation: {grade_letters[0] or '?'} → {grade_letters[1] or '?'} "
                f"(platform score {grade_before} → {grade_after} on a 0–10 scale, +{improvement}%)."
            ) if ev is not None else "Live Adaptive Data run — evaluation not returned.",
        )
    except Exception as exc:
        _append_log(run_id, f"LIVE run failed: {exc}\n{traceback.format_exc()}")
        _finish_run(run_id, "failed", evaluation_note=f"Live run failed: {exc}")


def _map_live_row(row: dict) -> dict:
    """
    Map one Adaption output row into our schema.

    An adapted row looks like:
      text                – the original feedback
      enhanced_prompt     – prompt wrapper containing the rephrased feedback
      enhanced_completion – markdown-fenced JSON: sentiment/score/topic/
                            complaint/urgency/recommended_action
      reasoning_trace     – the model's chain of thought
    """
    original = row.get("text") or ""
    enhanced_prompt = row.get("enhanced_prompt") or row.get("prompt") or ""
    completion = row.get("enhanced_completion") or row.get("completion") or ""
    reasoning = (
        row.get("reasoning_trace") or row.get("reasoning")
        or row.get("reasoning_content") or ""
    )

    # 1) the rephrased/normalized review, unwrapped from the prompt scaffolding
    adapted_text = _extract_feedback_content(enhanced_prompt) or original

    # 2) Adaption's own analysis, when the blueprint produced JSON
    parsed = _extract_json(completion)

    fb_id = None
    ctx = row.get("context")
    if isinstance(ctx, dict):
        fb_id = ctx.get("feedback_id")
    if not fb_id:
        for key in ("feedback_id", "id", "metadata_id"):
            if row.get(key) not in (None, ""):
                fb_id = row[key]
                break

    topic = parsed.get("topic")
    return {
        "feedback_id": int(fb_id) if fb_id is not None else None,
        "adapted_text": adapted_text,
        "sentiment": parsed.get("sentiment"),
        "score": parsed.get("score"),
        "topic": topic,
        "complaint": parsed.get("complaint") or None,
        "urgency": parsed.get("urgency"),
        "recommended_action": parsed.get("recommended_action"),
        "reasoning": reasoning,
        "detected_language": "en",
    }


def _extract_feedback_content(enhanced_prompt: str) -> str:
    """
    Pull the customer's words out of the generated prompt wrapper, e.g.
      Please analyze the following product feedback ... Feedback Content: "<text>"
    """
    import re as _re

    if not enhanced_prompt:
        return ""
    for pattern in (
        r'Feedback Content:\s*"([^"]+)"',
        r'Feedback:\s*"([^"]+)"',
        r'Content:\s*"([^"]+)"',
        r'"([^"]{20,})"',
    ):
        m = _re.search(pattern, enhanced_prompt, flags=_re.IGNORECASE | _re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    start, depth = None, 0
    for i, ch in enumerate(text):
        if ch == "{":
            if start is None:
                start = i
            depth += 1
        elif ch == "}" and start is not None:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start: i + 1])
                except json.JSONDecodeError:
                    start = None
    return {}
