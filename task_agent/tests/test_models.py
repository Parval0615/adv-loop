from __future__ import annotations

from dataclasses import fields, is_dataclass

from task_agent.models import Observation, Plan, PlanStep, TaskRunResult, TaskSpec, TaskStep
from task_agent.prompts import (
    ARGUMENT_GENERATION_SYSTEM_PROMPT,
    EXECUTION_THOUGHT_SYSTEM_PROMPT,
    FINAL_SUMMARY_SYSTEM_PROMPT,
    GOAL_JUDGE_SYSTEM_PROMPT,
    PLAN_GENERATION_SYSTEM_PROMPT,
    REPLAN_SYSTEM_PROMPT,
    TASK_PARSE_SYSTEM_PROMPT,
)


def test_task_spec_fields_match_contract() -> None:
    assert is_dataclass(TaskSpec)
    assert [field.name for field in fields(TaskSpec)] == [
        "raw_instruction",
        "goal",
        "subgoals",
        "constraints",
        "entities",
        "parse_mode",
    ]


def test_task_step_fields_capture_decision_chain() -> None:
    assert [field.name for field in fields(TaskStep)] == [
        "plan_step_id",
        "thought",
        "action_tool",
        "action_args",
        "decision_reason",
        "observation",
        "replan_triggered",
    ]

    observation = Observation(
        answer="added to cart",
        blocked=False,
        risk_level="normal",
        value={"cart_size": 1},
        summary={"tool": "cart_add_item"},
    )
    step = TaskStep(
        plan_step_id="step-1",
        thought="Need to add the selected item.",
        action_tool="cart_add_item",
        action_args={"product_id": "p1", "quantity": 1},
        decision_reason="The plan step requires adding the item to the cart.",
        observation=observation,
    )

    assert step.to_dict() == {
        "plan_step_id": "step-1",
        "thought": "Need to add the selected item.",
        "action_tool": "cart_add_item",
        "action_args": {"product_id": "p1", "quantity": 1},
        "decision_reason": "The plan step requires adding the item to the cart.",
        "observation": {
            "answer": "added to cart",
            "blocked": False,
            "risk_level": "normal",
            "value": {"cart_size": 1},
            "summary": {"tool": "cart_add_item"},
        },
        "replan_triggered": False,
    }


def test_plan_and_result_fields_match_shared_contract() -> None:
    assert [field.name for field in fields(PlanStep)] == ["step_id", "candidate_tool", "args_hint"]
    assert [field.name for field in fields(Plan)] == ["steps", "revision"]
    assert [field.name for field in fields(Observation)] == ["answer", "blocked", "risk_level", "value", "summary"]
    assert [field.name for field in fields(TaskRunResult)] == [
        "task_spec",
        "plans",
        "trace",
        "final_answer",
        "goal_achieved",
        "replan_count",
        "llm_mode",
    ]

    spec = TaskSpec(raw_instruction="buy headphones", goal="buy headphones")
    plan = Plan(steps=[PlanStep(step_id="step-1", candidate_tool="product_search")], revision=0)
    result = TaskRunResult(
        task_spec=spec,
        plans=[plan],
        trace=[],
        final_answer="done",
        goal_achieved=True,
        replan_count=0,
        llm_mode="offline",
    )

    assert result.to_dict()["plans"][0]["steps"][0]["candidate_tool"] == "product_search"


def test_default_containers_are_not_shared() -> None:
    first_spec = TaskSpec(raw_instruction="first", goal="first")
    second_spec = TaskSpec(raw_instruction="second", goal="second")
    first_spec.subgoals.append("search")
    first_spec.constraints["budget_cents"] = 80000

    assert second_spec.subgoals == []
    assert second_spec.constraints == {}

    first_plan = Plan()
    second_plan = Plan()
    first_plan.steps.append(PlanStep(step_id="step-1", candidate_tool="product_search"))

    assert second_plan.steps == []


def test_prompt_constants_cover_required_agent_stages() -> None:
    prompts = [
        TASK_PARSE_SYSTEM_PROMPT,
        PLAN_GENERATION_SYSTEM_PROMPT,
        EXECUTION_THOUGHT_SYSTEM_PROMPT,
        ARGUMENT_GENERATION_SYSTEM_PROMPT,
        REPLAN_SYSTEM_PROMPT,
        FINAL_SUMMARY_SYSTEM_PROMPT,
        GOAL_JUDGE_SYSTEM_PROMPT,
    ]

    assert all(isinstance(prompt, str) and prompt.strip() for prompt in prompts)
    assert "raw_instruction" in TASK_PARSE_SYSTEM_PROMPT
    assert "goal" in TASK_PARSE_SYSTEM_PROMPT
    assert "subgoals" in TASK_PARSE_SYSTEM_PROMPT
    assert "constraints" in TASK_PARSE_SYSTEM_PROMPT
    assert "entities" in TASK_PARSE_SYSTEM_PROMPT
    assert "parse_mode" in TASK_PARSE_SYSTEM_PROMPT
    assert "candidate_tool" in PLAN_GENERATION_SYSTEM_PROMPT
    assert "args_hint" in ARGUMENT_GENERATION_SYSTEM_PROMPT
    assert "revision" in REPLAN_SYSTEM_PROMPT
    assert "goal_achieved" in GOAL_JUDGE_SYSTEM_PROMPT
