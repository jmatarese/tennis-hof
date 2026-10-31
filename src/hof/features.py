"""Career statistics, one row per player (tour + player_id).

PLACEHOLDER: only what the placeholder method in model.py needs, counted from
the raw data with no filtering. Which matches, tournaments, rounds and flagged
rows count is the team's decision (see data/README.md and the open issues).
"""

import pandas as pd

from hof.data import Dataset

KEY = ["tour", "player_id"]
COLUMNS = [
    "slams",
    "slam_finals",
    "weeks_no1",
    "weeks_top10",
    "wins",
    "losses",
    "first_year",
    "last_year",
]


def _count(rows: pd.DataFrame, id_col: str, index: pd.MultiIndex) -> pd.Series:
    return rows.groupby(["tour", id_col]).size().rename_axis(KEY).reindex(index, fill_value=0)


def career_stats(ds: Dataset) -> pd.DataFrame:
    m = ds.matches
    index = pd.MultiIndex.from_frame(ds.players[KEY])
    finals = m[(m["round"] == "F") & (m["tourney_level"] == "G")]
    # A ranking week counts once, even where the source repeats a player in one week
    weeks = ds.rankings.drop_duplicates(["tour", "player_id", "ranking_date"])

    df = pd.DataFrame(index=index)
    df["slams"] = _count(finals, "winner_id", index)
    df["slam_finals"] = df["slams"] + _count(finals, "loser_id", index)
    df["weeks_no1"] = _count(weeks[weeks["rank"] == 1], "player_id", index)
    df["weeks_top10"] = _count(weeks[weeks["rank"] <= 10], "player_id", index)
    df["wins"] = _count(m, "winner_id", index)
    df["losses"] = _count(m, "loser_id", index)
    # A career spans every year with a match or a ranking week
    active = pd.concat(
        [
            m[["tour", "winner_id", "tourney_date"]].set_axis([*KEY, "date"], axis=1),
            m[["tour", "loser_id", "tourney_date"]].set_axis([*KEY, "date"], axis=1),
            weeks[["tour", "player_id", "ranking_date"]].set_axis([*KEY, "date"], axis=1),
        ]
    )
    years = (active["date"] // 10000).groupby([active["tour"], active["player_id"]])
    df["first_year"] = years.min().reindex(index).astype("Int64")
    df["last_year"] = years.max().reindex(index).astype("Int64")
    return df[COLUMNS]
