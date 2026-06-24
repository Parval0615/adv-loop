from pathlib import Path

import pytest
from pydantic import ValidationError

from auto_attack_system.attack_spec import AttackSpec, load_scenario_manifest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "auto_evaluation_system" / "configs" / "scenarios" / "manifest.yaml"


def test_attack_spec_accepts_phase2_shape() -> None:
    spec = AttackSpec(
        attack_id="p2-memory-poison-controlled-direct-api:memory_poisoning:semantic_substitution:medium",
        risk_type="memory_poisoning",
        strategy="semantic_substitution",
        intensity="medium",
        target="short_term",
        label="poisoned",
        goal="Query weather, search news, summarize in text.",
        success_criteria=["controlled trajectory records memory poisoning ground truth"],
        metadata={"split": "dev"},
    )

    assert spec.risk_type == "memory_poisoning"
    assert spec.metadata["split"] == "dev"


def test_scenario_manifest_loads_phase2_pairs() -> None:
    manifest = load_scenario_manifest(MANIFEST)

    assert manifest.schema_version == "attack-scenarios-v0.1"
    assert {record.risk_type for record in manifest.records} == {
        "memory_poisoning",
        "tool_tampering",
        "goal_perturbation",
    }


def test_attack_spec_rejects_invalid_shape() -> None:
    with pytest.raises(ValidationError):
        AttackSpec(
            attack_id="invalid",
            risk_type="unknown",
            strategy="semantic_substitution",
            intensity="medium",
            target="short_term",
            label="poisoned",
            goal="Query weather, search news, summarize in text.",
            success_criteria=["must be non-empty"],
        )

    with pytest.raises(ValidationError):
        AttackSpec(
            attack_id="invalid",
            risk_type="memory_poisoning",
            strategy="semantic_substitution",
            intensity="medium",
            target="short_term",
            label="poisoned",
            goal="Query weather, search news, summarize in text.",
            success_criteria=[],
        )
