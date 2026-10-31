"""How a career becomes a score, and where the Hall of Fame line sits.

PLACEHOLDER: score = number of major singles titles. It exists only so the
pipeline, tests, PR report and paper run end to end. It is not the team's
method; the project brief (docs/) sets out what the real one should address.
"""

import numpy as np
import pandas as pd

# How much each career statistic is worth. Changing a weight is a methodology
# change: say why in the PR, and the report comment shows what it moved.
WEIGHTS = {"slams": 1.0}

# ITHF policy: eligible five years after a player is no longer a significant
# factor on the tour. Approximated here as five years after their last match.
ELIGIBLE_AFTER = 5


def score(features: pd.DataFrame) -> pd.Series:
    return sum((features[k] * w for k, w in WEIGHTS.items()), start=pd.Series(0.0, features.index))


def ithf_rule(features: pd.DataFrame) -> pd.Series:
    """Baseline: the Hall's own automatic-ballot rule for singles players.

    Five major titles, or three majors plus at least 13 weeks at No. 1.
    """
    return (features["slams"] >= 5) | ((features["slams"] >= 3) & (features["weeks_no1"] >= 13))


def fit_threshold(scores: pd.Series, inducted: pd.Series) -> float:
    """The score cut-off that maximises F1 on the training years.

    Note: this uses Hall status to place the line. The brief treats Hall status
    as validation data, so the team should decide whether to keep this step.
    """
    best, best_f1 = float("inf"), -1.0
    for t in np.unique(scores):
        pred = scores >= t
        tp = (pred & inducted).sum()
        f1 = 2 * tp / (pred.sum() + inducted.sum()) if tp else 0.0
        if f1 > best_f1:
            best, best_f1 = float(t), f1
    return best
