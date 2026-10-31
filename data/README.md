# Data

The big data is not in git. It lives in the team's Hugging Face dataset,
[jmatarese/atp-data](https://huggingface.co/datasets/jmatarese/atp-data), a copy
of Jeff Sackmann's ATP and WTA data (CC BY-NC-SA 4.0). `data/snapshot.toml`
pins one commit of it; `uv run hof setup` downloads the pinned files to
`~/.cache/huggingface`, and every run records which snapshot it used. Only
`src/hof/data.py` knows where the data lives.

What's in git here is small and hand-made:

| File | What it is |
|---|---|
| `sources/ithf_inductees_2026-10-21.tsv` | The ITHF inductee list exactly as collected from [tennisfame.com](https://www.tennisfame.com/hall-of-famers/inductees) on 2026-10-21 (271 cards). Never edited |
| `inductees.csv` | **Preliminary.** Players from that list matched to `tour` + `player_id` by `scripts/build_inductees.py`: 94 players (87 exact name matches, 7 reviewed aliases), one source URL per row |
| `inductees_unmatched.csv` | The 121 players not matched, with the reason (almost all pre-Open-Era careers) |

The full master set of inductees is tracked in issue #9. To rebuild:
`uv run python scripts/build_inductees.py data/sources/ithf_inductees_2026-10-21.tsv`

## Current snapshot: `v1`

Commit `c704c1bcbe08949246d956b54b099715d5997dcb`: the source
[Aneeshers/tennis-sackmann-archive](https://huggingface.co/datasets/Aneeshers/tennis-sackmann-archive)
at commit `8ac86f7c`, duplicated on 2026-10-21, plus the dataset card.

The pipeline reads tour-level singles matches, weekly rankings and players for
both tours (about 200 MB). Challenger, futures, qualifying, ITF and
point-by-point files are in the dataset but not read.

| | ATP | WTA |
|---|---|---|
| Matches | 199,389 (Dec 1967 – May 2026) | 162,182 (Dec 1967 – May 2026) |
| Players | 66,912 | 70,571 |
| Weekly rankings | 3,420,414 rows, from 1973-08-27 | 2,154,263 rows, from **1984-01-02** |

ATP and WTA reuse the same player id numbers (14,627 overlap), so a player is
always identified by `tour` + `player_id`.

## What loading does

`data.load()` validates every table against the schemas in `data.py` and fails
on malformed data. It never filters: that's a method decision. It does two
things beyond reading:

1. **Drops exact duplicate rows**: 181 ATP and 55 WTA ranking rows that repeat
   another row exactly. Nothing is lost.
2. **Adds `flag_*` columns** for rows the team still has to decide about. The
   rows stay in; the pipeline chooses what to do with each flag.

| Flag | ATP | WTA | What it marks |
|---|---|---|---|
| `flag_self_match` | 3 | 1 | Winner and loser are the same id ("Unknown" vs "Unknown") |
| `flag_unknown_player` | 90 | 0 | A player recorded as "Unknown" |
| `flag_bye` | 2 | 0 | The "opponent" is a bye: no match was played |
| `flag_duplicate_key` | 0 | 32 | Rows sharing tourney_id + match_num but not identical |
| `flag_impossible_value` | 2 | 24 | Negative stats or ages, or text in a number column (`"exho"` as a draw size; made empty) |
| `flag_conflicting_duplicate` (rankings) | 1,198 | 452 | A player with two different ranks in the same week |

One value is normalised: surface `clay` becomes `Clay` (31 WTA rows from 2025).

## Open questions for the team

Recorded here so they're decided on purpose, in the paper's Data section:

- What to do with each flag above.
- Walkovers (W/O), retirements (RET) and defaults (DEF): do they count as wins, losses, matches?
- Which tournament levels count (Davis Cup `D`, Olympics `O`, exhibitions `E`, WTA tiers, `35+H`/`50+H`)?
- Round robin (`RR`), bronze-medal (`BR`) and `ER` rounds.
- Missing data: no surface (2,990 ATP, 4,897 WTA), no birth date (18,639 ATP, 44,161 WTA), no ranking points.
- Rankings start in 1973 (ATP) and 1984 (WTA) in this data: how to treat earlier careers (the brief asks for a data audit of 1968–71).
- One-set matches (`best_of = 1`, 138 WTA rows, mostly 1970s).

## Publishing a new version

1. Upload the new files and tag the version:
   ```bash
   uv run hf upload jmatarese/atp-data ./new-files atp --repo-type dataset --commit-message "Add 2026 season"
   uv run hf repos tag create jmatarese/atp-data v2 --repo-type dataset
   ```
2. Get the commit hash:
   ```bash
   uv run python -c "from huggingface_hub import HfApi; print(HfApi().dataset_info('jmatarese/atp-data', revision='v2').sha)"
   ```
3. Update `name` and `revision` in `snapshot.toml`, and the dataset card's versions table.
4. Open a PR that changes **only** the snapshot. The report will warn that the data changed.
