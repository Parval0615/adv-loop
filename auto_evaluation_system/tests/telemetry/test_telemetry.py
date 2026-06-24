import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import validate

from auto_evaluation_system.events import (
    LLMInferencePayload,
    MaxStepsExceeded,
    MemoryOpPayload,
    StepEvent,
    StepType,
)
from auto_evaluation_system.sandbox.config import ScenarioConfig
from auto_evaluation_system.sandbox.session import SandboxEnvironment
from auto_evaluation_system.telemetry import TelemetryStepEmitter, TrajectoryRecorder


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "trajectory-v1.schema.json").read_text(encoding="utf-8"))
SCENARIO = ROOT / "configs" / "scenarios" / "p1-sandbox-5step-direct-api.yaml"


def make_llm_event(
    messages: list[dict] | None = None,
    memory_ops: list[MemoryOpPayload] | None = None,
    state_delta: dict | None = None,
) -> StepEvent:
    return StepEvent(
        step_type=StepType.LLM_INFERENCE,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        llm=LLMInferencePayload(
            model="gpt-4o-mini",
            input_messages=messages or [{"role": "user", "content": "hello"}],
            turn_index=0,
        ),
        memory_ops=memory_ops or [],
        state_delta=state_delta,
    )


def make_session():
    config = ScenarioConfig.from_yaml(SCENARIO)
    return SandboxEnvironment().create_session(config)


def test_telemetry_emitter_assigns_step_index() -> None:
    emitter = TelemetryStepEmitter(max_steps=2)

    assert emitter.emit(make_llm_event()) == 0
    assert emitter.emit(make_llm_event()) == 1
    assert [event.step_index for event in emitter.events()] == [0, 1]


def test_telemetry_emitter_enforces_max_steps() -> None:
    emitter = TelemetryStepEmitter(max_steps=1)
    emitter.emit(make_llm_event())

    with pytest.raises(MaxStepsExceeded):
        emitter.emit(make_llm_event())


def test_telemetry_emitter_deep_copies_events() -> None:
    messages = [{"role": "user", "content": "original"}]
    event = make_llm_event(messages=messages)
    emitter = TelemetryStepEmitter()
    emitter.emit(event)

    event.llm.input_messages[0]["content"] = "mutated"
    messages[0]["content"] = "also mutated"

    stored = emitter.events()[0]
    assert stored.llm is not None
    assert stored.llm.input_messages[0]["content"] == "original"


def test_trajectory_recorder_matches_schema() -> None:
    session = make_session()
    session.emitter.emit(make_llm_event())

    trajectory = TrajectoryRecorder.from_session(session)

    validate(instance=trajectory, schema=SCHEMA)


def test_trajectory_recorder_preserves_memory_ops_and_state_delta() -> None:
    session = make_session()
    memory_op = MemoryOpPayload(
        op="write",
        namespace=session.memory_namespace,
        key="k1",
        layer="short_term",
    )
    session.emitter.emit(
        make_llm_event(
            memory_ops=[memory_op],
            state_delta={"memory": {"wrote": "k1"}},
        )
    )

    trajectory = TrajectoryRecorder.from_session(session)
    first_step = trajectory["steps"][0]

    assert first_step["memory_ops"] == [memory_op.model_dump()]
    assert first_step["state_delta"] == {"memory": {"wrote": "k1"}}


def test_telemetry_overhead_is_numeric() -> None:
    session = make_session()
    session.emitter.emit(make_llm_event())

    trajectory = TrajectoryRecorder.from_session(session)
    overhead = trajectory["metadata"]["telemetry_overhead_ms"]

    assert isinstance(overhead, float)
    assert overhead >= 0.0


def test_telemetry_does_not_mutate_llm_input_messages() -> None:
    messages = [{"role": "system", "content": "stay fixed"}, {"role": "user", "content": "hi"}]
    before = deepcopy(messages)
    session = make_session()
    session.emitter.emit(make_llm_event(messages=messages))

    TrajectoryRecorder.from_session(session)

    assert messages == before
