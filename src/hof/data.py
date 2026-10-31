"""The data snapshot: which one we use, how to fetch it, and how to load it.

`data/snapshot.toml` pins one commit of the team's Hugging Face dataset. Every
run records its `name` and `revision`, so a ranking change is always a code
change, never a silent change upstream. Only this module knows where the data
lives; swap the storage here and nothing else changes.

Loading follows the project brief (docs/): keep the raw data, prefer explicit
missingness to invented values, and leave every judgement call to the method.
So `load` only

- drops rows that are *exact* duplicates of another row (no information lost),
- adds `flag_*` columns marking rows the team still has to decide about, and
- validates: malformed data fails here, not three steps later in a model.

It never filters. Which tournaments, rounds, walkovers or flagged rows count is
a method decision and belongs in the pipeline.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pandera.pandas as pa
from huggingface_hub import snapshot_download
from huggingface_hub.errors import LocalEntryNotFoundError

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "data" / "snapshot.toml"
INDUCTEES = ROOT / "data" / "inductees.csv"
TOURS = ("atp", "wta")


@dataclass(frozen=True)
class Snapshot:
    name: str  # for people, e.g. "v1"
    repo: str  # e.g. "jmatarese/atp-data"
    revision: str  # commit hash on the Hub: immutable, unlike a tag
    files: list[str]  # glob patterns: download only what the pipeline reads


def pinned() -> Snapshot:
    with PIN.open("rb") as f:
        return Snapshot(**tomllib.load(f))


def _download(snap: Snapshot, offline: bool) -> Path:
    return Path(
        snapshot_download(
            snap.repo,
            repo_type="dataset",
            revision=snap.revision,
            allow_patterns=snap.files,
            local_files_only=offline,
        )
    )


def is_fetched(snap: Snapshot) -> bool:
    try:
        _download(snap, offline=True)
        return True
    except LocalEntryNotFoundError:
        return False


def fetch(snap: Snapshot) -> Path:
    """Download the pinned files once; later calls read the local cache."""
    return _download(snap, offline=False)


@dataclass(frozen=True)
class Dataset:
    """Every table has a `tour` column: ATP and WTA reuse the same player ids."""

    matches: pd.DataFrame
    players: pd.DataFrame
    rankings: pd.DataFrame
    inductees: pd.DataFrame


# Rows the team still has to decide about. Each flag is True/False on every row.
FLAGS = {
    "matches": {
        "flag_self_match": "winner_id equals loser_id (e.g. 'Unknown' vs 'Unknown')",
        "flag_unknown_player": "a player is recorded as 'Unknown'",
        "flag_bye": "the 'opponent' is a bye, not a player, so no match was played",
        "flag_duplicate_key": "another row has the same tour, tourney_id and match_num",
        "flag_impossible_value": "a number column held text (now empty) or is negative (kept)",
    },
    "rankings": {
        "flag_conflicting_duplicate": "the player has two different rows in the same week",
    },
}

# Codes from atp/matches_data_dictionary.txt plus those observed in the data
# (the dictionary does not list 'O' Olympics, 'BR' bronze match or 'ER' early rounds).
# An unknown code fails validation, so a new code gets looked at before it is used.
LEVELS = {
    "atp": ["G", "M", "A", "F", "D", "O"],
    "wta": ["G", "PM", "P", "I", "T1", "T2", "T3", "T4", "T5", "W", "CC", "F", "D", "O", "E", "J"]
    + ["35+H", "50+H"],
}
ROUNDS = ["R128", "R64", "R32", "R16", "QF", "SF", "F", "RR", "BR", "ER"]
SURFACES = ["Hard", "Clay", "Grass", "Carpet"]

_tour = pa.Column(str, pa.Check.isin(TOURS))
_id = pa.Column("int64", pa.Check.ge(0), coerce=True)
_count = pa.Column("Int64", pa.Check.ge(0), nullable=True, coerce=True)
_season = pa.Check.in_range(19671201, 20991231)  # the 1968 season's first events are dated Dec 1967

_MATCH_STATS = [
    f"{side}_{stat}"
    for side in ("w", "l")
    for stat in ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced")
]
# Match numbers that can't be negative. Bad values are flagged, not rejected (see _numbers).
_MATCH_INTS = ["draw_size", "minutes", "winner_rank", "loser_rank", *_MATCH_STATS]
_MATCH_FLOATS = ["winner_age", "loser_age", "winner_rank_points", "loser_rank_points"]
SCHEMAS = {
    "matches": pa.DataFrameSchema(
        {
            "tour": _tour,
            "tourney_id": pa.Column(str),
            "tourney_name": pa.Column(str),
            "tourney_level": pa.Column(str),
            "tourney_date": pa.Column("int64", _season, coerce=True),
            "surface": pa.Column(str, pa.Check.isin(SURFACES), nullable=True),
            "round": pa.Column(str, pa.Check.isin(ROUNDS)),
            # 1 is real: one-set matches, mostly 1970s WTA
            "best_of": pa.Column("Int64", pa.Check.isin([1, 3, 5]), nullable=True, coerce=True),
            "winner_id": _id,
            "loser_id": _id,
            "score": pa.Column(str, nullable=True),  # walkovers, retirements, defaults are real
            **{c: pa.Column("Int64", nullable=True) for c in _MATCH_INTS},
            **{c: pa.Column("Float64", nullable=True) for c in _MATCH_FLOATS},
            **{c: pa.Column(bool) for c in FLAGS["matches"]},
        },
        checks=pa.Check(
            lambda df: (df["tour"] + ":" + df["tourney_level"]).isin(
                [f"{t}:{lv}" for t, levels in LEVELS.items() for lv in levels]
            ),
            error="tourney_level not in LEVELS for its tour",
        ),
    ),
    "players": pa.DataFrameSchema(
        {
            "tour": _tour,
            "player_id": _id,
            "name": pa.Column(str, nullable=True),
            "name_first": pa.Column(str, nullable=True),
            "name_last": pa.Column(str, nullable=True),
            "hand": pa.Column(str, nullable=True),
            # Birth dates are often missing or partial (day "00"); kept as recorded.
            "dob": pa.Column("Int64", nullable=True, coerce=True),
            "ioc": pa.Column(str, nullable=True),
            "height": _count,
        },
        unique=["tour", "player_id"],
    ),
    "rankings": pa.DataFrameSchema(
        {
            "tour": _tour,
            "ranking_date": pa.Column("int64", pa.Check.in_range(19730101, 20991231), coerce=True),
            "rank": pa.Column("int64", pa.Check.ge(1), coerce=True),  # ties share a rank
            "player_id": _id,
            "points": pa.Column("Float64", pa.Check.ge(0), nullable=True, coerce=True),
            **{c: pa.Column(bool) for c in FLAGS["rankings"]},
        }
    ),
    "inductees": pa.DataFrameSchema(
        {
            "tour": _tour,
            "player_id": _id,
            "name": pa.Column(str),
            "induction_year": pa.Column("int64", pa.Check.in_range(1955, 2099), coerce=True),
            "source": pa.Column(str, pa.Check.str_startswith("https://")),
        },
        unique=["tour", "player_id"],
    ),
}


def _read(files: list[Path], tour: str) -> pd.DataFrame:
    """Read CSVs as text, so pandas guesses nothing; the schema converts types."""
    if not files:
        raise FileNotFoundError(f"no {tour} files found")
    frames = [pd.read_csv(f, dtype=str, keep_default_na=False, na_values=[""]) for f in files]
    df = pd.concat(frames, ignore_index=True)
    df.insert(0, "tour", tour)
    return df


def _numbers(df: pd.DataFrame, cols: list[str], dtype: str) -> pd.Series:
    """Convert columns to numbers; return which rows held text or a negative value.

    Text can't live in a number column, so it becomes missing. Negative values
    stay as recorded. Either way the row is flagged for the team to decide on.
    """
    bad = pd.Series(False, index=df.index)
    for c in cols:
        num = pd.to_numeric(df[c], errors="coerce")
        bad |= (df[c].notna() & num.isna()) | (num < 0)
        df[c] = num.astype(dtype)
    return bad


def _matches(path: Path, tour: str) -> pd.DataFrame:
    df = _read(sorted((path / tour).glob(f"{tour}_matches_[0-9][0-9][0-9][0-9].csv")), tour)
    # Same surface, different capitalisation (e.g. 'clay' in some 2025 WTA rows)
    df["surface"] = df["surface"].str.capitalize()
    names = df["winner_name"].fillna("") + "|" + df["loser_name"].fillna("")
    df["flag_self_match"] = df["winner_id"] == df["loser_id"]
    df["flag_unknown_player"] = names.str.contains(r"(?:^|\|)\s*(?:\w\s)?Unknown\s*(?:\||$)")
    df["flag_bye"] = names.str.contains(r"(?:^|\|)\s*Bye\d*\s*(?:\||$)", case=False)
    df["flag_duplicate_key"] = df.duplicated(["tourney_id", "match_num"], keep=False)
    df["flag_impossible_value"] = _numbers(df, _MATCH_INTS, "Int64") | _numbers(
        df, _MATCH_FLOATS, "Float64"
    )
    return df


def _rankings(path: Path, tour: str) -> pd.DataFrame:
    df = _read(sorted((path / tour).glob(f"{tour}_rankings_*.csv")), tour)
    df = df.rename(columns={"player": "player_id"}).drop_duplicates(ignore_index=True)
    df["flag_conflicting_duplicate"] = df.duplicated(["ranking_date", "player_id"], keep=False)
    return df


def _players(path: Path, tour: str) -> pd.DataFrame:
    df = _read([path / tour / f"{tour}_players.csv"], tour)
    name = (df["name_first"].fillna("") + " " + df["name_last"].fillna("")).str.strip()
    df.insert(2, "name", name.where(name != ""))
    return df


def _check_links(ds: Dataset) -> None:
    """Every player id used in matches, rankings or inductees exists for that tour."""
    known = pd.MultiIndex.from_frame(ds.players[["tour", "player_id"]])
    used = {
        "matches.winner_id": ds.matches[["tour", "winner_id"]],
        "matches.loser_id": ds.matches[["tour", "loser_id"]],
        "rankings.player_id": ds.rankings[["tour", "player_id"]],
        "inductees.player_id": ds.inductees[["tour", "player_id"]],
    }
    for where, ids in used.items():
        missing = ~pd.MultiIndex.from_frame(ids).isin(known)
        if missing.any():
            sample = ids[missing].drop_duplicates().head(5).to_dict("records")
            raise ValueError(f"{missing.sum()} {where} values are not in players, e.g. {sample}")


def load(path: Path, inductees: Path = INDUCTEES) -> Dataset:
    """Read every table, mark rows to decide about, and validate."""
    tables = {
        "matches": pd.concat([_matches(path, t) for t in TOURS], ignore_index=True),
        "players": pd.concat([_players(path, t) for t in TOURS], ignore_index=True),
        "rankings": pd.concat([_rankings(path, t) for t in TOURS], ignore_index=True),
        "inductees": pd.read_csv(inductees, dtype=str, keep_default_na=False, na_values=[""]),
    }
    ds = Dataset(**{name: SCHEMAS[name].validate(df) for name, df in tables.items()})
    _check_links(ds)
    return ds
