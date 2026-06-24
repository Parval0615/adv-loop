import json
from pathlib import Path

import pytest
from jsonschema import validate
from pydantic import ValidationError

from auto_attack_system.attack_spec import load_scenario_manifest
from auto_evaluation_system.detection.contracts import (
    DetectorAttribution,
    DetectorInput,
    DetectorOutput,
    load_acceptance_fixture_manifest,
)
from auto_evaluation_system.sandbox.config import ScenarioConfig

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "trajectory-v1.schema.json").read_text(encoding="utf-8"))
FIXTURE_MANIFEST = ROOT / "datasets" / "acceptance" / "detectors" / "manifest.yaml"


def test_detector_contract_accepts_minimal_input_and_output() -> None:
    detector_input = DetectorInput(
        metric="MIS",
        scenario_pair_id="p2-memory-poison-direct-api",
        controlled_trajectory_path="datasets/annotated/phase2/trajectories/p2-memory-poison-controlled-direct-api.json",
        attack_spec_id="p2-memory-poison-controlled-direct-api:memory_poisoning:semantic_substitution:medium",
    )
    detector_output = DetectorOutput(
        metric=detector_input.metric,
        score=0.8,
        decision="poisoned",
        attribution=[
            DetectorAttribution(
                evidence_type="memory_op",
                step_index=0,
                field_path="steps[0].memory_ops",
                summary="controlled memory poisoning wrote short-term memory",
            )
        ],
    )

    assert detector_output.metric == detector_input.metric
    assert detector_output.attribution[0].step_index == 0


def test_detector_contract_rejects_invalid_score_or_empty_attribution() -> None:
    with pytest.raises(ValidationError):
        DetectorOutput(metric="MIS", score=1.2, decision="poisoned", attribution=[])

    with pytest.raises(ValidationError):
        DetectorInput(
            metric="UNKNOWN",
            scenario_pair_id="p2-memory-poison-direct-api",
            controlled_trajectory_path="datasets/annotated/phase2/trajectories/p2-memory-poison-controlled-direct-api.json",
            attack_spec_id="p2-memory-poison-controlled-direct-api:memory_poisoning:semantic_substitution:medium",
        )


def test_acceptance_fixture_manifest_points_to_existing_phase2_artifacts() -> None:
    fixture_manifest = load_acceptance_fixture_manifest(FIXTURE_MANIFEST)

    assert fixture_manifest.schema_version == "detector-acceptance-v0.1"
    assert {record.metric for record in fixture_manifest.records} == {"MIS", "GDM", "TRS"}

    for record in fixture_manifest.records:
        scenario_manifest = load_scenario_manifest(ROOT / record.scenario_manifest_path)
        scenario_pair = next(
            item for item in scenario_manifest.records if item.pair_id == record.scenario_pair_id
        )
        assert scenario_pair.attack_spec_id == record.attack_spec_id
        assert scenario_pair.risk_type == record.risk_type

        clean = ScenarioConfig.from_yaml(ROOT / record.clean_scenario_path)
        controlled = ScenarioConfig.from_yaml(ROOT / record.controlled_scenario_path)
        assert clean.injection.mode == "none"
        assert controlled.injection.mode == "controlled"
        assert controlled.injection.kind == record.risk_type
        assert controlled.injection.label == record.controlled_label

        trajectory = json.loads((ROOT / record.controlled_trajectory_path).read_text(encoding="utf-8"))
        validate(instance=trajectory, schema=SCHEMA)
        injection = trajectory["metadata"]["injections"][0]
        assert injection["injection_id"] == record.attack_spec_id
        assert injection["label"] == record.controlled_label
        assert record.expected_evidence
