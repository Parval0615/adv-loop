import json
from pathlib import Path

import pytest

from auto_evaluation_system.detection import run_mis_baseline
from auto_evaluation_system.detection.contracts import (
    AcceptanceFixtureRecord,
    DetectorInput,
    load_acceptance_fixture_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_MANIFEST = ROOT / "datasets" / "acceptance" / "detectors" / "manifest.yaml"


def test_mis_baseline_detects_memory_poisoning_acceptance_fixture() -> None:
    detector_input = _detector_input_for_metric("MIS")

    output = run_mis_baseline(detector_input)

    field_paths = {item.field_path for item in output.attribution}
    assert output.metric == "MIS"
    assert output.decision == "poisoned"
    assert output.score >= 0.8
    assert "metadata.injections" in field_paths
    assert "steps[0].memory_ops" in field_paths
    assert "steps[0].state_delta.injection" in field_paths


def test_mis_baseline_rejects_non_mis_input() -> None:
    detector_input = _detector_input_for_metric("GDM")

    with pytest.raises(ValueError, match="MIS baseline"):
        run_mis_baseline(detector_input)


def test_mis_baseline_returns_clean_when_poisoning_evidence_is_missing(tmp_path: Path) -> None:
    detector_input = _detector_input_for_metric("MIS")
    trajectory_path = ROOT / detector_input.controlled_trajectory_path
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    trajectory["metadata"].pop("injections", None)
    trajectory["steps"][0].pop("memory_ops", None)
    trajectory["steps"][0].pop("state_delta", None)

    candidate_path = tmp_path / "missing-memory-poisoning-evidence.json"
    candidate_path.write_text(json.dumps(trajectory), encoding="utf-8")
    candidate_input = detector_input.model_copy(
        update={"controlled_trajectory_path": str(candidate_path)}
    )

    output = run_mis_baseline(candidate_input)

    assert output.metric == "MIS"
    assert output.decision == "clean"
    assert output.score <= 0.5
    assert output.failure_notes
    assert output.attribution[0].evidence_type == "missing_memory_poisoning_evidence"


def _detector_input_for_metric(metric: str) -> DetectorInput:
    manifest = load_acceptance_fixture_manifest(FIXTURE_MANIFEST)
    record = next(item for item in manifest.records if item.metric == metric)
    return _input_from_record(record)


def _input_from_record(record: AcceptanceFixtureRecord) -> DetectorInput:
    return DetectorInput(
        metric=record.metric,
        scenario_pair_id=record.scenario_pair_id,
        controlled_trajectory_path=record.controlled_trajectory_path,
        attack_spec_id=record.attack_spec_id,
    )
