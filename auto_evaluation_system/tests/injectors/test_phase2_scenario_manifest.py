from pathlib import Path

from auto_attack_system.attack_spec import load_scenario_manifest
from auto_evaluation_system.sandbox.config import ScenarioConfig

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "configs" / "scenarios" / "manifest.yaml"


def test_phase2_scenario_manifest_pairs_clean_and_controlled_scenarios() -> None:
    manifest = load_scenario_manifest(MANIFEST)

    assert {record.risk_type for record in manifest.records} == {
        "memory_poisoning",
        "tool_tampering",
        "goal_perturbation",
    }

    for record in manifest.records:
        clean_path = ROOT / record.clean_scenario
        controlled_path = ROOT / record.controlled_scenario
        assert clean_path.exists()
        assert controlled_path.exists()

        clean = ScenarioConfig.from_yaml(clean_path)
        controlled = ScenarioConfig.from_yaml(controlled_path)

        assert clean.injection.mode == "none"
        assert controlled.injection.mode == "controlled"
        assert clean.reproducibility.seed == record.seed
        assert controlled.reproducibility.seed == record.seed
        assert clean.agent.framework == record.framework
        assert controlled.agent.framework == record.framework
        assert clean.agent.goal == controlled.agent.goal
        assert clean.tools.mode == controlled.tools.mode == "mock"

        experiment_id, kind, strategy, intensity = record.attack_spec_id.split(":")
        assert experiment_id == controlled.experiment_id
        assert kind == controlled.injection.kind == record.risk_type
        assert strategy == controlled.injection.strategy
        assert intensity == controlled.injection.intensity
        assert controlled.injection.label == record.controlled_label
