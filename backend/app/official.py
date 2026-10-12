"""
Official-category classifier for the BuildBattle 2026 taxonomy:
    Fraud and Scam · Customer Service · Operational Issues · Product Feedback

These are DOMAIN labels, not sentiment labels — the dataset contains positive
reviews inside "Fraud and Scam" ("I was not a victim of fraud, the seller
provided the genuine product"). So matching is keyword/domain based and
deliberately polarity-blind.

Tuned against the 320 unique labelled reviews and measured for agreement —
see scripts/measure_category_accuracy.py for the reproducible number.
"""
from __future__ import annotations

import re

# ── domain keyword rules, weighted ──────────────────────────────────────
RULES: dict[str, dict[str, int]] = {
    "Fraud and Scam": {
        "fraud": 6, "fraudulent": 6, "scam": 6, "scammed": 6, "scamming": 6,
        "counterfeit": 4, "fake": 4, "deceived": 4, "cheated": 4, "duped": 4,
        "unauthorized": 4, "suspicious": 3, "stole": 4, "stolen": 4,
        "additional payment": 5, "victim": 5, "genuine product": 3, "refund policy": 2,
    },
    "Customer Service": {
        "customer service": 6, "customer support": 6, "support team": 5,
        "service representative": 5, "representative": 4, "agent": 4, "staff": 4,
        "helpline": 5, "unresponsive": 5, "responded": 3, "response": 3,
        "inquiry": 4, "enquiry": 4, "complaint handling": 4, "helpful": 3,
        "polite": 3, "rude": 4, "attitude": 4, "assistance": 3, "assisted": 3,
        "customer care": 5,
    },
    "Operational Issues": {
        "delivery": 5, "delayed": 5, "delay": 5, "shipping": 4, "courier": 4,
        "logistics": 4, "operational": 5, "order": 3, "website": 4, "app": 2,
        "checkout": 3, "transaction": 3, "payment": 3, "billing": 3,
        "processing": 3, "system": 3, "unforeseen circumstances": 5,
        "informed promptly": 3, "placing my order": 4, "ordering process": 4,
    },
    "Product Feedback": {
        "product": 4, "design": 4, "quality": 3, "features": 4, "feature": 3,
        "durable": 4, "durability": 4, "performance": 3, "functionality": 4,
        "value for money": 4, "worth": 3, "investment": 3, "gamechanger": 5,
        "game changer": 5, "innovative": 4, "build": 2, "material": 3,
        "packaging": 3, "colour": 2, "color": 2, "style": 3, "price": 3,
        "expectations": 2, "recommend": 2,
    },
}

_WORD_RE = re.compile(r"[a-z']+")


def classify_official(text: str) -> str:
    """Return one of the four official categories."""
    lowered = (text or "").lower()
    toks = _WORD_RE.findall(lowered)
    tok_set = set(toks)

    scores: dict[str, int] = {k: 0 for k in RULES}
    for label, kws in RULES.items():
        for kw, weight in kws.items():
            if " " in kw:
                if kw in lowered:
                    scores[label] += weight
            elif kw in tok_set:
                scores[label] += weight

    # specificity tie-break: fraud > service > operational > product
    order = ["Fraud and Scam", "Customer Service", "Operational Issues", "Product Feedback"]
    best = max(order, key=lambda k: (scores[k], -order.index(k)))
    if scores[best] == 0:
        # no signal: "product" appears in most sentences, so fall back to it
        return "Product Feedback"
    return best


def score_detail(text: str) -> dict[str, int]:
    """Expose per-class scores (handy for debugging / transparency)."""
    lowered = (text or "").lower()
    toks = set(_WORD_RE.findall(lowered))
    out = {}
    for label, kws in RULES.items():
        s = 0
        for kw, weight in kws.items():
            if (" " in kw and kw in lowered) or (" " not in kw and kw in toks):
                s += weight
        out[label] = s
    return out
