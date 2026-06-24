from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_STEP_TYPES = [
    "llm_inference",
    "tool_call",
    "llm_inference",
    "tool_call",
    "llm_inference",
]


def normalize_trajectory(trajectory: dict) -> dict:
    normalized = deepcopy(trajectory)
    normalized["session_id"] = "normalized-session"
    for step in normalized.get("steps", []):
        step["timestamp"] = "NORMALIZED"
        if "llm" in step and step["llm"].get("latency_ms") is not None:
            step["llm"]["latency_ms"] = 0.0
        if "tool_call" in step:
            step["tool_call"]["latency_ms"] = 0.0
    if "metadata" in normalized:
        normalized["metadata"]["started_at"] = "NORMALIZED"
        normalized["metadata"]["ended_at"] = "NORMALIZED"
        normalized["metadata"]["telemetry_overhead_ms"] = 0.0
    return normalized


def assert_golden_step_sequence(trajectory: dict) -> None:
    assert [step["step_type"] for step in trajectory["steps"]] == GOLDEN_STEP_TYPES
    assert len(trajectory["steps"]) == 5
    assert trajectory["steps"][4]["llm"]["tool_call_intents"] == []
    assert trajectory["steps"][4]["llm"]["output_content"]
