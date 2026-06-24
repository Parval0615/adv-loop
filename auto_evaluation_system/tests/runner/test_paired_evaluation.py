import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auto_evaluation_system.runner import (
    GDMAcceptanceEvaluationResult,
    MISAcceptanceEvaluationResult,
    PairedEvaluationDryRunResult,
    PairedEvaluationReportRecord,
    PairedEvaluationReportSkeleton,
    TRSAcceptanceEvaluationResult,
    build_gdm_paired_report_with_status,
    build_mis_paired_report_with_status,
    build_paired_evaluation_report_skeleton,
    build_trs_paired_report_with_status,
    run_paired_evaluation_dry_run,
    run_gdm_acceptance_evaluation,
    run_mis_acceptance_evaluation,
    run_trs_acceptance_evaluation,
)
from auto_evaluation_system.detection.contracts import DetectorAttribution, DetectorOutput

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE_MANIFEST = ROOT / "datasets" / "acceptance" / "detectors" / "manifest.yaml"
GOLDEN_REPORT = ROOT / "datasets" / "acceptance" / "reports" / "paired-evaluation-report-v0.1.json"
TRS_STATUS_REPORT = ROOT / "datasets" / "acceptance" / "reports" / "paired-evaluation-trs-status-v0.1.json"
GDM_STATUS_REPORT = ROOT / "datasets" / "acceptance" / "reports" / "paired-evaluation-gdm-status-v0.1.json"
MIS_STATUS_REPORT = ROOT / "datasets" / "acceptance" / "reports" / "paired-evaluation-mis-status-v0.1.json"


def test_paired_evaluation_report_skeleton_builds_from_acceptance_fixtures() -> None:
    report = build_paired_evaluation_report_skeleton(
        ACCEPTANCE_MANIFEST,
        repo_root=ROOT,
    )

    assert report.schema_version == "paired-evaluation-report-v0.1"
    assert {record.metric for record in report.records} == {"MIS", "GDM", "TRS"}
    assert {record.test_status for record in report.records} == {"not_run"}


def test_paired_evaluation_report_records_expose_required_fields() -> None:
    report = build_paired_evaluation_report_skeleton(
        ACCEPTANCE_MANIFEST,
        repo_root=ROOT,
    )
    memory_record = next(record for record in report.records if record.metric == "MIS")

    assert memory_record.pair_id == "p2-memory-poison-direct-api"
    assert memory_record.risk_type == "memory_poisoning"
    assert memory_record.expected_decision == "poisoned"
    assert memory_record.evidence_summary
    assert memory_record.failure_notes == []
    assert memory_record.clean_scenario_path.endswith("p2-memory-poison-clean-direct-api.yaml")
    assert memory_record.controlled_scenario_path.endswith("p2-memory-poison-controlled-direct-api.yaml")
    assert memory_record.controlled_trajectory_path.endswith("p2-memory-poison-controlled-direct-api.json")


def test_paired_evaluation_report_record_rejects_empty_evidence_summary() -> None:
    with pytest.raises(ValidationError):
        PairedEvaluationReportRecord(
            pair_id="p2-memory-poison-direct-api",
            risk_type="memory_poisoning",
            metric="MIS",
            attack_spec_id="p2-memory-poison-controlled-direct-api:memory_poisoning:semantic_substitution:medium",
            expected_decision="poisoned",
            evidence_summary=[],
            clean_scenario_path="configs/scenarios/p2-memory-poison-clean-direct-api.yaml",
            controlled_scenario_path="configs/scenarios/p2-memory-poison-controlled-direct-api.yaml",
            controlled_trajectory_path="datasets/annotated/phase2/trajectories/p2-memory-poison-controlled-direct-api.json",
        )


def test_paired_evaluation_golden_report_matches_builder_output() -> None:
    built_report = build_paired_evaluation_report_skeleton(
        ACCEPTANCE_MANIFEST,
        repo_root=ROOT,
    )
    golden_payload = json.loads(GOLDEN_REPORT.read_text(encoding="utf-8"))
    golden_report = PairedEvaluationReportSkeleton.model_validate(golden_payload)

    assert golden_report.model_dump(mode="json") == built_report.model_dump(mode="json")


def test_paired_evaluation_dry_run_matches_golden_fixture() -> None:
    result = run_paired_evaluation_dry_run(
        ACCEPTANCE_MANIFEST,
        repo_root=ROOT,
        golden_report_path=GOLDEN_REPORT,
    )

    assert isinstance(result, PairedEvaluationDryRunResult)
    assert result.matches_golden is True
    assert result.golden_report is not None
    assert {record.test_status for record in result.generated_report.records} == {"not_run"}


def test_paired_evaluation_dry_run_rejects_golden_mismatch(tmp_path: Path) -> None:
    golden_payload = json.loads(GOLDEN_REPORT.read_text(encoding="utf-8"))
    golden_payload["records"][0]["test_status"] = "failed"
    mismatched_golden = tmp_path / "paired-evaluation-report-v0.1.json"
    mismatched_golden.write_text(json.dumps(golden_payload), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        run_paired_evaluation_dry_run(
            ACCEPTANCE_MANIFEST,
            repo_root=ROOT,
            golden_report_path=mismatched_golden,
        )


def test_paired_evaluation_dry_run_does_not_modify_golden_fixture() -> None:
    before = GOLDEN_REPORT.read_bytes()

    run_paired_evaluation_dry_run(
        ACCEPTANCE_MANIFEST,
        repo_root=ROOT,
        golden_report_path=GOLDEN_REPORT,
    )

    assert GOLDEN_REPORT.read_bytes() == before


def test_mis_acceptance_evaluation_matches_expected_decision() -> None:
    result = run_mis_acceptance_evaluation(ACCEPTANCE_MANIFEST, repo_root=ROOT)

    assert isinstance(result, MISAcceptanceEvaluationResult)
    assert result.fixture_id == "mis-p2-memory-poison-direct-api"
    assert result.pair_id == "p2-memory-poison-direct-api"
    assert result.expected_decision == "poisoned"
    assert result.actual_decision == "poisoned"
    assert result.passed is True
    assert result.detector_output.metric == "MIS"


def test_mis_acceptance_evaluation_rejects_manifest_without_mis_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = {"schema_version": "detector-acceptance-v0.1", "records": []}
    full_report = build_paired_evaluation_report_skeleton(ACCEPTANCE_MANIFEST, repo_root=ROOT)
    trs_record = next(record for record in full_report.records if record.metric == "TRS")
    manifest["records"].append(
        {
            "fixture_id": "trs-only",
            "metric": "TRS",
            "scenario_pair_id": trs_record.pair_id,
            "attack_spec_id": trs_record.attack_spec_id,
            "risk_type": trs_record.risk_type,
            "controlled_label": "tampered",
            "scenario_manifest_path": "configs/scenarios/manifest.yaml",
            "clean_scenario_path": trs_record.clean_scenario_path,
            "controlled_scenario_path": trs_record.controlled_scenario_path,
            "controlled_trajectory_path": trs_record.controlled_trajectory_path,
            "expected_decision": trs_record.expected_decision,
            "expected_evidence": trs_record.evidence_summary,
        }
    )
    trs_only_manifest = tmp_path / "detectors.yaml"
    trs_only_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("MIS baseline should not run without a MIS fixture")

    monkeypatch.setattr(
        "auto_evaluation_system.runner.paired_evaluation.run_mis_baseline",
        fail_if_called,
    )

    with pytest.raises(ValueError, match="exactly one MIS"):
        run_mis_acceptance_evaluation(trs_only_manifest, repo_root=ROOT)


def test_trs_acceptance_evaluation_matches_expected_decision() -> None:
    result = run_trs_acceptance_evaluation(ACCEPTANCE_MANIFEST, repo_root=ROOT)

    assert isinstance(result, TRSAcceptanceEvaluationResult)
    assert result.fixture_id == "trs-p2-tool-tamper-direct-api"
    assert result.pair_id == "p2-tool-tamper-direct-api"
    assert result.expected_decision == "high"
    assert result.actual_decision == "high"
    assert result.passed is True
    assert result.detector_output.metric == "TRS"


def test_trs_acceptance_evaluation_rejects_manifest_without_trs_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = json.loads(json.dumps({"schema_version": "detector-acceptance-v0.1", "records": []}))
    full_report = build_paired_evaluation_report_skeleton(ACCEPTANCE_MANIFEST, repo_root=ROOT)
    memory_record = next(record for record in full_report.records if record.metric == "MIS")
    manifest["records"].append(
        {
            "fixture_id": "mis-only",
            "metric": "MIS",
            "scenario_pair_id": memory_record.pair_id,
            "attack_spec_id": memory_record.attack_spec_id,
            "risk_type": memory_record.risk_type,
            "controlled_label": "poisoned",
            "scenario_manifest_path": "configs/scenarios/manifest.yaml",
            "clean_scenario_path": memory_record.clean_scenario_path,
            "controlled_scenario_path": memory_record.controlled_scenario_path,
            "controlled_trajectory_path": memory_record.controlled_trajectory_path,
            "expected_decision": memory_record.expected_decision,
            "expected_evidence": memory_record.evidence_summary,
        }
    )
    mis_only_manifest = tmp_path / "detectors.yaml"
    mis_only_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("TRS baseline should not run without a TRS fixture")

    monkeypatch.setattr(
        "auto_evaluation_system.runner.paired_evaluation.run_trs_baseline",
        fail_if_called,
    )

    with pytest.raises(ValueError, match="exactly one TRS"):
        run_trs_acceptance_evaluation(mis_only_manifest, repo_root=ROOT)


def test_gdm_acceptance_evaluation_matches_expected_decision() -> None:
    result = run_gdm_acceptance_evaluation(ACCEPTANCE_MANIFEST, repo_root=ROOT)

    assert isinstance(result, GDMAcceptanceEvaluationResult)
    assert result.fixture_id == "gdm-p2-goal-perturb-direct-api"
    assert result.pair_id == "p2-goal-perturb-direct-api"
    assert result.expected_decision == "drifted"
    assert result.actual_decision == "drifted"
    assert result.passed is True
    assert result.detector_output.metric == "GDM"


def test_gdm_acceptance_evaluation_rejects_manifest_without_gdm_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = {"schema_version": "detector-acceptance-v0.1", "records": []}
    full_report = build_paired_evaluation_report_skeleton(ACCEPTANCE_MANIFEST, repo_root=ROOT)
    trs_record = next(record for record in full_report.records if record.metric == "TRS")
    manifest["records"].append(
        {
            "fixture_id": "trs-only",
            "metric": "TRS",
            "scenario_pair_id": trs_record.pair_id,
            "attack_spec_id": trs_record.attack_spec_id,
            "risk_type": trs_record.risk_type,
            "controlled_label": "tampered",
            "scenario_manifest_path": "configs/scenarios/manifest.yaml",
            "clean_scenario_path": trs_record.clean_scenario_path,
            "controlled_scenario_path": trs_record.controlled_scenario_path,
            "controlled_trajectory_path": trs_record.controlled_trajectory_path,
            "expected_decision": trs_record.expected_decision,
            "expected_evidence": trs_record.evidence_summary,
        }
    )
    trs_only_manifest = tmp_path / "detectors.yaml"
    trs_only_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("GDM baseline should not run without a GDM fixture")

    monkeypatch.setattr(
        "auto_evaluation_system.runner.paired_evaluation.run_gdm_baseline",
        fail_if_called,
    )

    with pytest.raises(ValueError, match="exactly one GDM"):
        run_gdm_acceptance_evaluation(trs_only_manifest, repo_root=ROOT)


def test_mis_paired_report_status_marks_only_mis_record_passed() -> None:
    report = build_mis_paired_report_with_status(ACCEPTANCE_MANIFEST, repo_root=ROOT)

    mis_record = next(record for record in report.records if record.metric == "MIS")
    untouched_records = [record for record in report.records if record.metric != "MIS"]
    assert mis_record.test_status == "passed"
    assert mis_record.failure_notes == []
    assert {record.test_status for record in untouched_records} == {"not_run"}


def test_trs_paired_report_status_marks_only_trs_record_passed() -> None:
    report = build_trs_paired_report_with_status(ACCEPTANCE_MANIFEST, repo_root=ROOT)

    trs_record = next(record for record in report.records if record.metric == "TRS")
    untouched_records = [record for record in report.records if record.metric != "TRS"]
    assert trs_record.test_status == "passed"
    assert trs_record.failure_notes == []
    assert {record.test_status for record in untouched_records} == {"not_run"}


def test_gdm_paired_report_status_marks_only_gdm_record_passed() -> None:
    report = build_gdm_paired_report_with_status(ACCEPTANCE_MANIFEST, repo_root=ROOT)

    gdm_record = next(record for record in report.records if record.metric == "GDM")
    untouched_records = [record for record in report.records if record.metric != "GDM"]
    assert gdm_record.test_status == "passed"
    assert gdm_record.failure_notes == []
    assert {record.test_status for record in untouched_records} == {"not_run"}


def test_mis_paired_report_status_tracks_failed_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detector_output = DetectorOutput(
        metric="MIS",
        score=0.2,
        decision="clean",
        attribution=[
            DetectorAttribution(
                evidence_type="missing_memory_poisoning_evidence",
                field_path="steps[].memory_ops",
                summary="No memory poisoning signal was found.",
            )
        ],
        failure_notes=["No memory poisoning operation found."],
    )
    failed_result = MISAcceptanceEvaluationResult(
        fixture_id="mis-p2-memory-poison-direct-api",
        pair_id="p2-memory-poison-direct-api",
        expected_decision="poisoned",
        actual_decision="clean",
        passed=False,
        detector_output=detector_output,
    )

    monkeypatch.setattr(
        "auto_evaluation_system.runner.paired_evaluation.run_mis_acceptance_evaluation",
        lambda *args, **kwargs: failed_result,
    )

    report = build_mis_paired_report_with_status(ACCEPTANCE_MANIFEST, repo_root=ROOT)
    mis_record = next(record for record in report.records if record.metric == "MIS")

    assert mis_record.test_status == "failed"
    assert mis_record.failure_notes == [
        "Expected MIS decision poisoned, got clean.",
        "No memory poisoning operation found.",
    ]


def test_gdm_paired_report_status_tracks_failed_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detector_output = DetectorOutput(
        metric="GDM",
        score=0.2,
        decision="aligned",
        attribution=[
            DetectorAttribution(
                evidence_type="missing_goal_drift_evidence",
                field_path="goal.text",
                summary="No goal drift signal was found.",
            )
        ],
        failure_notes=["No goal perturbation injection found."],
    )
    failed_result = GDMAcceptanceEvaluationResult(
        fixture_id="gdm-p2-goal-perturb-direct-api",
        pair_id="p2-goal-perturb-direct-api",
        expected_decision="drifted",
        actual_decision="aligned",
        passed=False,
        detector_output=detector_output,
    )

    monkeypatch.setattr(
        "auto_evaluation_system.runner.paired_evaluation.run_gdm_acceptance_evaluation",
        lambda *args, **kwargs: failed_result,
    )

    report = build_gdm_paired_report_with_status(ACCEPTANCE_MANIFEST, repo_root=ROOT)
    gdm_record = next(record for record in report.records if record.metric == "GDM")

    assert gdm_record.test_status == "failed"
    assert gdm_record.failure_notes == [
        "Expected GDM decision drifted, got aligned.",
        "No goal perturbation injection found.",
    ]


def test_trs_paired_report_status_tracks_failed_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detector_output = DetectorOutput(
        metric="TRS",
        score=0.2,
        decision="low",
        attribution=[
            DetectorAttribution(
                evidence_type="missing_tool_tampering_evidence",
                field_path="steps[].tool_call.response",
                summary="No tamper signal was found.",
            )
        ],
        failure_notes=["No tampered tool response found."],
    )
    failed_result = TRSAcceptanceEvaluationResult(
        fixture_id="trs-p2-tool-tamper-direct-api",
        pair_id="p2-tool-tamper-direct-api",
        expected_decision="high",
        actual_decision="low",
        passed=False,
        detector_output=detector_output,
    )

    monkeypatch.setattr(
        "auto_evaluation_system.runner.paired_evaluation.run_trs_acceptance_evaluation",
        lambda *args, **kwargs: failed_result,
    )

    report = build_trs_paired_report_with_status(ACCEPTANCE_MANIFEST, repo_root=ROOT)
    trs_record = next(record for record in report.records if record.metric == "TRS")

    assert trs_record.test_status == "failed"
    assert trs_record.failure_notes == [
        "Expected TRS decision high, got low.",
        "No tampered tool response found.",
    ]


def test_trs_paired_report_status_matches_fixture_snapshot() -> None:
    report = build_trs_paired_report_with_status(ACCEPTANCE_MANIFEST, repo_root=ROOT)
    fixture_payload = json.loads(TRS_STATUS_REPORT.read_text(encoding="utf-8"))
    fixture_report = PairedEvaluationReportSkeleton.model_validate(fixture_payload)

    assert report.model_dump(mode="json") == fixture_report.model_dump(mode="json")


def test_gdm_paired_report_status_matches_fixture_snapshot() -> None:
    report = build_gdm_paired_report_with_status(ACCEPTANCE_MANIFEST, repo_root=ROOT)
    fixture_payload = json.loads(GDM_STATUS_REPORT.read_text(encoding="utf-8"))
    fixture_report = PairedEvaluationReportSkeleton.model_validate(fixture_payload)

    assert report.model_dump(mode="json") == fixture_report.model_dump(mode="json")


def test_mis_paired_report_status_matches_fixture_snapshot() -> None:
    report = build_mis_paired_report_with_status(ACCEPTANCE_MANIFEST, repo_root=ROOT)
    fixture_payload = json.loads(MIS_STATUS_REPORT.read_text(encoding="utf-8"))
    fixture_report = PairedEvaluationReportSkeleton.model_validate(fixture_payload)

    assert report.model_dump(mode="json") == fixture_report.model_dump(mode="json")
