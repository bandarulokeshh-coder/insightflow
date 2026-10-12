# InsightFlow — Intelligent Customer Feedback & Decision Platform

**Build Battle 2026 · AI × Web Hackathon · Frontend Arena**
Raw customer feedback → adapted, trustworthy data → prioritised decisions.

> **Built on the official `BuildBattle_2026_Customer_Feedback_Dataset.csv` (7,000 rows).**
> That dataset is **95.4% exact duplicates** (7,000 rows → 317 unique reviews), so
> InsightFlow collapses them at ingest, measures its classifier against the organizer's
> own labels (**99.1% agreement**), and runs the deduplicated rows through a **live
> Adaptive Data job** (290 rows · 3 credits), which the platform graded **E → B,
> 2.0 → 7.2 on its own 0–10 scale (+260%)** and returned with per-row recommended
> actions and reasoning traces. Full evidence in
> **[DATASET_FINDINGS.md](DATASET_FINDINGS.md)**.

### Verified live Adaption output

| Signal | Value |
|---|---|
| Platform grade | **E → B** (in-sample note below) |
| Platform score | 2.0 → 7.2 (0–10 scale, +260%) |
| Rows adapted | 290 of 290 matched, 0 unmatched |
| Output fields | `enhanced_prompt`, `enhanced_completion`, `reasoning_trace`, `persona_injection` |
| Per-row extras | `recommended_action`, `sentiment`, `urgency`, chain-of-thought |

Both scales are shown separately and never conflated: the live run displays the
**platform's 0–10 score with letter grades**, while the demo artifact displays
InsightFlow's **0–100 composite** (uniqueness 30 · diversity 20 · language 20 ·
clarity 20 · metadata 10).

> **The core idea:** generic AI gives generic insights. InsightFlow *adapts the data layer to each business* — its language, products and voice — using **Adaption**, and **proves the improvement** with before/after data-quality grades. Everything downstream (dashboard, priorities, reports) is computed from adapted data.

---

## How Adaption powers the pipeline (the judged integration)

```
Raw feedback (form · CSV import · sample data)
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  FEEDBACK REFINERY  ──  Adaption Adaptive Data API              │
│                                                                 │
│  1. datasets.upload_file(csv)          ingest raw feedback      │
│  2. datasets.adapt(..., estimate=True) credit quote (no blind)  │
│  3. datasets.adapt(recipes, blueprint) the run                  │
│       • deduplication        – dupes skew priority scoring      │
│       • prompt_rephrase      – messy text → analysable          │
│       • language_expansion   – Hinglish/Telugu/Tamil → English  │
│       • reasoning_traces     – the "why" behind each label      │
│       • blueprint            – per-business analyst persona     │
│  4. wait_for_completion() → evaluation_summary                  │
│       grade_before → grade_after        ★ measurable uplift     │
│  5. download() → adapted rows enter the analysis engine         │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
Analysis engine → Dashboard · Recommendations · Issue tracker · Reports
```

**Why this is meaningful, not a side-call:** every imported row passes through the refinery *before* any analysis. The blueprint injects a quick-commerce analyst persona and a strict JSON schema; reasoning traces power the "why" behind each recommendation; grade_before → grade_after proves the data improved. A generic sentiment tool analyses noise — InsightFlow analyses adapted, business-specific data.

**Code map:** `backend/app/adaption_service.py` (orchestration + live SDK path) · `backend/app/refinery_demo.py` (cached-artifact fallback, same output shape) · `backend/app/analysis.py` (sentiment/topic/priority engine).

### Modes
| Mode | When | What happens |
|---|---|---|
| `live` | `ADAPTION_API_KEY` set | Real Adaptive Data API run (upload → adapt → download) |
| `demo` | no key yet | Cached-artifact refinery replaying the identical pipeline locally, **0 credits** — clearly labelled `DEMO` everywhere |

`mode: "auto"` (the UI default) picks live when a key is present, else demo. **Flip to live by adding your key — no code changes.**

---

## Quickstart

```bash
# 1 ── Backend (FastAPI + SQLite, seeds itself from the official dataset:
#     7,000 rows → 317 unique after exact-dedup, ~3s on cold boot)
cd backend
pip install -r requirements.txt
cp .env.example .env          # add ADAPTION_API_KEY when you have it
uvicorn app.main:app --reload # → http://localhost:8000/docs

# 2 ── Frontend (Next.js 16 + Tailwind + Recharts)
cd ../frontend
npm install
npm run dev                   # → http://localhost:3000
```

Verify everything (API, analysis, full refinery run):
```bash
cd backend && python scripts/smoke_test.py
```

Regenerate the sample dataset (messy, multilingual, duplicate-laden — the refinery's raison d'être):
```bash
python backend/scripts/generate_sample_data.py
```

### Development notes (two traps worth knowing)

**1. Never run `next build` while `next dev` is running.** Both use the same
`.next` directory. A production build overwrites the dev server's module graph,
after which the server renders one version while the browser hydrates a cached
bundle — a hydration mismatch that *only* appears in the browser, never in the
build output. If it happens: stop the dev server, `rm -rf .next`, restart, then
**hard-reload** the browser (Cmd/Ctrl+Shift+R) so the cached client bundle is
discarded.

```bash
npm run dev:clean    # rm -rf .next && next dev — recovers from a poisoned cache
```

**2. A green build does not prove the UI works.** In this project a missing
PostCSS config silently dropped *every* Tailwind utility class while the build,
the type-check and all HTTP routes looked perfectly healthy. Verify rendered
pages, not just compiled ones:

```bash
npm run check    # tsc --noEmit
npm run verify   # loads all 6 routes in a real browser; fails on hydration
                 # errors, console errors, missing styles or an error overlay
```
(first run needs `npx playwright install chromium`)

### Deploying

**Live now:** 🔗 **https://insightflow-sand-gamma.vercel.app** (frontend) ·
📦 https://github.com/bandarulokeshh-coder/insightflow (repo)

| Piece | Host | Notes |
|---|---|---|
| Frontend | **Vercel** ✅ deployed | root dir `frontend`; set `NEXT_PUBLIC_API_URL` to the API origin |
| Backend | **Render** (blueprint ready) | `render.yaml` included — see below |
| Screenshots | `docs/screens/*.png` | captured at 1440px for the submission write-up |

**Why the backend is not on Vercel.** Vercel is serverless: read-only filesystem,
a ~10 s function ceiling and no long-lived process. The Feedback Refinery launches
Adaption jobs in daemon threads that write adapted rows back to SQLite, so it needs
a real persistent web service.

**Deploy the backend (Render, free tier):**
1. Open <https://dashboard.render.com/select-repo?repo=bandarulokeshh-coder/insightflow>
2. **Blueprint** → Render reads `render.yaml` automatically → **Apply**
3. Copy the resulting `https://insightflow-api-xxxx.onrender.com` URL

**Then wire the frontend to it:**
```bash
cd frontend
vercel env add NEXT_PUBLIC_API_URL production   # paste the Render URL
vercel --prod
```
When `NEXT_PUBLIC_API_URL` is set, `lib/api.ts` uses it directly and the
`localhost:8000` rewrite in `next.config.ts` disables itself — no code changes.

`backend/Dockerfile` (build from the repo root) serves Fly.io / Railway / any
Docker host. Cold-boot seeding takes ~3 s, so free-tier health checks pass.

CI: `.github/workflows/ci.yml` runs the 24-check backend smoke test plus the
frontend type-check and production build on every push.


---

## Feature map (vs the problem statement)

| § | Requirement | Where it lives |
|---|---|---|
| 1 | Feedback management: submit, CSV import, search, filter, organise, sample data | `app/feedback` · `routers/feedback.py` — imports the official 7,000-row CSV and flags 6,683 duplicates |
| 2 | AI analysis: sentiment, recurring topics, complaints, grouping; Adaption used meaningfully | `app/refinery` · `analysis.py` + `official.py` + `adaption_service.py` — **99.1% agreement** measured against the dataset's own labels |
| 3 | Analytics dashboard: metrics, sentiment distribution, top issues, trends, filters | `app/` (dashboard) · `routers/analytics.py` — incl. dedup headline, quality grades, confidence matrix |
| 4 | Recommendations: high-priority issues, actionable steps, explainable "why" | `app/recommendations` · `analysis.compute_recommendations` — severity-floored priority + per-card justification |
| 5 | Reports & tracking: save/track issues, export/share report, business-friendly | `app/issues`, `app/reports` · `routers/reports.py` |

**Priority score** = frequency (30%) + negative share (30%) + severity (40%), where severity floors each issue class (fraud 1.0 → product 0.3). Fraud ranks critical because it involves money loss, not because it is the largest bucket — and every card says so in plain language, with counts, trend and real quotes.

---

## Demo script (3 minutes)

1. **Hook (15s)** — "Businesses drown in feedback. We don't just analyse it — we *adapt* it."
2. **The mess (30s)** — `Feedback` page → import a messy CSV (or show the sample set): duplicates, Hinglish/Telugu, typos, emoji. Point at the noise.
3. **The Refinery (60s)** — `Adaption Refinery` → toggle recipes, hit **Run Refinery** → live log streams → **81.3 → 91.6 (+12.7% quality)** before a single insight was drawn. Show an adapted row: *"Naaku refund ravatam ledu…"* → *"My refund has not arrived…"* + its reasoning trace.
4. **Insights (40s)** — back to Dashboard: metrics, sentiment trend rising on Delivery, filter by sentiment/topic and watch it recompute.
5. **Decision (30s)** — `Recommendations`: top priority card with the *why* (counts + trend + urgency + quotes) → **Track as issue**.
6. **Report (15s)** — `Reports` → export `.md`; show it's business-ready.
7. **Close (10s)** — "Adaptive data layer → trustworthy insights → decisions. That's InsightFlow."

---

## Repo layout

```
insightflow/
├── sample_data/official_dataset.csv  # ★ 7,000 rows — the seed source (317 unique)
├── sample_data/feedback.csv          # 362 multilingual rows — fallback seed only
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, startup seed
│   │   ├── models.py  schemas.py   # SQLModel tables + Pydantic DTOs
│   │   ├── analysis.py             # sentiment · topics · priority · recommendations
│   │   ├── adaption_service.py     # ★ Adaption: live SDK path + orchestration
│   │   ├── refinery_demo.py        # ★ cached-artifact refinery (demo mode)
│   │   ├── seed.py  database.py
│   │   └── routers/                # feedback · analytics · adaption · issues · reports
│   └── scripts/                    # generate_sample_data.py · smoke_test.py
├── render.yaml                     # backend blueprint → Render
├── backend/Dockerfile              # build from repo root; Fly.io / Railway / Docker
├── .github/workflows/ci.yml        # smoke test + type-check + build on every push
└── frontend/
    ├── app/                        # dashboard · feedback · refinery · recommendations · issues · reports
    ├── components/                 # Sidebar · ui.tsx · charts.tsx (Recharts)
    └── lib/api.ts                  # typed API client
```

---

## Roadmap (if the clock allows)

- **AutoScientist stretch** — the official dataset is labelled and template-generated with only 37.6% content diversity, which is *precisely* the case for augmentation + training a small triage model on the adapted corpus. Add a UI toggle: *generic classifier* vs *model adapted to this corpus*, showing the measured lift on held-out rows.
- **Streaming analysis** for large imports; Postgres swap for concurrency.
- **Owner assignment + SLA timers** on tracked issues.
- **Live Adaption run in the demo** (small `max_rows`, estimate-first) once credits land.

---

_Built solo in 48 hours for Build Battle 2026 — “BUILD. ADAPT. SHIP. COMPETE.”_
