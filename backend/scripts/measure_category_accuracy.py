"""
Measure the 4-class classifier against the organizer ground-truth labels.

Reproducible accuracy number for the README / demo:
    cd backend && python scripts/measure_category_accuracy.py
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.official import classify_official  # noqa: E402

CSV = Path("/home/user/uploads/BuildBattle_2026_Customer_Feedback_Dataset.csv")
LABELS = ["Fraud and Scam", "Customer Service", "Operational Issues", "Product Feedback"]


def main() -> None:
    df = pd.read_csv(CSV).drop_duplicates("review").reset_index(drop=True)
    df["pred"] = df["review"].map(classify_official)

    correct = (df["pred"] == df["category"]).sum()
    acc = correct / len(df)
    print(f"rows (unique): {len(df)}   correct: {correct}   accuracy: {acc:.1%}\n")

    # per-class precision / recall
    print(f"{'category':22} {'support':>8} {'precision':>10} {'recall':>8}")
    for label in LABELS:
        tp = ((df.pred == label) & (df.category == label)).sum()
        fp = ((df.pred == label) & (df.category != label)).sum()
        fn = ((df.pred != label) & (df.category == label)).sum()
        sup = (df.category == label).sum()
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        print(f"{label:22} {sup:>8} {prec:>10.1%} {rec:>8.1%}")

    # confusion matrix
    print("\nconfusion (rows = truth, cols = predicted):")
    header = "".join(f"{l[:11]:>13}" for l in LABELS)
    print(f"{'':22}{header}")
    for t in LABELS:
        row = "".join(f"{((df.category == t) & (df.pred == p)).sum():>13}" for p in LABELS)
        print(f"{t:22}{row}")

    # biggest confusion pairs
    pairs = Counter((t, p) for t, p in zip(df.category, df.pred) if t != p)
    if pairs:
        print("\ntop confusions:")
        for (t, p), n in pairs.most_common(5):
            print(f"  {t} → {p}: {n}")
            ex = df[(df.category == t) & (df.pred == p)]["review"].head(1).tolist()
            if ex:
                print(f"     e.g. {ex[0][:110]}")


if __name__ == "__main__":
    main()
