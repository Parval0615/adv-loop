from __future__ import annotations

import json
from pathlib import Path

from arena.eval import run_eval


def test_arena_eval_writes_reports_and_thresholds(tmp_path: Path) -> None:
    report = run_eval(tmp_path)

    assert (tmp_path / "arena_eval_report.json").exists()
    assert (tmp_path / "arena_eval_report.md").exists()
    assert report["case_count"] >= 4
    assert report["metrics"]["passed_thresholds"]["trace_completeness"] is True
    assert report["metrics"]["passed_thresholds"]["synthetic_injection_recall"] is True
    assert report["metrics"]["passed_thresholds"]["policy_decision_correctness"] is True
    assert report["metrics"]["passed_thresholds"]["coverage_complete"] is True
    assert report["metrics"]["coverage"]["missing"] == {
        "groups": [],
        "source_types": [],
        "policy_rules": [],
        "evasion_tags": [],
    }

    payload = json.loads((tmp_path / "arena_eval_report.json").read_text(encoding="utf-8"))
    assert payload["metrics"]["benign_false_positive_rate"] <= 0.05
