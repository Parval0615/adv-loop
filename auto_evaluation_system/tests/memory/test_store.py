import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import validate

from auto_evaluation_system.events import LLMInferencePayload, StepEvent, StepType
from auto_evaluation_system.memory import InMemoryMemoryStore
from auto_evaluation_system.sandbox.config import ScenarioConfig
from auto_evaluation_system.sandbox.session import SandboxEnvironment
from auto_evaluation_system.telemetry import TrajectoryRecorder


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "trajectory-v1.schema.json").read_text(encoding="utf-8"))
SCENARIO = ROOT / "configs" / "scenarios" / "p1-sandbox-5step-direct-api.yaml"


def test_memory_write_read_delete() -> None:
    store = InMemoryMemoryStore()
    write_audit = store.write("ns1", "short_term", "k1", {"answer": 42})
    value, read_audit = store.read("ns1", "short_term", "k1")
    delete_audit = store.delete("ns1", "short_term", "k1")
    missing, missing_audit = store.read("ns1", "short_term", "k1")

    assert value == {"answer": 42}
    assert missing is None
    assert write_audit.op == "write"
    assert read_audit.metadata == {"hit": True}
    assert delete_audit.metadata == {"existed": True}
    assert missing_audit.metadata == {"hit": False}


def test_memory_layers_are_isolated() -> None:
    store = InMemoryMemoryStore()
    store.write("ns1", "short_term", "shared", "short")
    store.write("ns1", "long_term", "shared", "long")

    short_value, _ = store.read("ns1", "short_term", "shared")
    long_value, _ = store.read("ns1", "long_term", "shared")

    assert short_value == "short"
    assert long_value == "long"


def test_memory_namespaces_are_isolated() -> None:
    store = InMemoryMemoryStore()
    store.write("ns-a", "episodic", "k1", "a")

    value, _ = store.read("ns-b", "episodic", "k1")

    assert value is None
    assert store.list_namespace("ns-a")[0].value == "a"
    assert store.list_namespace("ns-b") == []


def test_memory_crud_generates_audit_records() -> None:
    store = InMemoryMemoryStore()
    store.write("ns1", "short_term", "k1", "v1", source="test")
    store.read("ns1", "short_term", "k1", source="test")
    store.delete("ns1", "short_term", "missing", source="test")

    audit_log = store.audit_log("ns1")

    assert [record.op for record in audit_log] == ["write", "read", "delete"]
    assert audit_log[2].metadata == {"existed": False}
    assert all(record.source == "test" for record in audit_log)


def test_memory_audit_record_converts_to_payload() -> None:
    store = InMemoryMemoryStore()
    audit = store.write("ns1", "long_term", "k1", "v1")

    payload = audit.to_payload()

    assert payload.op == "write"
    assert payload.namespace == "ns1"
    assert payload.layer == "long_term"
    assert payload.key == "k1"


def test_memory_payload_enters_trajectory_and_validates_schema() -> None:
    config = ScenarioConfig.from_yaml(SCENARIO)
    session = SandboxEnvironment().create_session(config)
    audit = session.memory_store.write(session.memory_namespace, "short_term", "k1", "v1")
    session.emitter.emit(
        StepEvent(
            step_type=StepType.LLM_INFERENCE,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            llm=LLMInferencePayload(
                model="gpt-4o-mini",
                input_messages=[{"role": "user", "content": "remember k1"}],
                turn_index=0,
            ),
            memory_ops=[audit.to_payload()],
        )
    )

    trajectory = TrajectoryRecorder.from_session(session)

    assert trajectory["steps"][0]["memory_ops"][0]["key"] == "k1"
    validate(instance=trajectory, schema=SCHEMA)
