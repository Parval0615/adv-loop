import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import validate

from auto_evaluation_system.runner import ExperimentRunner, diff_trajectories


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "trajectory-v1.schema.json").read_text(encoding="utf-8"))
SCENARIO = ROOT / "configs" / "scenarios" / "p1-sandbox-5step-direct-api.yaml"


def test_runner_writes_result_artifacts(tmp_path: Path) -> None:
    runner = ExperimentRunner(results_root=tmp_path / "runs")

    result = runner.run_scenario(SCENARIO)

    assert (result.output_dir / "scenario.yaml").exists()
    assert (result.output_dir / "trajectory.json").exists()
    assert (result.output_dir / "metadata.json").exists()
    assert result.metadata["experiment_id"] == result.experiment_id
    assert result.metadata["seed"] == result.seed
    assert result.metadata["framework"] == "direct_api"
    assert result.metadata["output_dir"] == str(result.output_dir)


def test_runner_writes_schema_valid_trajectory(tmp_path: Path) -> None:
    result = ExperimentRunner(results_root=tmp_path / "runs").run_scenario(SCENARIO)
    trajectory = json.loads((result.output_dir / "trajectory.json").read_text(encoding="utf-8"))

    validate(instance=trajectory, schema=SCHEMA)


def test_runner_repeated_runs_create_distinct_directories(tmp_path: Path) -> None:
    runner = ExperimentRunner(results_root=tmp_path / "runs")

    first = runner.run_scenario(SCENARIO)
    second = runner.run_scenario(SCENARIO)

    assert first.output_dir != second.output_dir
    assert first.output_dir.exists()
    assert second.output_dir.exists()


def test_runner_parallel_scenario_raises(tmp_path: Path) -> None:
    data = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    data["runner"]["parallel"] = True
    scenario = tmp_path / "parallel.yaml"
    scenario.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(NotImplementedError):
        ExperimentRunner(results_root=tmp_path / "runs").run_scenario(scenario)


def test_diff_trajectories_detects_changes(tmp_path: Path) -> None:
    baseline = ExperimentRunner(results_root=tmp_path / "runs").run_scenario(SCENARIO).trajectory
    candidate = deepcopy(baseline)
    candidate["steps"][-1]["llm"]["output_content"] = "changed"
    candidate["steps"][1]["tool_call"]["name"] = "changed_tool"

    diff = diff_trajectories(baseline, candidate)

    assert diff["step_count"]["changed"] is False
    assert diff["step_type_sequence"]["changed"] is False
    assert diff["tool_call_sequence"]["changed"] is True
    assert diff["final_llm_output"]["changed"] is True
