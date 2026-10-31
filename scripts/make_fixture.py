"""Build tests/fixtures/data/: a small frozen slice of the pinned snapshot for the tests.

    uv run python scripts/make_fixture.py

The slice (both tours, every year):

- matches: Grand Slam semifinals and finals, so major titles and finals are exact
- rankings: the top 10 of the first ranking of each quarter
- players: everyone those rows mention, plus every inductee
- inductees: the rows of data/inductees.csv for players in the slice

The files keep the dataset's layout and every column the schemas check, so
`data.load` reads the fixture exactly like the real snapshot. It must stay
under 1 MB: it is committed to git so tests run offline in seconds.
Regenerate it only on purpose: the golden files depend on it.
"""

import shutil

import pandas as pd

from hof import data

OUT = data.ROOT / "tests" / "fixtures" / "data"


def main() -> None:
    src = data.fetch(data.pinned())
    inductees = pd.read_csv(data.INDUCTEES, dtype=str, keep_default_na=False, na_values=[""])
    shutil.rmtree(OUT, ignore_errors=True)
    kept_inductees = []
    for tour in data.TOURS:
        (OUT / tour).mkdir(parents=True)
        files = sorted((src / tour).glob(f"{tour}_matches_[0-9][0-9][0-9][0-9].csv"))
        ids: set[str] = set()
        for f in files:
            m = pd.read_csv(f, dtype=str, keep_default_na=False, na_values=[""])
            m = m[(m["tourney_level"] == "G") & m["round"].isin(["SF", "F"])]
            if not m.empty:
                m.to_csv(OUT / tour / f.name, index=False, lineterminator="\n")
                ids |= set(m["winner_id"]) | set(m["loser_id"])

        r = pd.concat(
            pd.read_csv(f, dtype=str, keep_default_na=False, na_values=[""])
            for f in sorted((src / tour).glob(f"{tour}_rankings_*.csv"))
        ).drop_duplicates()
        dates = pd.Series(sorted(r["ranking_date"].unique()))
        quarter = dates.str[:4] + "-" + ((dates.str[4:6].astype(int) - 1) // 3).astype(str)
        firsts = set(dates.groupby(quarter).first())
        r = r[r["ranking_date"].isin(firsts) & (r["rank"].astype(int) <= 10)]
        r.to_csv(OUT / tour / f"{tour}_rankings_fixture.csv", index=False, lineterminator="\n")
        ids |= set(r["player"])

        ind = inductees[inductees["tour"] == tour]
        ids |= set(ind["player_id"])
        kept_inductees.append(ind)
        p = pd.read_csv(src / tour / f"{tour}_players.csv", dtype=str, keep_default_na=False)
        p[p["player_id"].isin(ids)].to_csv(
            OUT / tour / f"{tour}_players.csv", index=False, lineterminator="\n"
        )
    pd.concat(kept_inductees).to_csv(OUT / "inductees.csv", index=False, lineterminator="\n")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"Wrote {OUT} ({size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
