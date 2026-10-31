"""The PR report, end to end: two pipeline runs in, Markdown out."""

from hof import model, pipeline, report
from tests.conftest import FIXTURE


def test_identical_runs_report_no_changes(tmp_path):
    pipeline.run(tmp_path / "base", FIXTURE)
    pipeline.run(tmp_path / "head", FIXTURE)
    md = report.markdown(tmp_path / "base", tmp_path / "head")
    assert md.startswith("## Hall of Fame report")
    assert "No player crosses the line." in md
    assert "No ranking changes" in md


def test_method_change_shows_movers(tmp_path, monkeypatch):
    pipeline.run(tmp_path / "base", FIXTURE)
    # The placeholder scores majors only; add weeks at No. 1 to force a difference
    monkeypatch.setitem(model.WEIGHTS, "weeks_no1", 0.1)
    pipeline.run(tmp_path / "head", FIXTURE)
    md = report.markdown(tmp_path / "base", tmp_path / "head")
    assert "changed rank" in md
    assert "Kendall" in md
    assert "Biggest moves up" in md
