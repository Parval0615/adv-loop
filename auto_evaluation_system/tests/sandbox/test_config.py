from pathlib import Path


from auto_evaluation_system.sandbox.config import ScenarioConfig


ROOT = Path(__file__).resolve().parents[2]


def test_load_direct_api_scenario() -> None:
    path = ROOT / "configs" / "scenarios" / "p1-sandbox-5step-direct-api.yaml"
    config = ScenarioConfig.from_yaml(path)
    assert config.agent.framework == "direct_api"
    assert config.runner.max_steps == 5


def test_load_langgraph_scenario() -> None:
    path = ROOT / "configs" / "scenarios" / "p1-sandbox-5step-langgraph.yaml"
    config = ScenarioConfig.from_yaml(path)
    assert config.agent.framework == "langgraph"


def test_cassette_path_resolution() -> None:
    path = ROOT / "configs" / "scenarios" / "p1-sandbox-5step-direct-api.yaml"
    config = ScenarioConfig.from_yaml(path)
    cassette = ROOT / "tests" / "cassettes" / "direct_api" / config.experiment_id / "seed_42.yaml"
    assert cassette.exists()
