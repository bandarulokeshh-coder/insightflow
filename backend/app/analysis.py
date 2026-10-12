"""
InsightFlow analysis engine.

Works fully offline (rule-based) so the app is demonstrable with zero API
keys. Everything here operates on the *adapted* text when available —
that is the point of the Feedback Refinery: better data in, better
insights out.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Optional

# ─────────────────────────────────────────────────────────────────────
# Sentiment lexicon
# ─────────────────────────────────────────────────────────────────────
POSITIVE = {
    "love", "loved", "great", "excellent", "amazing", "awesome", "perfect",
    "fantastic", "good", "best", "happy", "fast", "helpful", "smooth",
    "recommend", "brilliant", "wonderful", "superb", "thanks", "thank",
    "polite", "friendly", "quick", "refunded", "resolved", "fresh", "tasty",
    "value", "worth", "reliable", "impressed", "responsive", "seamless",
    "convenient", "affordable", "clean", "nice", "brilliant",
}

NEGATIVE = {
    "bad", "terrible", "awful", "worst", "horrible", "poor", "slow", "late",
    "broken", "crash", "crashes", "crashed", "bug", "bugs", "buggy", "fail",
    "failed", "fails", "failing", "damaged", "cold", "stale", "rude", "unhelpful",
    "expensive", "overpriced", "charge", "charged", "wrong", "missing", "never",
    "unacceptable", "disappointed", "disappointing", "angry", "frustrated",
    "frustrating", "useless", "waste", "ignored", "delay", "delayed", "spilled",
    "leaked", "leaking", "error", "errors", "glitch", "glitchy", "stuck",
    "hung", "unresponsive", "cancelled", "denied", "ripped", "scam", "freeze",
    "freezes", "lag", "laggy", "confusing", "hidden", "surge", "overcharged",
    "twice", "lying", "misleading", "rotten", "undercooked", "burnt", "hacked",
}

NEGATORS = {"not", "no", "never", "hardly", "barely", "isn't", "wasn't", "don't", "didn't"}

URGENCY_WORDS = {
    "refund": 2, "fraud": 3, "fraudulent": 3, "scam": 3, "unauthorized": 3,
    "double": 2, "twice": 2, "overcharged": 2, "never received": 3,
    "never arrived": 3, "safety": 3, "injury": 3, "allergic": 3, "stolen": 3,
    "leak": 2, "leaked": 2, "hacked": 3, "bank": 2, "cancel": 1, "escalate": 2,
    "lawyer": 3, "consumer court": 3, "urgent": 2, "immediately": 1, "days": 1,
    "weeks": 2, "still waiting": 2, "no response": 2,
}

# ─────────────────────────────────────────────────────────────────────
# Topic taxonomy — keyword → topic, weighted
# ─────────────────────────────────────────────────────────────────────
TOPIC_KEYWORDS: dict[str, dict[str, int]] = {
    "Delivery": {
        "delivery": 3, "deliver": 3, "delivered": 2, "late": 2, "rider": 3,
        "driver": 2, "arrived": 2, "cold": 2, "order": 1, "waiting": 2,
        "eta": 3, "minutes": 1, "hours": 2, "courier": 3, "shipment": 3,
        "shipping": 3, "parcel": 2, "tracking": 2, "spilled": 2, "spill": 2,
    },
    "App Bug": {
        "crash": 3, "crashes": 3, "crashed": 3, "bug": 3, "bugs": 3, "buggy": 3,
        "glitch": 3, "error": 2, "freeze": 2, "freezes": 2, "stuck": 2, "update": 2,
        "app": 1, "login": 3, "logged": 2, "screen": 2, "blank": 2, "version": 2,
        "force": 2, "closes": 2, "cart": 2, "checkout": 2, "reinstall": 3,
    },
    "Refund": {
        "refund": 4, "money": 2, "back": 1, "credited": 2, "reimburse": 4,
        "cancelled": 2, "cancel": 2, "return": 2, "returned": 1, "deducted": 2,
        "wallet": 2, "pending": 2, "reversal": 3,
    },
    "Billing": {
        "charge": 3, "charged": 4, "overcharged": 4, "billing": 4, "invoice": 3,
        "price": 2, "pricing": 2, "expensive": 2, "surge": 3, "fee": 3,
        "fees": 3, "subscription": 3, "renewal": 3, "auto-renew": 3, "hidden": 3,
        "double": 3, "twice": 3, "upi": 2, "payment": 2, "gst": 2,
    },
    "Support": {
        "support": 4, "agent": 3, "customer care": 4, "helpline": 4, "chat": 2,
        "bot": 2, "email": 2, "respond": 3, "response": 2, "ignored": 3,
        "rude": 3, "unhelpful": 3, "escalate": 3, "ticket": 3, "call": 2,
        "representative": 3, "hold": 2, "transferred": 3,
    },
    "Product Quality": {
        "quality": 3, "stale": 3, "fresh": 2, "rotten": 2, "damaged": 3,
        "damage": 3, "broken": 3, "taste": 2, "tasty": 2, "undercooked": 3,
        "burnt": 3, "expired": 4, "smell": 2, "smelly": 3, "defective": 4,
        "faulty": 3, "duplicate": 2, "counterfeit": 4, "wrong item": 3,
    },
    "Packaging": {
        "package": 3, "packaging": 4, "packed": 3, "seal": 3, "sealed": 2,
        "leak": 3, "leaked": 4, "leaking": 4, "box": 2, "wrapped": 2,
        "container": 2, "torn": 3, "spilled": 3, "spill": 3,
    },
    "App UX": {
        "ui": 4, "ux": 4, "interface": 3, "design": 2, "slow": 2, "confusing": 3,
        "navigation": 3, "search": 2, "filter": 2, "font": 2, "layout": 2,
        "cluttered": 3, "dark mode": 3, "accessibility": 3, "flow": 2,
    },
    "Performance": {
        "lag": 4, "laggy": 4, "slow": 3, "loading": 3, "loads": 2, "battery": 3,
        "drain": 3, "heating": 3, "memory": 2, "performance": 3, "hang": 3,
        "hangs": 3, "minutes to open": 3, "timeout": 3,
    },
    "Payments": {
        "payment failed": 4, "payment": 3, "upi": 3, "card": 3, "gateway": 3,
        "otp": 3, "transaction": 3, "declined": 3, "failed": 2, "netbanking": 3,
        "cod": 2, "cash": 1,
    },
}

TOPIC_ACTIONS = {
    # official BuildBattle taxonomy
    "Fraud and Scam": "Stand up a seller-verification and escrow flow: auto-flag requests for off-platform payment, hold payouts on fraud reports, and run a same-day refund review for confirmed cases.",
    "Customer Service": "Introduce a first-response SLA with escalation after one contact, route repeat contacts to senior agents, and measure resolution rate per agent weekly.",
    "Operational Issues": "Instrument the order journey end-to-end (site, payment, fulfilment) and publish status updates proactively — most operational complaints are about silence, not the fault itself.",
    "Product Feedback": "Feed recurring product observations into the roadmap review, tag them against SKUs, and close the loop with customers when an item they flagged is fixed.",
    "Delivery": "Fix delivery SLAs: tighten ETA promises, audit late-night routing, and add proactive delay notifications before the customer has to ask.",
    "App Bug": "Ship a hotfix release addressing crash and login reports, then add crash telemetry with alerts so regressions are caught in hours, not weeks.",
    "Refund": "Automate refunds for orders cancelled by the platform and set an SLA (<48h) with status notifications — most refund complaints are about silence, not money.",
    "Billing": "Audit pricing pages and invoices for hidden/inconsistent charges; issue goodwill credits where customers were overcharged and simplify the fee wording.",
    "Support": "Add real-time response SLA tracking, route repeat contacts to senior agents, and publish a callback option instead of holding queues.",
    "Product Quality": "Trigger QC audits on the flagged SKUs/vendors and add a pre-dispatch quality checklist for perishable and fragile items.",
    "Packaging": "Revise packaging for liquids and fragile items (double-seal + tamper tape) and add an in-transit spill complaint funnel that credits customers instantly.",
    "App UX": "Run a focused usability pass on search, filters and checkout; instrument drop-off points and A/B test the top 3 friction spots.",
    "Performance": "Profile cold-start and list rendering; introduce caching and skeleton loaders, and set performance budgets in CI.",
    "Payments": "Improve the payment retry UX: keep the cart on failure, add UPI fallback and clear error codes, and reconcile pending transactions nightly.",
    "General": "Review the recurring themes with the owning team and define a measurable weekly target for reduction.",
}

# Domain severity prior: some issue classes carry inherent risk regardless of
# volume. Fraud involves money loss and safety, so it must outrank a larger
# bucket of low-severity product observations. This floors the urgency term.
SEVERITY_PRIOR: dict[str, float] = {
    "Fraud and Scam": 1.00, "Operational Issues": 0.70, "Customer Service": 0.50,
    "Product Feedback": 0.30,
    "Payments": 0.80, "Refund": 0.70, "Billing": 0.70, "App Bug": 0.70,
    "Product Quality": 0.70, "Delivery": 0.60, "Packaging": 0.50, "Support": 0.50,
    "App UX": 0.40, "Performance": 0.40, "General": 0.30,
}

TITLES: dict[str, str] = {
    "Fraud and Scam": "Tackle fraud and scam reports",
    "Customer Service": "Improve customer-service responsiveness",
    "Operational Issues": "Resolve operational and fulfilment issues",
    "Product Feedback": "Act on recurring product feedback",
    "General": "Review recurring general complaints",
}

_WORD_RE = re.compile(r"[a-z']+")
_SENT_RE = re.compile(r"[^.!?\n]+[.!?]?")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def score_sentiment(text: str, rating: Optional[float] = None) -> tuple[str, float]:
    """Return (label, score in -1..1). Rating wins when present."""
    toks = _tokens(text)
    pos = sum(1 for t in toks if t in POSITIVE)
    neg = sum(1 for t in toks if t in NEGATIVE)
    # negation flip: "not good"
    for i, t in enumerate(toks[:-1]):
        if t in NEGATORS and toks[i + 1] in POSITIVE:
            pos -= 1
            neg += 1
    total = pos + neg
    lex_score = 0.0 if total == 0 else (pos - neg) / total

    rating_score = None
    if rating is not None:
        rating_score = max(-1.0, min(1.0, (rating - 3) / 2))

    if rating_score is not None and total < 3:
        score = rating_score
    elif rating_score is not None:
        score = 0.6 * rating_score + 0.4 * lex_score
    else:
        score = lex_score

    if score > 0.15:
        label = "positive"
    elif score < -0.15:
        label = "negative"
    else:
        label = "neutral"
    return label, round(score, 3)


def classify_topic(text: str) -> str:
    toks = _tokens(text)
    lowered = text.lower()
    scores: Counter = Counter()
    for topic, kws in TOPIC_KEYWORDS.items():
        for kw, weight in kws.items():
            if " " in kw:
                if kw in lowered:
                    scores[topic] += weight
            elif kw in toks:
                scores[topic] += weight
    if not scores:
        return "General"
    return scores.most_common(1)[0][0]


def extract_complaint(text: str) -> Optional[str]:
    """Pull the most negative clause out of the feedback."""
    best, best_score = None, 0
    for sentence in _SENT_RE.findall(text):
        s = sentence.strip()
        if len(s) < 8:
            continue
        toks = _tokens(s)
        score = sum(1 for t in toks if t in NEGATIVE) - sum(1 for t in toks if t in POSITIVE)
        if score > best_score:
            best, best_score = s, score
    return best


def urgency_of(text: str) -> int:
    lowered = text.lower()
    toks = _tokens(text)
    score = 0
    for phrase, weight in URGENCY_WORDS.items():
        if " " in phrase:
            if phrase in lowered:
                score = max(score, weight)
        elif phrase in toks:
            score = max(score, weight)
    return min(3, score)


def analyze_text(text: str, rating: Optional[float] = None) -> dict:
    sentiment, score = score_sentiment(text, rating)
    return {
        "sentiment": sentiment,
        "sentiment_score": score,
        "topic": classify_topic(text),
        "complaint": extract_complaint(text) if sentiment != "positive" else None,
        "urgency": urgency_of(text),
    }


# ─────────────────────────────────────────────────────────────────────
# Priority scoring + recommendations
# ─────────────────────────────────────────────────────────────────────
def priority_label(score: float) -> str:
    if score >= 65:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 38:
        return "medium"
    return "low"


def compute_recommendations(items: Iterable[dict], recent_share: float = 0.4) -> list[dict]:
    """
    `items` = list of dicts with keys: text, sentiment, topic, urgency, created_at (iso str).
    Returns ranked recommendations with an explainable 'why'.
    """
    items = list(items)
    if not items:
        return []

    total = len(items)
    by_topic: dict[str, list[dict]] = {}
    for it in items:
        by_topic.setdefault(it.get("topic") or "General", []).append(it)

    sorted_items = sorted(items, key=lambda x: str(x.get("created_at", "")), reverse=True)
    recent_cut = max(1, int(total * recent_share))
    recent_set = {id(x) for x in sorted_items[:recent_cut]}

    recs: list[dict] = []
    for topic, group in by_topic.items():
        count = len(group)
        neg = [g for g in group if g.get("sentiment") == "negative"]
        neg_share = len(neg) / count
        urgency_max = max((int(g.get("urgency", 0)) for g in group), default=0)
        urgency_avg = sum(int(g.get("urgency", 0)) for g in group) / count
        recent_neg = sum(1 for g in neg if id(g) in recent_set)
        momentum = recent_neg / max(1, len([g for g in group if id(g) in recent_set]))

        freq_norm = min(1.0, count / max(1, 0.25 * total))
        urgency_norm = min(1.0, (urgency_avg / 3) + (0.15 if urgency_max >= 3 else 0))
        prior = SEVERITY_PRIOR.get(topic, 0.30)
        severity = max(urgency_norm, prior)
        score = round(100 * (0.30 * freq_norm + 0.30 * neg_share + 0.40 * severity), 1)

        examples = [g["text"] for g in neg[:3]] or [g["text"] for g in group[:2]]
        trend_txt = (
            "rising" if momentum > neg_share + 0.08
            else "easing" if momentum < neg_share - 0.08
            else "steady"
        )

        why = (
            f"{count} feedback items mention {topic} ({round(neg_share * 100)}% negative, "
            f"{trend_txt} trend). "
        )
        if prior >= 0.7 and urgency_norm < prior:
            why += "Severity floor applied: this issue class carries elevated risk, so it is not ranked by volume alone. "
        if urgency_max >= 3 and neg_share >= 0.15:
            why += "Includes escalation-level signals (refund/fraud/safety language). "
        elif urgency_max >= 2 and neg_share >= 0.15:
            why += "Includes escalation risk (refunds, repeated contacts). "
        why += f"Representative quote: \u201c{examples[0][:140]}\u201d"

        recs.append({
            "topic": topic,
            "priority": score,
            "priority_label": priority_label(score),
            "title": TITLES.get(topic, f"Address {topic}"),
            "action": TOPIC_ACTIONS.get(topic, TOPIC_ACTIONS["General"]),
            "why": why,
            "evidence_count": count,
            "negative_count": len(neg),
            "negative_share": round(neg_share, 3),
            "trend": trend_txt,
            "urgency_max": urgency_max,
            "examples": examples,
        })

    recs.sort(key=lambda r: r["priority"], reverse=True)
    return recs


def trend_buckets(items: Iterable[dict], key: str = "created_at") -> list[dict]:
    """Monthly sentiment trend: [{month, positive, negative, neutral, total}]."""
    buckets: dict[str, Counter] = {}
    for it in items:
        raw = str(it.get(key) or "")
        month = raw[:7] if len(raw) >= 7 else "unknown"
        b = buckets.setdefault(month, Counter())
        b["total"] += 1
        b[it.get("sentiment") or "neutral"] += 1
    return [
        {"month": m, **dict(b)}
        for m, b in sorted(buckets.items())
        if m != "unknown"
    ]
