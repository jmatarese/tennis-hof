"""The whole method, end to end: data in, ranked players and metrics out.

`rank()` is where the team's method plugs in. Whatever it does, it must return
the contract the PR report and the paper read (see README): one row per player
with rank, tour, player_id, name, score, predicted, inducted and status, and the
metrics dict below.
"""

import json
import platform
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from hof import data, evaluate, features, model

# PLACEHOLDER: train on players who became eligible up to this year, test on the ones after.
SPLIT_YEAR = 2010


class Stopwatch:
    def __init__(self) -> None:
        self.seconds: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        yield
        self.seconds[name] = round(time.perf_counter() - start, 4)


def rank(ds: data.Dataset, clock: Stopwatch | None = None) -> tuple[pd.DataFrame, dict]:
    """Rank every contender and score the method against real inductions."""
    clock = clock or Stopwatch()
    with clock.stage("features"):
        f = features.career_stats(ds)
    with clock.stage("score"):
        as_of = int(ds.matches["tourney_date"].max() // 10000) + 1
        # PLACEHOLDER: a contender reached a major final or the top 10
        df = f[(f["slam_finals"] > 0) | (f["weeks_top10"] > 0)].copy()
        df["score"] = model.score(df).round(4)
        df["ithf_rule"] = model.ithf_rule(df)
        inducted = pd.MultiIndex.from_frame(ds.inductees[features.KEY])
        df["inducted"] = df.index.isin(inducted)
        df["eligible_year"] = (df["last_year"] + model.ELIGIBLE_AFTER).astype(int)
        eligible = df[df["eligible_year"] <= as_of]
        train = eligible[eligible["eligible_year"] <= SPLIT_YEAR]
        threshold = model.fit_threshold(train["score"], train["inducted"])
        df["predicted"] = df["score"] >= threshold
        df["status"] = (df["eligible_year"] <= as_of).map({True: "eligible", False: "active"})
    with clock.stage("evaluate"):
        test = df[(df["eligible_year"] > SPLIT_YEAR) & (df["eligible_year"] <= as_of)]
        metrics = {
            "as_of": as_of,
            "split_year": SPLIT_YEAR,
            "threshold": threshold,
            "model": evaluate.metrics(test["predicted"], test["score"], test["inducted"]),
            "ithf_rule": evaluate.metrics(
                test["ithf_rule"], test["ithf_rule"].astype(float), test["inducted"]
            ),
        }
    names = ds.players.set_index(features.KEY)["name"]
    df = (
        df.join(names)
        .reset_index()
        .sort_values(["score", "tour", "player_id"], ascending=[False, True, True])
    )
    df.insert(0, "rank", range(1, len(df) + 1))
    cols = [
        "rank",
        "tour",
        "player_id",
        "name",
        "score",
        "predicted",
        "ithf_rule",
        "inducted",
        "status",
        "eligible_year",
        *features.COLUMNS,
    ]
    return df[cols].reset_index(drop=True), metrics


def run(out: Path, path: Path | None = None) -> dict:
    """Run against the pinned snapshot (or a data folder `path`) and write results to `out`.

    A data folder brings its own inductees.csv (the test fixture does).
    """
    clock = Stopwatch()
    snap = data.pinned()
    folder = path or data.fetch(snap)  # outside the stopwatch: a download is not our runtime
    with clock.stage("load"):
        ds = data.load(folder, path / "inductees.csv" if path else data.INDUCTEES)
    rankings, metrics = rank(ds, clock)
    git = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=data.ROOT
    )
    commit = git.stdout.strip() if git.returncode == 0 else ""
    metrics["run"] = {
        "commit": commit,
        "snapshot": {"name": snap.name, "revision": snap.revision} if path is None else str(path),
        "python": platform.python_version(),
        "platform": platform.platform(terse=True),
        "seconds": clock.seconds,
    }
    out.mkdir(parents=True, exist_ok=True)
    rankings.to_csv(out / "rankings.csv", index=False, lineterminator="\n")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics
