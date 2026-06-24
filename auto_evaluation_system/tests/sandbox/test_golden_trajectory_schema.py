import json
from pathlib import Path

import pytest
from jsonschema import validate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "trajectory-v1.schema.json"
GOLDEN_PATH = ROOT / "schemas" / "fixtures" / "golden-5step-trajectory.json"

GOLDEN_STEP_TYPES = [
    "llm_inference",
    "tool_call",
    "llm_inference",
    "tool_call",
    "llm_inference",
]


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_golden_trajectory_validates_against_schema(schema: dict, golden: dict) -> None:
    validate(instance=golden, schema=schema)


def test_golden_step_type_sequence(golden: dict) -> None:
    assert [step["step_type"] for step in golden["steps"]] == GOLDEN_STEP_TYPES


def test_golden_has_five_steps(golden: dict) -> None:
    assert len(golden["steps"]) == 5


def test_golden_final_step_has_no_tool_intents(golden: dict) -> None:
    final = golden["steps"][4]
    assert final["step_type"] == "llm_inference"
    assert final["llm"]["tool_call_intents"] == []
    assert final["llm"]["output_content"]
