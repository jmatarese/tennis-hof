"""The ranking on a frozen dataset. If this fails, the method changed.

If you meant to change it, regenerate the expected files and commit them with
your PR so reviewers see exactly what moved:

    uv run pytest tests/test_pipeline.py --force-regen
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from hof import data, pipeline


# One golden file per test: `--force-regen` stops a test at its first rewrite,
# so two checks in one test would need two runs to regenerate.
def test_rankings_match_golden_file(ds, dataframe_regression):
    rankings, _ = pipeline.rank(ds)
    dataframe_regression.check(rankings.astype({"first_year": float, "last_year": float}))


def test_metrics_match_golden_file(ds, data_regression):
    _, metrics = pipeline.rank(ds)
    data_regression.check(metrics)


@settings(max_examples=5, deadline=None)
@given(seed=st.integers(0, 2**32 - 1))
def test_row_order_does_not_change_rankings(ds, seed):
    shuffled = data.Dataset(
        matches=ds.matches.sample(frac=1, random_state=seed),
        players=ds.players.sample(frac=1, random_state=seed),
        rankings=ds.rankings.sample(frac=1, random_state=seed),
        inductees=ds.inductees.sample(frac=1, random_state=seed),
    )
    expected, _ = pipeline.rank(ds)
    got, _ = pipeline.rank(shuffled)
    assert got.equals(expected)
