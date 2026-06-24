import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import validate

from auto_evaluation_system.events import LLMInferencePayload, StepEvent, StepType
from auto_evaluation_system.runner import ExperimentRunner
from auto_evaluation_system.sandbox.config import ScenarioConfig
from auto_evaluation_system.sandbox.session import SandboxEnvironment
from auto_evaluation_system.telemetry import TrajectoryRecorder


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "trajectory-v1.schema.json").read_text(encoding="utf-8"))
SCENARIO = ROOT / "configs" / "scenarios" / "p1-sandbox-5step-direct-api.yaml"


def test_runner_sandbox_telemetry_results_chain(tmp_path: Path) -> None:
    result = ExperimentRunner(results_root=tmp_path / "runs").run_scenario(SCENARIO)

    assert result.output_dir.exists()
    validate(instance=result.trajectory, schema=SCHEMA)
    assert result.trajectory["experiment_id"] == "p1-sandbox-5step-direct-api"


def test_sandbox_memory_telemetry_chain() -> None:
    config = ScenarioConfig.from_yaml(SCENARIO)
    session = SandboxEnvironment().create_session(config)
    audit = session.memory_store.write(
        session.memory_namespace,
        "short_term",
        "k1",
        {"fact": "value"},
    )
    session.emitter.emit(
        StepEvent(
            step_type=StepType.LLM_INFERENCE,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            llm=LLMInferencePayload(
                model="gpt-4o-mini",
                input_messages=[{"role": "user", "content": "use memory"}],
                turn_index=0,
            ),
            memory_ops=[audit.to_payload()],
        )
    )

    trajectory = TrajectoryRecorder.from_session(session)

    validate(instance=trajectory, schema=SCHEMA)
    assert trajectory["steps"][0]["memory_ops"][0]["namespace"] == session.memory_namespace
