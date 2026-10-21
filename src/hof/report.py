"""Compare two runs (master and a PR) and describe the difference in Markdown."""

import json
from pathlib import Path

import pandas as pd
from scipy.stats import kendalltau, spearmanr

METRICS = ["precision", "recall", "f1", "auc"]


def _load(run: Path) -> tuple[pd.DataFrame, dict]:
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    return pd.read_csv(run / "rankings.csv"), metrics


def compare(base: Path, head: Path) -> pd.DataFrame:
    """One row per player seen in either run, with both ranks and scores."""
    b, _ = _load(base)
    h, _ = _load(head)
    keep = ["player_id", "name", "rank", "score", "predicted", "inducted", "status"]
    df = b[keep].merge(h[keep], on=["player_id", "name"], how="outer", suffixes=("_base", "_head"))
    df["rank_change"] = df["rank_base"] - df["rank_head"]  # positive = moved up
    df["score_change"] = (df["score_head"] - df["score_base"]).round(4)
    return df.sort_values("rank_head", na_position="last").reset_index(drop=True)


def _rank(x: float) -> str:
    return "—" if pd.isna(x) else str(int(x))


def _short(sha: str) -> str:
    return f"`{sha[:7]}`" if sha else "`(uncommitted)`"


def _metric_row(label: str, m: dict, base: dict | None = None) -> str:
    cells = []
    for k in METRICS:
        cell = f"{m[k]:.3f}"
        if base is not None and (d := m[k] - base[k]):
            cell += f" ({'▲' if d > 0 else '▼'} {abs(d):.3f})"
        cells.append(cell)
    return f"| {label} | " + " | ".join(cells) + " |"


def _player_table(rows: pd.DataFrame) -> list[str]:
    lines = ["| player | rank master → PR | score master → PR | inducted |", "|---|---|---|---|"]
    for r in rows.itertuples():
        lines.append(
            f"| {r.name} | {_rank(r.rank_base)} → {_rank(r.rank_head)} "
            f"| {r.score_base:.2f} → {r.score_head:.2f} | {'yes' if r.inducted_head else ''} |"
        )
    return lines


def markdown(base: Path, head: Path) -> str:
    df = compare(base, head)
    _, bm = _load(base)
    _, hm = _load(head)
    br, hr = bm["run"], hm["run"]
    snap = hr["snapshot"]
    snap_txt = f"`{snap['name']}` (`{snap['revision'][:12]}`)" if isinstance(snap, dict) else snap
    out = [
        "## Hall of Fame report",
        "",
        f"**What ran:** this PR {_short(hr['commit'])} against master {_short(br['commit'])} "
        f"on data snapshot {snap_txt}, Python {hr['python']} on {hr['platform']}.",
    ]
    if bm["run"]["snapshot"] != snap:
        out.append(
            f"\n> [!WARNING]\n> The data snapshot changed (master used `{bm['run']['snapshot']}`)"
            ". Ranking changes below mix code and data changes."
        )

    both = df.dropna(subset=["rank_base", "rank_head"])
    unchanged = both["score_change"].eq(0).all() and len(both) == len(df)

    out += ["", "### The Hall of Fame line"]
    crossed = df[df["predicted_base"].fillna(False) != df["predicted_head"].fillna(False)]
    if crossed.empty:
        out.append("No player crosses the line.")
    else:
        out.append(f"**{len(crossed)} player(s) cross the line.**")
        for label, now_in in (("Now in", True), ("Now out", False)):
            rows = crossed[crossed["predicted_head"].fillna(False) == now_in]
            if not rows.empty:
                out += ["", f"{label}:", "", *_player_table(rows)]

    out += [
        "",
        "### Agreement with real inductions "
        f"(players eligible {hm['split_year'] + 1}–{hm['as_of']})",
        "",
        "| | precision | recall | F1 | AUC |",
        "|---|---|---|---|---|",
        _metric_row("ITHF auto-ballot rule (baseline)", hm["ithf_rule"]),
        _metric_row("master", bm["model"]),
        _metric_row("**this PR**", hm["model"], bm["model"]),
        "",
        f"Test set: {hm['model']['players']} eligible contenders, "
        f"{hm['model']['inducted']} inducted. Score threshold {hm['threshold']:.2f} "
        f"(master {bm['threshold']:.2f}), fitted on players eligible up to {hm['split_year']}.",
    ]

    out += ["", "### Ranking changes"]
    if unchanged:
        out.append(f"No ranking changes across {len(df)} contenders.")
    else:
        tau = kendalltau(both["score_base"], both["score_head"]).statistic
        rho = spearmanr(both["score_base"], both["score_head"]).statistic
        moved = int((both["rank_change"] != 0).sum())
        out.append(
            f"{moved} of {len(df)} contenders changed rank. Agreement with master: "
            f"Kendall τ = {tau:.3f}, Spearman ρ = {rho:.3f}."
        )
        for label, rows in (
            ("Biggest moves up", both[both["rank_change"] > 0].nlargest(10, "rank_change")),
            ("Biggest moves down", both[both["rank_change"] < 0].nsmallest(10, "rank_change")),
        ):
            if not rows.empty:
                out += [
                    "",
                    f"<details><summary>{label}</summary>",
                    "",
                    *_player_table(rows),
                    "",
                    "</details>",
                ]

    out += ["", "### Runtime", "", "| stage | master | PR | change |", "|---|---|---|---|"]
    stages = list(dict.fromkeys([*br["seconds"], *hr["seconds"]]))
    for s in [*stages, "total"]:
        b = sum(br["seconds"].values()) if s == "total" else br["seconds"].get(s, 0.0)
        h = sum(hr["seconds"].values()) if s == "total" else hr["seconds"].get(s, 0.0)
        pct = f"{(h - b) / b:+.0%}" if b else "new"
        name = f"**{s}**" if s == "total" else s
        out.append(f"| {name} | {b:.2f}s | {h:.2f}s | {pct} |")
    out.append(
        "\nBoth runs share one runner, so the times are comparable with each other "
        "but not with other PRs."
    )

    top = df.head(20)
    out += [
        "",
        "<details><summary>Top 20 on this PR</summary>",
        "",
        "| # | player | score | status | predicted | inducted |",
        "|---|---|---|---|---|---|",
    ]
    for r in top.itertuples():
        out.append(
            f"| {_rank(r.rank_head)} | {r.name} | {r.score_head:.2f} | {r.status_head} "
            f"| {'yes' if r.predicted_head else ''} | {'yes' if r.inducted_head else ''} |"
        )
    out += ["", "</details>"]
    return "\n".join(out) + "\n"
