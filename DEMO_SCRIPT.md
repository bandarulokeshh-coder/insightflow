# 🎬 InsightFlow — 3-Minute Demo Script

**Everything below is verifiable in the running app. Numbers are measured, not claimed.**

---

## Before you start (checklist)

- [ ] Backend running: `cd backend && uvicorn app.main:app --reload`
- [ ] Frontend running: `cd frontend && npm run dev`
- [ ] A **live Refinery run already exists** in history (see *Run history* on the Refinery page) — **do not run the live refinery in front of judges, it takes ~14 minutes.** Use it from history, or run the mode switch to `demo` if you want a live-feeling run that finishes in seconds.
- [ ] Browser zoom ~110%, one tab, dashboard open
- [ ] Backup: a screen recording of the whole flow (laptops fail in demos)

---

## The 3 minutes

### 0:00 — Hook (15s)
> "Businesses drown in customer feedback. The usual response is a sentiment dashboard. We did something different: **we don't just analyse the data — we adapt it first.** And we can prove the difference."

### 0:15 — The dataset's dirty secret (35s)
*(Dashboard. Scroll to the **Dataset** card.)*
> "This is the official BuildBattle dataset: **7,000 rows**. Watch what happens when we ingest it honestly — **6,683 of those rows are exact duplicates. Only 317 unique reviews exist.**"

*(Point at the numbers.)*
> "95.4% of this file is copy-paste. Every frequency metric on a naive dashboard is inflated **22×**. That's not a data problem — it's a tooling problem. So deduplication is the first thing the pipeline does."

### 0:50 — Measured, not claimed (30s)
*(Scroll to **Category agreement**.)*
> "Most AI demos *claim* accuracy. This dataset ships with ground-truth labels, so we measured ours: **99.1% agreement** — 314 of 317 rows match the organizer's own category labels."

*(Click **Show confusion matrix**.)*
> "Here's the full picture, per class — including the three rows we get wrong. That's the point of a confusion matrix: it's not a marketing number."

### 1:20 — The Refinery (50s)
*(Go to **Adaption Refinery**.)*
> "This is the Adaption integration — the data layer, not a side call. Every run: upload → free credit estimate → adapt with recipes → download → analyse."

*(Open the completed **live run** from history.)*
> "This is a **real Adaptive Data run** — 290 rows, 3 credits, ~14 minutes. Recipes: deduplication, prompt rephrasing, reasoning traces, plus our analyst blueprint that forces strict-JSON output."

*(Point at the grade.)*
> "**Data quality 47.3 → 86.1, up 82%** — and look at the dimensions: uniqueness went 4.5 → 100, and diversity is still only 37.6%."

*(Pause here — this is the differentiator.)*
> "We're showing you a number that isn't flattering. Even after dedup, two-thirds of this corpus is the same sentence re-worded — it's template-generated. That's exactly what augmentation and model training are for, and we surface it instead of hiding it behind a 100/100."

### 2:10 — Decision (30s)
*(Go to **Recommendations**.)*
> "Now the payoff. Priorities with a severity floor — fraud isn't ranked by volume, it's ranked by risk: **critical**."

*(Hover the why-line.)*
> "'31 items, 42% negative, rising trend, severity floor applied — money loss and safety.' Every claim traces back to real rows."

*(Click **Track as issue** → Issues page.)*
> "One click turns it into a trackable issue."

### 2:40 — Honest gaps + close (20s)
*(Dashboard → Trend panel.)*
> "One last thing. This dataset has no timestamps — so we **refuse to draw a trend line** for it. Here's the empty state that says so."

*(Click **+ Import dated sample feed**, wait 2s, chart appears.)*
> "One click imports a dated, multilingual feed — now trends light up, and the language-normalization stage has real work to do."

> "**Adaptive data layer → trustworthy insights → decisions.** Everything you saw is either measured, or labelled as sample data. That's InsightFlow."

---

## Likely judge questions — prepared answers

**"Isn't 99.1% just tuned on the test set?"**
> "Yes — it's in-sample agreement, and we say so in the API response and the README. The honest claim is 'we measured our classifier against the organizer's labels.' The rule weights are tuned on the 320 unique reviews; a held-out split is the next step, and AutoScientist is how we'd get there."

**"Why is Product Feedback not top priority when it's the biggest bucket?"**
> "Because 166 of its 183 rows are *praise*. Volume without severity would rank 'the product is great' above fraud. That's why severity floors the score, and why the card prints the reason."

**"Is the demo refinery real?"**
> "No — and it never pretends to be. Every demo run is labelled `demo` in the UI and the API. The live run in history is the real Adaptive Data API; the demo artifact exists so the product stays demonstrable without burning credits."

**"What did Adaption actually do that a normal LLM call couldn't?"**
> "Three things: it deduplicated the data layer itself (95% of the corpus), it rephrased and normalized it, and it returned **measured quality grades plus reasoning traces** that power our recommendation 'why' lines. We also inject a per-business blueprint so the outputs follow our schema."

**"What's next?"**
> "Augmentation on the 37.6%-diverse corpus, then AutoScientist to train a triage model — the dataset is labelled and template-heavy, which is exactly the case training is for."

---

## Do NOT do in the demo

- ❌ Click **Run Refinery** in live mode (14 minutes — you'll stand there in silence)
- ❌ Claim 99.1% generalises to unseen data
- ❌ Claim the demo-artifact grades are Adaption's output — say "this run is labelled demo"
- ❌ Fabricate a trend line for a dataset without timestamps
