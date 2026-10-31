"""Properties every version of the method must keep.

These are axioms, checked on hundreds of generated careers. They start with
only what the placeholder obviously satisfies; the team adds its own, and they
double as the paper's "Properties" section.
"""

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from hof import model

career = st.fixed_dictionaries({"slams": st.integers(0, 30), "weeks_no1": st.integers(0, 450)})


@given(career, st.sampled_from(sorted(model.WEIGHTS)))
def test_more_achievement_never_lowers_the_score(c, stat):
    better = {**c, stat: c[stat] + 1}
    before, after = model.score(pd.DataFrame([c, better]))
    assert after >= before


@pytest.mark.parametrize(
    ("slams", "weeks_no1", "on_ballot"),
    [(5, 0, True), (4, 0, False), (3, 13, True), (3, 12, False), (2, 300, False)],
)
def test_ithf_rule_matches_the_published_thresholds(slams, weeks_no1, on_ballot):
    df = pd.DataFrame([{"slams": slams, "weeks_no1": weeks_no1}])
    assert bool(model.ithf_rule(df).iloc[0]) is on_ballot
