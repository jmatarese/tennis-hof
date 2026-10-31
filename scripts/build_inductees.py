"""Build data/inductees.csv from the ITHF list, matched to the dataset's player ids.

    uv run python scripts/build_inductees.py data/sources/ithf_inductees_2026-10-21.tsv

The input is the Hall's inductee list exactly as collected from
https://www.tennisfame.com/hall-of-famers/inductees (kept unedited in
data/sources/). This script keeps the player categories (Recent Player,
Master Player), finds each player in the pinned snapshot, and writes:

- data/inductees.csv: matched players, with how each was matched
- data/inductees_unmatched.csv: players not found, for the master-set work

Matching never guesses. A player matches on the full name (`exact`) or a
reviewed entry in ALIASES (`alias`), and only among players whose first
tour-level match came in or before their induction year, so a modern namesake can't
match a 1950s inductee. Ambiguous names are left unmatched.

This is a preliminary list: the team will build the full master set later.
"""

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

from hof import data

INDEX = "https://www.tennisfame.com/hall-of-famers/inductees"

# ITHF name -> name in Sackmann's players file, where the two differ.
# Each entry is a reviewed fact (married names, nicknames, name order).
ALIASES = {
    "stefanie graf": "steffi graf",
    "margaret smith court": "margaret court",
    "li na": "na li",
    "richard pancho gonzalez": "richard gonzalez",
    "ann haydon jones": "ann jones",
    "natasha zvereva": "natalia zvereva",
    "evonne goolagong": "evonne goolagong cawley",
    "lesley turner bowrey": "lesley turner",
    "angela mortimer barrett": "angela mortimer",
    "maureen connolly brinker": "maureen connolly",
    "manuel santana": "manolo santana",
    "bob bryan": "bob bryan",
    "mike bryan": "mike bryan",
}
TITLES = {"sir", "baron", "dr", "major", "king"}


def norm(name: str) -> str:
    """Lowercase ASCII words: 'Björn Borg' -> 'bjorn borg', "Dr. James" -> 'james'."""
    ascii_ = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    words = re.sub(r"[^a-z ]", " ", ascii_.lower().replace("-", " ")).split()
    return " ".join(w for w in words if w not in TITLES and w != "ii")


def main(source: Path) -> None:
    ithf = pd.read_csv(source, sep="\t", dtype=str, keep_default_na=False)
    players = ithf[ithf["category"].isin(["Recent Player", "Master Player", ""])].copy()
    # One card covers both Bryan brothers
    bryans = players["name"] == "BOB & MIKE BRYAN"
    players = pd.concat(
        [
            players[~bryans],
            players[bryans].assign(name="BOB BRYAN"),
            players[bryans].assign(name="MIKE BRYAN"),
        ]
    )
    players["source"] = players["profile_url"].where(players["profile_url"] != "", INDEX)

    ds_path = data.fetch(data.pinned())
    pool = []
    for tour in data.TOURS:
        p = data._players(ds_path, tour)
        m = data._matches(ds_path, tour)
        year = m["tourney_date"].str[:4].astype(int)
        first = pd.concat([year, year]).groupby(pd.concat([m["winner_id"], m["loser_id"]])).min()
        p = p[p["player_id"].isin(first.index)].copy()
        p["first_year"] = p["player_id"].map(first)
        p["key"] = p["name"].fillna("").map(norm)
        pool.append(p[["tour", "player_id", "name", "key", "first_year"]])
    pool = pd.concat(pool, ignore_index=True)

    matched, unmatched = [], []
    for r in players.itertuples():
        key = norm(r.name)
        hit, how, reason = None, None, "not in the data"
        for k, h in ((key, "exact"), (ALIASES.get(key), "alias")):
            rows = pool[pool["key"] == k]
            if rows.empty:
                continue
            rows = rows[rows["first_year"] <= int(r.class_year)]
            if len(rows) == 1:
                hit, how = rows.iloc[0], h
                break
            reason = (
                f"{len(rows)} players share this name" if len(rows) else "only a later namesake"
            )
        base = {
            "name": r.name.title(),
            "induction_year": r.class_year,
            "category": r.category,
            "source": r.source,
        }
        if hit is None:
            unmatched.append({**base, "reason": reason})
        else:
            matched.append(
                {
                    "tour": hit["tour"],
                    "player_id": hit["player_id"],
                    **base,
                    "dataset_name": hit["name"],
                    "match": how,
                }
            )

    out = pd.DataFrame(matched).sort_values(["tour", "induction_year", "name"])
    out.to_csv(data.ROOT / "data" / "inductees.csv", index=False, lineterminator="\n")
    miss = pd.DataFrame(unmatched).sort_values(["induction_year", "name"])
    miss.to_csv(data.ROOT / "data" / "inductees_unmatched.csv", index=False, lineterminator="\n")
    print(f"{len(out)} matched ({out['match'].value_counts().to_dict()}), {len(miss)} unmatched")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
