"""How well a set of predictions matches the players the Hall actually inducted."""

import pandas as pd
from scipy.stats import mannwhitneyu


def metrics(predicted: pd.Series, scores: pd.Series, inducted: pd.Series) -> dict[str, float]:
    tp = int((predicted & inducted).sum())
    precision = tp / predicted.sum() if predicted.any() else 0.0
    recall = tp / inducted.sum() if inducted.any() else 0.0
    f1 = 2 * precision * recall / (precision + recall) if tp else 0.0
    pos, neg = scores[inducted], scores[~inducted]
    auc = mannwhitneyu(pos, neg).statistic / (len(pos) * len(neg)) if len(pos) and len(neg) else 0.0
    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "auc": round(float(auc), 4),
        "players": len(scores),
        "inducted": int(inducted.sum()),
    }
