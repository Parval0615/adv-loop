import json
from pathlib import Path

from auto_evaluation_system.runner import (
    ClosedLoopEvaluationReport,
    run_closed_loop_evaluation,
)

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_MANIFEST = ROOT / "configs" / "scenarios" / "manifest.yaml"
ACCEPTANCE_MANIFEST = ROOT / "datasets" / "acceptance" / "detectors" / "manifest.yaml"


def test_closed_loop_evaluation_runs_all_attack_defense_pairs(tmp_path: Path) -> None:
    report = run_closed_loop_evaluation(
        SCENARIO_MANIFEST,
        ACCEPTANCE_MANIFEST,
        repo_root=ROOT,
        results_root=tmp_path / "closed-loop",
    )

    assert isinstance(report, ClosedLoopEvaluationReport)
    assert report.schema_version == "closed-loop-report-v0.1"
    assert {record.pair_id for record in report.records} == {
        "p2-memory-poison-direct-api",
        "p2-tool-tamper-direct-api",
        "p2-goal-perturb-direct-api",
    }
    assert {record.passed for record in report.records} == {True}


def test_closed_loop_evaluation_records_detector_and_defense_decisions(tmp_path: Path) -> None:
    report = run_closed_loop_evaluation(
        SCENARIO_MANIFEST,
        ACCEPTANCE_MANIFEST,
        repo_root=ROOT,
        results_root=tmp_path / "closed-loop",
    )

    expected_detector_decisions = {
        "MIS": "poisoned",
        "TRS": "high",
        "GDM": "drifted",
    }
    expected_guards = {
        "memory_poisoning": "memory_guard",
        "tool_tampering": "tool_guard",
        "goal_perturbation": "goal_guard",
    }

    for record in report.records:
        assert record.detector_output.decision == expected_detector_decisions[record.metric]
        assert record.clean_defense_decision.allowed is True
        assert record.clean_defense_decision.decision == "allow"
        assert record.controlled_defense_decision.allowed is False
        assert record.controlled_defense_decision.decision == "block"
        assert record.controlled_defense_decision.guard == expected_guards[record.risk_type]
        assert record.audit_integrity.valid is True
        assert record.audit_integrity.total_entries == 2
        assert record.failure_notes == []


def test_closed_loop_evaluation_persists_report_and_trajectory_defense_metadata(tmp_path: Path) -> None:
    results_root = tmp_path / "closed-loop"
    report = run_closed_loop_evaluation(
        SCENARIO_MANIFEST,
        ACCEPTANCE_MANIFEST,
        repo_root=ROOT,
        results_root=results_root,
    )

    report_path = results_root / "closed-loop-report-v0.1.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_payload["schema_version"] == "closed-loop-report-v0.1"
    assert len(report_payload["records"]) == 3
    assert report.metadata["report_path"] == str(report_path)

    for record in report.records:
        clean_trajectory = json.loads((Path(record.clean_run_path) / "trajectory.json").read_text(encoding="utf-8"))
        controlled_trajectory = json.loads(
            (Path(record.controlled_run_path) / "trajectory.json").read_text(encoding="utf-8")
        )

        assert clean_trajectory["metadata"]["defense_decisions"][0]["allowed"] is True
        assert controlled_trajectory["metadata"]["defense_decisions"][0]["allowed"] is False
        assert (Path(record.controlled_run_path) / "defense-audit.log").exists()
