import json

from jsonschema import validate

from auto_evaluation_system.sandbox.run import run_scenario
from .conftest import ROOT, assert_golden_step_sequence, normalize_trajectory


SCHEMA = json.loads((ROOT / "schemas" / "trajectory-v1.schema.json").read_text(encoding="utf-8"))


def test_langgraph_replay_produces_golden_structure() -> None:
    scenario = ROOT / "configs" / "scenarios" / "p1-sandbox-5step-langgraph.yaml"
    trajectory = run_scenario(str(scenario))
    validate(instance=trajectory, schema=SCHEMA)
    assert_golden_step_sequence(trajectory)


def test_langgraph_matches_direct_api_step_sequence() -> None:
    direct = run_scenario(str(ROOT / "configs" / "scenarios" / "p1-sandbox-5step-direct-api.yaml"))
    langgraph = run_scenario(str(ROOT / "configs" / "scenarios" / "p1-sandbox-5step-langgraph.yaml"))
    assert [s["step_type"] for s in direct["steps"]] == [s["step_type"] for s in langgraph["steps"]]


def test_langgraph_replay_is_deterministic() -> None:
    scenario = ROOT / "configs" / "scenarios" / "p1-sandbox-5step-langgraph.yaml"
    first = normalize_trajectory(run_scenario(str(scenario)))
    second = normalize_trajectory(run_scenario(str(scenario)))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
