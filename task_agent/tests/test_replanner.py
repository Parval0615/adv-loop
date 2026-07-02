from __future__ import annotations

from typing import Any

import pytest

from task_agent.models import Observation, Plan, PlanStep, TaskSpec
from task_agent.prompts import REPLAN_SYSTEM_PROMPT
from task_agent.replanner import replan, should_replan
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


def test_budget_exceeded_triggers_replan_and_revision_increment() -> None:
    spec = TaskSpec(
        raw_instruction="找800元内降噪耳机并下单",
        goal="购买预算内耳机",
        constraints={"budget_cents": 80000},
    )
    obs = Observation(
        answer="已创建订单 o0001，服务端金额 900.00 元，状态 pending_payment。",
        value={"order_id": "o0001", "amount_cents": 90000},
        summary={"tool": "create_order"},
    )

    triggered, failure = should_replan(obs, spec)

    assert triggered is True
    assert "预算" in failure

    llm = RecordingLLM(
        {
            "revision": 1,
            "steps": [
                {
                    "step_id": "find-cheaper",
                    "candidate_tool": "product_search",
                    "args_hint": {"query": "800元内 降噪耳机"},
                },
                {
                    "step_id": "illegal",
                    "candidate_tool": "merchant_update_price",
                    "args_hint": {"product_id": "p1001", "new_price_cents": 1},
                },
            ],
        }
    )

    plan = replan(
        spec,
        history=[Plan(steps=[PlanStep("old", "create_order")], revision=2)],
        failure=failure,
        role="buyer",
        llm=llm,
    )
    allowed_tools = {entry["name"] for entry in catalog_for_role("buyer")}

    assert plan.revision == 3
    assert [step.step_id for step in plan.steps] == ["find-cheaper", "illegal"]
    assert all(step.candidate_tool in allowed_tools for step in plan.steps)
    assert plan.steps[0].candidate_tool == "product_search"
    assert plan.steps[1].candidate_tool == "product_search"
    assert llm.calls[0]["system"] == REPLAN_SYSTEM_PROMPT
    assert llm.calls[0]["schema_hint"]["minimum_revision"] == 3
    assert "预算" in llm.calls[0]["user"]


def test_search_no_match_and_out_of_stock_trigger_replan() -> None:
    spec = TaskSpec(raw_instruction="买同类有货商品", goal="找到可买商品")

    no_match = Observation(
        answer="没有找到匹配商品。",
        value=[],
        summary={"tool": "product_search"},
    )
    out_of_stock = Observation(
        answer="p1001 库存不足，不能加入购物车。",
        blocked=True,
        summary={"tool": "cart_add_item"},
    )

    no_match_triggered, no_match_failure = should_replan(no_match, spec)
    stock_triggered, stock_failure = should_replan(out_of_stock, spec)

    assert no_match_triggered is True
    assert "无匹配" in no_match_failure
    assert stock_triggered is True
    assert "缺货" in stock_failure


def test_blocked_observation_replans_with_legal_tool_fallback() -> None:
    spec = TaskSpec(raw_instruction="帮我处理订单", goal="完成订单处理")
    obs = Observation(
        answer="未知电商工具被默认拦截: 'transfer_money'",
        blocked=True,
        risk_level="high",
        summary={"tool": "transfer_money"},
    )

    triggered, failure = should_replan(obs, spec)

    assert triggered is True
    assert "工具异常" in failure

    llm = RecordingLLM(
        {
            "revision": 0,
            "steps": [
                {
                    "step_id": "safe-support",
                    "candidate_tool": "transfer_money",
                    "args_hint": {"amount_cents": 1},
                }
            ],
        }
    )

    plan = replan(spec, history=[], failure=failure, role="buyer", llm=llm)

    assert plan.revision == 1
    assert plan.steps[0].candidate_tool == "product_search"
    assert llm.calls[0]["system"] == REPLAN_SYSTEM_PROMPT
    assert "transfer_money" in llm.calls[0]["user"]


@pytest.mark.parametrize(
    ("tool_name", "answer", "expected"),
    [
        ("create_order", "购物车为空，不能创建订单。", "下单失败"),
        ("mock_payment", "支付金额必须等于服务端订单金额。", "支付失败"),
        ("get_product_detail", "工具参数错误或调用失败: product_id missing", "工具异常"),
    ],
)
def test_failure_categories_cover_order_payment_and_tool_errors(
    tool_name: str,
    answer: str,
    expected: str,
) -> None:
    spec = TaskSpec(raw_instruction="继续完成任务", goal="完成任务")
    obs = Observation(
        answer=answer,
        blocked=True,
        risk_level="high",
        summary={"tool": tool_name},
    )

    triggered, failure = should_replan(obs, spec)

    assert triggered is True
    assert expected in failure
