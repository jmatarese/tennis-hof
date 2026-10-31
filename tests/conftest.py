from pathlib import Path

import pytest

from hof import data

FIXTURE = Path(__file__).parent / "fixtures" / "data"


@pytest.fixture(scope="session")
def ds() -> data.Dataset:
    """A small frozen slice of the real snapshot (both tours, 1968-2026): Grand Slam
    semifinals and finals, the quarterly top 10, and the inductees among them.
    Rebuild with `uv run python scripts/make_fixture.py` (see its docstring)."""
    return data.load(FIXTURE, FIXTURE / "inductees.csv")
