from __future__ import annotations

from pathlib import Path

from arena.eval import run_eval
from sentinel_console import generate_console


def test_static_console_contains_required_views(tmp_path: Path) -> None:
    eval_dir = tmp_path / "eval"
    run_eval(eval_dir)

    index = generate_console(eval_dir, tmp_path / "console")
    html = index.read_text(encoding="utf-8")

    assert index.exists()
    assert (index.parent / "assets" / "style.css").exists()
    assert (index.parent / "assets" / "dag.svg").exists()
    assert (index.parent / "assets" / "timeline.svg").exists()
    assert "DAG View" in html
    assert "Timeline View" in html
    assert "Verdict Panel" in html
    assert "Decision Stream" in html
    assert "Policy Alerts And Trace Links" in html
    assert "Local deterministic arena review" in html
