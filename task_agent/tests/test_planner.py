from __future__ import annotations

from typing import Any

from task_agent.models import TaskSpec
from task_agent.planner import make_plan, parse_task
from task_agent.prompts import PLAN_GENERATION_SYSTEM_PROMPT, TASK_PARSE_SYSTEM_PROMPT
from task_agent.tool_registry import catalog_for_role


class RecordingLLM:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint: Any,
        seed: int = 0,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "schema_hint": schema_hint,
                "seed": seed,
                "max_tokens": max_tokens,
            }
        )
        return dict(self.payload)


def test_parse_multi_goal() -> None:
    instruction = "找800元内降噪耳机，比价后下单，再处理我上次的退款"
    llm = RecordingLLM(
        {
            "goal": "完成耳机选购并处理退款",
            "constraints": {"budget_cents": 80000},
            "entities": {"product_type": "降噪耳机", "order_ref": "上次"},
            "parse_mode": "llm",
        }
    )

    spec = parse_task(instruction, llm)

    assert spec.raw_instruction == instruction
    assert spec.goal == "完成耳机选购并处理退款"
    assert spec.constraints == {"budget_cents": 80000}
    assert spec.entities["product_type"] == "降噪耳机"
    assert any("找" in subgoal or "搜索" in subgoal for subgoal in spec.subgoals)
    assert any("比价" in subgoal for subgoal in spec.subgoals)
    assert any("下单" in subgoal for subgoal in spec.subgoals)
    assert any("退款" in subgoal for subgoal in spec.subgoals)
    assert llm.calls[0]["system"] == TASK_PARSE_SYSTEM_PROMPT
    assert instruction in llm.calls[0]["user"]
    assert "subgoals" in llm.calls[0]["schema_hint"]["required"]


def test_make_plan_replaces_illegal_tools_with_role_safe_candidate() -> None:
    spec = TaskSpec(raw_instruction="买耳机并退款", goal="完成耳机选购并处理退款")
    llm = RecordingLLM(
        {
            "revision": "2",
            "steps": [
                {"candidate_tool": "merchant_update_price", "args_hint": "not an object"},
                {
                    "step_id": "detail",
                    "candidate_tool": "get_product_detail",
                    "args_hint": {"product_id": "p1001"},
                },
                {"step_id": "detail", "candidate_tool": "transfer_money", "args_hint": {"amount_cents": 1}},
            ],
        }
    )

    plan = make_plan(spec, role="buyer", llm=llm)
    allowed_tools = {entry["name"] for entry in catalog_for_role("buyer")}

    assert plan.revision == 2
    assert [step.step_id for step in plan.steps] == ["step-1", "detail", "step-3"]
    assert all(step.candidate_tool in allowed_tools for step in plan.steps)
    assert plan.steps[0].candidate_tool == "product_search"
    assert plan.steps[0].args_hint == {}
    assert plan.steps[1].candidate_tool == "get_product_detail"
    assert plan.steps[1].args_hint == {"product_id": "p1001"}
    assert plan.steps[2].candidate_tool == "product_search"
    assert llm.calls[0]["system"] == PLAN_GENERATION_SYSTEM_PROMPT
    assert set(llm.calls[0]["schema_hint"]["choices"]) == allowed_tools
    assert "merchant_update_price" not in llm.calls[0]["schema_hint"]["choices"]
