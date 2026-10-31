"""Bad data must fail at load time, not three steps later inside the model.

And questionable data must be flagged, never silently dropped (docs/: keep the
raw data, prefer explicit missingness).
"""

import pandas as pd
import pandera.errors
import pytest

from hof import data


def test_fixture_passes_schema(ds):
    assert set(ds.matches["tour"]) == {"atp", "wta"}
    assert len(ds.inductees) > 0


def test_unknown_round_is_rejected(ds):
    bad = ds.matches.copy()
    bad.loc[bad.index[0], "round"] = "Final"
    with pytest.raises(pandera.errors.SchemaError):
        data.SCHEMAS["matches"].validate(bad)


def test_tourney_level_must_belong_to_its_tour(ds):
    bad = ds.matches.copy()
    bad.loc[bad.index[0], ["tour", "tourney_level"]] = ["atp", "PM"]  # a WTA-only code
    with pytest.raises(pandera.errors.SchemaError):
        data.SCHEMAS["matches"].validate(bad)


def test_player_ids_are_unique_per_tour(ds):
    bad = pd.concat([ds.players, ds.players.head(1)], ignore_index=True)
    with pytest.raises(pandera.errors.SchemaError):
        data.SCHEMAS["players"].validate(bad)


def test_inductee_needs_a_source_url(ds):
    bad = ds.inductees.copy()
    bad.loc[bad.index[0], "source"] = "wikipedia"
    with pytest.raises(pandera.errors.SchemaError):
        data.SCHEMAS["inductees"].validate(bad)


def test_unknown_player_id_is_rejected(ds):
    bad = ds.matches.copy()
    bad.loc[bad.index[0], "winner_id"] = 999_999_999
    with pytest.raises(ValueError, match="not in players"):
        data._check_links(data.Dataset(bad, ds.players, ds.rankings, ds.inductees))


def _write(folder, tour, matches=None, rankings=None):
    """A one-tour copy of the fixture with some rows replaced."""
    src = data.ROOT / "tests" / "fixtures" / "data"
    for t in data.TOURS:
        (folder / t).mkdir(parents=True)
        for f in (src / t).iterdir():
            (folder / t / f.name).write_bytes(f.read_bytes())
    (folder / "inductees.csv").write_bytes((src / "inductees.csv").read_bytes())
    if matches is not None:
        f = sorted((folder / tour).glob(f"{tour}_matches_*.csv"))[-1]
        matches(f)
    if rankings is not None:
        rankings(folder / tour / f"{tour}_rankings_fixture.csv")
    return data.load(folder, folder / "inductees.csv")


def test_negative_stat_is_flagged_not_dropped(tmp_path):
    def edit(f):
        df = pd.read_csv(f, dtype=str)
        df.loc[0, "w_ace"] = "-3"
        df.to_csv(f, index=False, lineterminator="\n")

    ds = _write(tmp_path, "atp", matches=edit)
    flagged = ds.matches[ds.matches["flag_impossible_value"]]
    assert len(flagged) == 1 and flagged["w_ace"].iloc[0] == -3


def test_exact_duplicate_ranking_rows_are_dropped_and_conflicts_flagged(tmp_path):
    def edit(f):
        df = pd.read_csv(f, dtype=str)
        twin, clash = df.iloc[[0]].copy(), df.iloc[[1]].copy()
        clash["rank"] = "99"
        pd.concat([df, twin, clash]).to_csv(f, index=False, lineterminator="\n")

    before = data.load(
        data.ROOT / "tests" / "fixtures" / "data",
        data.ROOT / "tests" / "fixtures" / "data" / "inductees.csv",
    )
    ds = _write(tmp_path, "atp", rankings=edit)
    assert len(ds.rankings) == len(before.rankings) + 1  # the exact twin is gone
    assert ds.rankings["flag_conflicting_duplicate"].sum() == 2
