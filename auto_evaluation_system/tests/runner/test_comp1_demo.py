import json
from pathlib import Path

from auto_evaluation_system.runner import Comp1DemoResult, run_comp1_demo

ROOT = Path(__file__).resolve().parents[3]


def test_comp1_demo_writes_full_artifact_bundle(tmp_path: Path) -> None:
    result = run_comp1_demo(
        repo_root=ROOT,
        runs_root=tmp_path / "runs",
        timestamp="20260101T000000Z",
    )

    assert isinstance(result, Comp1DemoResult)
    run_dir = tmp_path / "runs" / "20260101T000000Z"
    assert result.run_dir == run_dir

    for name in ("trace.jsonl", "report.json", "guard_decisions.json", "audit_refs.json", "summary.md"):
        assert (run_dir / name).exists(), f"missing artifact: {name}"


def test_comp1_demo_metrics_show_full_mitigation(tmp_path: Path) -> None:
    result = run_comp1_demo(
        repo_root=ROOT,
        runs_root=tmp_path / "runs",
        timestamp="20260101T000000Z",
    )

    metrics = result.metrics
    assert metrics["total_attack_pairs"] == 3
    assert metrics["threat_category_count"] == 3
    assert metrics["asr_before_defense"] == 1.0
    assert metrics["asr_after_defense"] == 0.0
    assert metrics["mitigation_effectiveness"] == 1.0
    assert metrics["false_positive_rate"] == 0.0
    assert metrics["audit_chain_valid"] is True
    assert metrics["all_passed"] is True


def test_comp1_demo_trace_covers_all_closed_loop_stages(tmp_path: Path) -> None:
    result = run_comp1_demo(
        repo_root=ROOT,
        runs_root=tmp_path / "runs",
        timestamp="20260101T000000Z",
    )

    trace_lines = (result.run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    stages = {json.loads(line)["stage"] for line in trace_lines}
    assert stages == {
        "attack.plan",
        "target.clean",
        "target.controlled",
        "evaluation",
        "defense.clean",
        "defense.controlled",
        "audit",
    }


def test_comp1_demo_report_has_attack_plans_and_attribution(tmp_path: Path) -> None:
    result = run_comp1_demo(
        repo_root=ROOT,
        runs_root=tmp_path / "runs",
        timestamp="20260101T000000Z",
    )

    payload = json.loads((result.run_dir / "report.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "comp1-demo-report-v0.1"
    assert set(payload["attack_plans"]) == {
        "p2-memory-poison-direct-api",
        "p2-tool-tamper-direct-api",
        "p2-goal-perturb-direct-api",
    }
    assert len(payload["damage_attribution"]) == 3
    for entry in payload["damage_attribution"]:
        assert entry["blocked_by_defense"] is True
        assert entry["attribution"]
