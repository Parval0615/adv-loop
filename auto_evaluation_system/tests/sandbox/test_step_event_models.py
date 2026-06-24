import pytest
from pydantic import ValidationError

from auto_evaluation_system.events.models import (
    GOLDEN_STEP_TYPE_SEQUENCE,
    LLMInferencePayload,
    StepEvent,
    StepType,
    ToolCallIntent,
    ToolCallPayload,
)


def test_llm_inference_requires_llm_payload() -> None:
    with pytest.raises(ValidationError):
        StepEvent(step_type=StepType.LLM_INFERENCE, timestamp="2026-01-01T00:00:00Z")


def test_tool_call_requires_tool_payload() -> None:
    with pytest.raises(ValidationError):
        StepEvent(step_type=StepType.TOOL_CALL, timestamp="2026-01-01T00:00:00Z")


def test_valid_llm_inference_event() -> None:
    event = StepEvent(
        step_type=StepType.LLM_INFERENCE,
        timestamp="2026-01-01T00:00:00Z",
        llm=LLMInferencePayload(
            model="gpt-4o-mini",
            input_messages=[{"role": "user", "content": "hi"}],
            turn_index=0,
        ),
    )
    assert event.step_type == StepType.LLM_INFERENCE


def test_valid_tool_call_event() -> None:
    event = StepEvent(
        step_type=StepType.TOOL_CALL,
        timestamp="2026-01-01T00:00:01Z",
        tool_call=ToolCallPayload(
            call_id="c1",
            name="get_weather",
            arguments={"city": "Beijing"},
            response={"temp": 22},
            parent_turn_index=0,
            latency_ms=1.0,
        ),
    )
    assert event.tool_call is not None


def test_golden_step_type_sequence_constant() -> None:
    assert [t.value for t in GOLDEN_STEP_TYPE_SEQUENCE] == [
        "llm_inference",
        "tool_call",
        "llm_inference",
        "tool_call",
        "llm_inference",
    ]


def test_tool_call_intent_fields() -> None:
    intent = ToolCallIntent(call_id="x", name="get_weather", arguments={"city": "Beijing"})
    assert intent.name == "get_weather"
