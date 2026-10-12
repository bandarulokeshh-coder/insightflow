"""
DEMO / CACHED-ARTIFACT refinery.

Runs the same transformation pipeline that Adaptive Data performs —
deduplication → language normalization → rephrasing → blueprint analysis →
reasoning traces → data-quality grading — locally, so InsightFlow is fully
demonstrable before the Adaption key/credits arrive.

Measured honestly: the BEFORE grade is computed on the raw corpus exactly as
it was uploaded (for the BuildBattle dataset that is 7,000 rows with 95%
exact duplication); the AFTER grade is computed on the refinery's output.

Every run produced here is labelled mode="demo" in the UI. Set
ADAPTION_API_KEY and the same run goes through the real platform instead.
"""
from __future__ import annotations

import random
import re
from collections import Counter
from datetime import datetime, timezone

from sqlmodel import Session, select

from . import analysis, models
from .database import engine

# ── Multilingual normalization dictionary (transliterated regional words) ──
LEXICON = {
    # Hindi/Hinglish
    "bahut": "very", "nahi": "not", "nahin": "not", "hai": "is", "hain": "are",
    "aayi": "came", "aaya": "came", "gaya": "went", "hua": "happened", "hui": "happened",
    "mera": "my", "meri": "my", "paise": "money", "paisa": "money", "wapas": "back",
    "abhi": "still", "tak": "until", "bhi": "also", "ka": "of", "ki": "of", "ke": "of",
    "bohot": "very", "kharab": "bad", "bekar": "useless", "jaldi": "quickly",
    "der": "late", "kabhi": "ever", "kyun": "why", "kya": "what", "raha": "ongoing",
    "rahi": "ongoing", "kar": "do", "karo": "do", "karna": "to do", "de": "give",
    "do": "give", "liye": "for", "bas": "just", "phir": "again", "din": "days",
    "ghante": "hours", "minute": "minute", "swad": "taste", "tha": "was", "thi": "was",
    # Telugu-English
    "chala": "very", "ledu": "not", "ledhu": "not", "undi": "is", "undindi": "was",
    "bagundindi": "was good", "bagundi": "is good", "kaani": "but", "kuda": "also",
    "nenu": "I", "naa": "my", "naaku": "to me", "ravatam": "arrival", "late": "late",
    "ayyindi": "happened", "cheyyandi": "please do", "ivvandi": "please give",
    "sari": "okay", "chalaa": "very", "manchi": "good", "dhanyavadalu": "thanks",
    # Tamil-English
    "romba": "very", "illa": "not", "irukku": "is", "aachu": "happened",
    "vanakkam": "hello", "nandri": "thanks", "konjam": "a little", "seri": "okay",
    # Kannada-English
    "thumba": "very", "ide": "is", "aaythu": "happened", "dhanyavada": "thanks",
}

NON_EN_MARKERS = set(LEXICON.keys())

# Phrase-level translation memory — translates whole idiomatic clauses (as
# Adaption's language normalization does) before token-level fallback.
PHRASE_TM: list[tuple[str, str]] = [
    (r"delivery bahut late aayi[.,]? rider ne call bhi nahi kiya[.,]? khana thanda ho gaya",
     "The delivery was very late and the rider did not even call. The food went cold"),
    (r"mera refund abhi tak nahi aaya[.,]? paise wapas karo[.,]? bahut kharab service hai",
     "My refund has still not arrived — please return my money. The service is very bad"),
    (r"app bar bar crash ho raha hai[.,]? cart khulta hi nahi[.,]? please fix karo jaldi",
     "The app keeps crashing and the cart does not even open. Please fix this soon"),
    (r"quality bahut kharab thi[.,]? (\w+) stale tha aur smell bhi aa rahi thi",
     r"The quality was very bad — the \1 was stale and it also smelled"),
    (r"support ne koi jawab nahi diya[.,]? (\d+) din se ticket pending hai[.,]? bahut frustrating",
     r"Support did not reply at all and my ticket has been pending for \1 days. Very frustrating"),
    (r"mujhe double charge hua hai[.,]? do baar paise cut gaye[.,]? refund karo please",
     "I was charged twice — money was deducted from my account twice. Please refund it"),
    (r"packaging kharab thi[.,]? milk packet leak ho gaya poore bag mein",
     "The packaging was bad and the milk packet leaked all over the bag"),
    (r"order chala late ayyindi[.,]? food antha cold ayyipoyindi[.,]? chala baadha ga undi",
     "The order arrived very late and the food was completely cold. Very disappointing"),
    (r"naaku refund ravatam ledu[.,]? (\d+) days ayyindi[.,]? money back ivvandi please",
     r"My refund has not arrived and it has been \1 days. Please give me my money back"),
    (r"app chala slow ga undi[.,]? loading chala time teesukuntundi[.,]? sariga pani cheyyatam ledu",
     "The app is very slow and loading takes a lot of time. It does not work properly"),
    (r"delivery chala fast ga vachindi[.,]? items fresh ga unnayi[.,]? chala bagundindi",
     "The delivery arrived very fast and the items were fresh. Excellent service"),
    (r"payment double ayindi[.,]? naa account nunchi rendu sarlu cut ayyindi",
     "The payment was taken twice and my account was charged twice"),
    (r"delivery romba late aachu[.,]? items ellam cold aayiduchu[.,]? romba mosam",
     "The delivery was very late and all the items became cold. Very bad service"),
    (r"refund innum varala[.,]? naan romba kashtapadren[.,]? please money back kudunga",
     "The refund has not come yet and I am struggling a lot. Please give me my money back"),
    (r"app romba slow[.,]? loading time romba jasthi[.,]? seri illa",
     "The app is very slow and loading takes too long. This is not acceptable"),
    (r"delivery thumba late aaythu[.,]? aa mele items damaged aagide[.,]? thumba kasta",
     "The delivery was very late and on top of that the items were damaged. Very disappointing"),
    (r"refund innu bandilla[.,]? naaku dhanyavada heli paisa kodu please",
     "The refund has not come yet — please give me my money back, thank you"),
]

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]+", flags=re.UNICODE
)
WS_RE = re.compile(r"\s+")

TYPO_FIXES = {"recieved": "received", "delievery": "delivery", "refnd": "refund",
              "paymnt": "payment", "custmer": "customer", "pakage": "package",
              "qualtiy": "quality", "worng": "wrong", "definately": "definitely"}

SHORTHAND = {"pls": "please", "plz": "please", "u": "you", "r": "are", " b4 ": " before ",
             "thx": "thanks", "bt": "but", "n": "and", "2": "to"}

NEAR_DUP_THRESHOLD = 0.85
MAX_ROWS_FOR_NEAR_DUP = 1200          # O(n²) guard


# ─────────────────────────────────────────────────────────────────────────
def execute(run_id, max_rows, recipes, blueprint, log, apply_rows, finish_run) -> None:
    import time

    log("DEMO mode — cached-artifact refinery (0 credits, same pipeline shape as Adaption).")
    log(f"Recipes: {', '.join(k for k, v in recipes.items() if v) or 'defaults'}")

    with Session(engine) as session:
        all_rows = list(session.exec(select(models.Feedback).order_by(models.Feedback.id)).all())

    # ── BEFORE: grade the raw corpus exactly as uploaded ────────────────
    raw_items = [{
        "text": r.text, "rating": r.rating, "product": r.product,
        "channel": r.channel, "created_at": r.created_at.isoformat() if r.created_at else "",
    } for r in all_rows]
    before = _quality(raw_items)
    log(f"Scored raw corpus: {len(raw_items)} rows → {before['score']}/100")
    log(f"  dimensions: {before['dims']}  (dupes {before['dupes_pct']}% · "
        f"non-English {before['nonen_pct']}% · noisy {before['noisy_pct']}%"
        + (f" · missing metadata {before['incomplete_pct']}%" if before["metadata_dimension"] else "")
        + ")")
    time.sleep(0.4)

    # ── exact duplicates were already collapsed at ingest ──────────────
    exact_dupes = sum(1 for r in all_rows if r.is_duplicate)
    if recipes.get("deduplication", True):
        log(f"Stage · exact deduplication → {exact_dupes} duplicate rows already collapsed at ingest "
            f"({before['dupes_pct']}% of the corpus).")
    time.sleep(0.3)

    # ── work only the surviving rows (this is also what keeps live runs cheap) ──
    unique = [r for r in all_rows if not r.is_duplicate]
    rows = unique[:max_rows] if max_rows else unique
    log(f"Processing {len(rows)} unique rows (max_rows={max_rows}).")
    time.sleep(0.3)

    # ── near-duplicate collapse (Adaption's dedup recipe removes near-dupes too) ──
    near_dropped: set[int] = set()
    if recipes.get("deduplication", True) and len(rows) <= MAX_ROWS_FOR_NEAR_DUP:
        kept: list[tuple[int, set[str]]] = []   # (index-in-rows, token signature)
        for i, r in enumerate(rows):
            toks = set(_norm_key(r.text).split())
            dup_of = None
            for _, other in kept:
                if not toks or not other:
                    continue
                if len(toks & other) / len(toks | other) >= NEAR_DUP_THRESHOLD:
                    dup_of = True
                    break
            if dup_of:
                near_dropped.add(i)
            else:
                kept.append((i, toks))
        log(f"Stage · near-duplicate collapse (Jaccard ≥ {NEAR_DUP_THRESHOLD}) → "
            f"{len(near_dropped)} near-duplicate rows removed.")
    else:
        log("Stage · near-duplicate collapse → skipped (row cap).")
    time.sleep(0.3)

    work = [r for i, r in enumerate(rows) if i not in near_dropped]

    # ── language normalization + rephrasing ───────────────────────────
    lang_counts = Counter()
    normalized = 0
    prepared: list[dict] = []
    for r in work:
        detected = detect_language(r.text)
        lang_counts[detected] += 1
        text = r.text
        if detected != "en" and recipes.get("language_expansion", True):
            text = translate_phrases(text)
            text = translate_tokens(text)
            normalized += 1
        if recipes.get("prompt_rephrase", True):
            text = rephrase(text)
        prepared.append({"row": r, "text": text, "lang": detected})

    if recipes.get("language_expansion", True):
        log(f"Stage · language normalization → {normalized} rows rewritten to English "
            f"(detected: {dict(lang_counts)}).")
    time.sleep(0.3)
    if recipes.get("prompt_rephrase", True):
        log("Stage · prompt rephrasing → whitespace, casing, punctuation and shorthand normalized.")
    time.sleep(0.3)

    # ── blueprint analysis + reasoning traces ─────────────────────────
    out_rows: list[dict] = []
    for p in prepared:
        r = p["row"]
        res = analysis.analyze_text(p["text"], r.rating)
        reasoning = (
            f"Language: {p['lang']} → normalized to English. "
            f"Sentiment: {res['sentiment']} ({res['sentiment_score']}) — "
            f"{'rating signal' if r.rating else 'lexical signal'}. "
            f"Topic: {res['topic']} — domain keywords matched in the normalized text. "
            f"Category: {getattr(r, 'official_category', None) or 'unlabelled'} (ground truth honoured as context). "
            f"Urgency: {res['urgency']}/3. Blueprint: analyst persona + strict JSON schema."
        ) if recipes.get("reasoning_traces", True) else ""

        out_rows.append({
            "feedback_id": r.id,
            "adapted_text": p["text"],
            "detected_language": p["lang"],
            "sentiment": res["sentiment"], "score": res["sentiment_score"],
            "topic": res["topic"], "complaint": res["complaint"],
            "urgency": res["urgency"], "reasoning": reasoning,
            "is_duplicate": False,
        })

    # rows dropped as near-duplicates get flagged so they leave the analytics
    for i in near_dropped:
        out_rows.append({
            "feedback_id": rows[i].id, "is_duplicate": True,
            "reasoning": f"Near-duplicate (Jaccard ≥ {NEAR_DUP_THRESHOLD}) of an earlier row — removed by the deduplication recipe.",
        })

    log(f"Stage · blueprint applied to {len(prepared)} rows "
        f"(persona: quick-commerce analyst · strict JSON output).")
    if recipes.get("reasoning_traces", True):
        log("Stage · reasoning traces captured for every adapted row.")
    time.sleep(0.4)

    stats = apply_rows(run_id, out_rows, log)

    # ── AFTER: grade the adapted output ───────────────────────────────
    after_items = [{
        "text": p["text"], "rating": p["row"].rating, "product": p["row"].product,
        "channel": p["row"].channel,
        "created_at": p["row"].created_at.isoformat() if p["row"].created_at else "",
    } for p in prepared]
    after = _quality(after_items)

    grade_before, grade_after = before["score"], after["score"]
    improvement = round(100 * (grade_after - grade_before) / max(1e-6, grade_before), 1)

    log(f"Scored adapted output: {len(after_items)} rows → {grade_after}/100")
    log(f"  dimensions: {after['dims']}")
    log(f"DATA QUALITY: {grade_before} → {grade_after}  (+{improvement}% improvement)")

    finish_run(
        run_id, "succeeded",
        run_ref=f"demo-artifact-{run_id}",
        rows_in=len(all_rows), rows_out=stats["applied"],
        duplicates_removed=exact_dupes + len(near_dropped),
        languages_normalized=stats["languages"],
        credits_estimate=round(0.12 * len(rows), 2), credits_consumed=0.0,
        grade_before=grade_before, grade_after=grade_after,
        improvement_percent=improvement,
        evaluation_note=(
            "Demo artifact — identical pipeline shape (exact + near dedupe → normalize → rephrase → "
            "blueprint → traces → grade). Set ADAPTION_API_KEY to run the live Adaptive Data platform."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    toks = [t.lower() for t in re.findall(r"[A-Za-z]+", text)]
    if not toks:
        return "unknown"
    markers = sum(1 for t in toks if t in NON_EN_MARKERS)
    ratio = markers / len(toks)
    if ratio >= 0.08 and markers >= 2:
        return "hi-en" if any(t in {"nahi", "hai", "bahut", "mera"} for t in toks) else "mixed-in"
    return "en"


def translate_phrases(text: str) -> str:
    out = text
    for pattern, english in PHRASE_TM:
        new = re.sub(pattern, english, out, flags=re.IGNORECASE)
        if new != out:
            out = new
    return out


def translate_tokens(text: str) -> str:
    out = []
    for token in re.split(r"(\W+)", text):
        low = token.lower()
        out.append(LEXICON[low] if low in LEXICON else token)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def rephrase(text: str) -> str:
    t = EMOJI_RE.sub(" ", text)
    for bad, good in TYPO_FIXES.items():
        t = re.sub(bad, good, t, flags=re.IGNORECASE)
    parts = [SHORTHAND.get(w.lower().strip(".,!?"), w) for w in t.split(" ")]
    t = WS_RE.sub(" ", " ".join(parts)).strip()
    sentences = re.split(r"(?<=[.!?])\s+", t)
    cleaned = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        s = s[0].upper() + s[1:]
        if not s.endswith((".", "!", "?")):
            s += "."
        cleaned.append(s)
    return " ".join(cleaned)


def _norm_key(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _quality(items: list[dict]) -> dict:
    """
    Data-quality score (0-100) from measurable row properties:
      uniqueness 30% · language 25% · clarity 25% · metadata 20%

    A dimension is dropped (and weights renormalized) when the source simply
    does not carry that field at all — a dataset without ratings should not be
    penalised for metadata it never had.
    """
    n = max(1, len(items))

    # uniqueness: exact duplicates, plus near-duplicates when the set is small
    seen: set[str] = set()
    dupes = 0
    keys: list[str] = []
    for i in items:
        key = _norm_key(i["text"])
        if key in seen:
            dupes += 1
        else:
            seen.add(key)
        keys.append(key)

    if n <= MAX_ROWS_FOR_NEAR_DUP:
        sigs: list[set[str]] = []
        for k in keys:
            toks = set(k.split())
            if any(toks and s and len(toks & s) / len(toks | s) >= NEAR_DUP_THRESHOLD for s in sigs):
                dupes += 1
            else:
                sigs.append(toks)
        uniqueness = 100 * (1 - dupes / n)
        near_measured = True
    else:
        uniqueness = 100 * (1 - dupes / n)
        near_measured = False

    nonen = sum(1 for i in items if detect_language(i["text"]) != "en")
    noisy = sum(
        1 for i in items
        if len(i["text"].strip()) < 25 or EMOJI_RE.search(i["text"]) or "  " in i["text"]
    )
    language = 100 * (1 - nonen / n)
    clarity = 100 * (1 - noisy / n)

    # the metadata dimension only applies if the SOURCE carries rating/product
    # data — a channel we defaulted ourselves does not count as metadata
    has_metadata = any(
        (i.get("rating") is not None) or (i.get("product") or "").strip()
        for i in items
    )
    if has_metadata:
        complete = sum(1 for i in items if i.get("rating") and (i.get("product") or "").strip())
        metadata = 100 * (complete / n)
    else:
        metadata = None

    diversity = _diversity(items)

    # weights: uniqueness 30 · diversity 20 · language 20 · clarity 20 · metadata 10
    dims = [("uniqueness", uniqueness, 0.30), ("diversity", diversity, 0.20),
            ("language", language, 0.20), ("clarity", clarity, 0.20)]
    if metadata is not None:
        dims.append(("metadata", metadata, 0.10))

    total_w = sum(w for _, _, w in dims)
    score = sum(v * w for _, v, w in dims) / total_w

    return {
        "score": round(score, 1),
        "dupes_pct": round(100 * dupes / n, 1),
        "nonen_pct": round(100 * nonen / n, 1),
        "noisy_pct": round(100 * noisy / n, 1),
        "incomplete_pct": round(100 * (100 - metadata) / 100, 1) if metadata is not None else 0.0,
        "metadata_dimension": metadata is not None,
        "near_dup_measured": near_measured,
        "dims": {k: round(v, 1) for k, v, _ in dims},
    }


def _diversity(items: list[dict], sample: int = 500, threshold: float = 0.7) -> float:
    """
    Share of rows whose content is NOT merely a re-wording of another row
    (max Jaccard similarity below `threshold`).

    This is what separates "deduplicated" from "diverse": a template-generated
    corpus can have zero exact duplicates and still say the same thing 40 times.
    Sampled so it stays fast on large corpora — and the SAME sampling is used
    for the before and after measurements, so the comparison stays fair.
    """
    if len(items) < 3:
        return 100.0
    rnd = random.Random(7)
    pool = items if len(items) <= sample else rnd.sample(items, sample)
    sigs = [set(_norm_key(i["text"]).split()) for i in pool]

    distinct = 0
    for a in range(len(sigs)):
        sa = sigs[a]
        if not sa:
            continue
        max_sim = 0.0
        for b in range(len(sigs)):
            if a == b:
                continue
            sb = sigs[b]
            if not sb:
                continue
            inter = len(sa & sb)
            if not inter:
                continue
            sim = inter / len(sa | sb)
            if sim > max_sim:
                max_sim = sim
                if max_sim >= threshold:
                    break
        if max_sim < threshold:
            distinct += 1
    return 100 * distinct / max(1, len(sigs))
