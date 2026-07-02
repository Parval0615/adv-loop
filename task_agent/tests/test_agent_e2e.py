from __future__ import annotations

from typing import Any

from auto_defense_system.ecommerce_agent.fixtures import create_demo_store
from auto_defense_system.ecommerce_agent.models import Product

from task_agent import TaskAgent, TaskSpec
from task_agent.agent import _search_query
from task_agent.prompts import (
    ARGUMENT_GENERATION_SYSTEM_PROMPT,
    EXECUTION_THOUGHT_SYSTEM_PROMPT,
    GOAL_JUDGE_SYSTEM_PROMPT,
    PLAN_GENERATION_SYSTEM_PROMPT,
    REPLAN_SYSTEM_PROMPT,
    TASK_PARSE_SYSTEM_PROMPT,
)


class ScriptedLLM:
    mode = "scripted-offline"

    def __init__(
        self,
        *,
        initial_steps: list[dict[str, Any]],
        replan_steps: list[list[dict[str, Any]]] | None = None,
        goal: str = "把商品加入购物车",
        offline: bool = False,
        parse_mode: str = "scripted",
    ) -> None:
        self.initial_steps = initial_steps
        self.replan_steps = replan_steps or []
        self.goal = goal
        self.offline = offline
        self.parse_mode = parse_mode
        self.complete_json_calls: list[dict[str, Any]] = []
        self.decide_calls: list[dict[str, Any]] = []
        self._replan_index = 0

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint: Any,
        seed: int = 0,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        self.complete_json_calls.append(
            {
                "system": system,
                "user": user,
                "schema_hint": schema_hint,
                "seed": seed,
                "max_tokens": max_tokens,
            }
        )
        if system == TASK_PARSE_SYSTEM_PROMPT:
            return {
                "goal": self.goal,
                "subgoals": [self.goal],
                "constraints": {},
                "entities": {},
                "parse_mode": self.parse_mode,
            }
        if system == PLAN_GENERATION_SYSTEM_PROMPT:
            return {"revision": 0, "steps": self.initial_steps}
        if system == REPLAN_SYSTEM_PROMPT:
            if self._replan_index < len(self.replan_steps):
                steps = self.replan_steps[self._replan_index]
            else:
                steps = self.replan_steps[-1] if self.replan_steps else self.initial_steps
            self._replan_index += 1
            return {"revision": self._replan_index, "steps": steps}
        if system == EXECUTION_THOUGHT_SYSTEM_PROMPT:
            return {"thought": "执行当前计划步骤。"}
        if system == ARGUMENT_GENERATION_SYSTEM_PROMPT:
            return {}
        if system == GOAL_JUDGE_SYSTEM_PROMPT:
            return {"goal_achieved": False, "reason": "state rules should decide"}
        return {}

    def decide(
        self,
        system: str,
        user: str,
        *,
        choices: list[str],
        seed: int = 0,
    ) -> dict[str, Any]:
        self.decide_calls.append(
            {"system": system, "user": user, "choices": choices, "seed": seed}
        )
        return {"choice": choices[0], "reason": "scripted"}


def test_offline_e2e_search_returns_task_run_result() -> None:
    agent = TaskAgent(force_offline=True)

    result = agent.run("搜索降噪耳机", max_steps=4)

    assert result.task_spec.raw_instruction == "搜索降噪耳机"
    assert result.llm_mode == "deterministic-offline"
    assert result.plans
    assert len(result.trace) == 1
    assert result.trace[0].action_tool == "product_search"
    assert result.trace[0].observation.blocked is False
    assert result.goal_achieved is True
    assert "已执行 1 个工具步骤" in result.final_answer


def test_flagship_search_query_strips_budget_flow_noise_and_hits_product() -> None:
    task_spec = TaskSpec(
        raw_instruction="找800元内降噪耳机比价后下单",
        goal="找800元内降噪耳机比价后下单",
    )
    query = _search_query(task_spec)
    store = create_demo_store()

    assert query == "降噪耳机"
    assert "p1001" in {product.product_id for product in store.search_products(query)}


def test_offline_replan_retries_relaxed_search_query_instead_of_mock_payment() -> None:
    llm = ScriptedLLM(
        goal="降噪耳机",
        initial_steps=[
            {
                "step_id": "bad-search",
                "candidate_tool": "product_search",
                "args_hint": {"query": "800元内降噪耳机比价后下单"},
            }
        ],
        replan_steps=[
            [
                {
                    "step_id": "bad-payment",
                    "candidate_tool": "mock_payment",
                    "args_hint": {},
                }
            ]
        ],
        offline=True,
        parse_mode="deterministic-offline",
    )
    agent = TaskAgent(store=create_demo_store(), llm=llm)

    result = agent.run("降噪耳机", max_steps=4, max_replans=1)

    assert result.replan_count == 1
    assert [step.action_tool for step in result.trace] == [
        "product_search",
        "product_search",
    ]
    assert result.trace[0].observation.value == []
    assert result.trace[1].action_args["query"] == "降噪耳机"
    assert "p1001" in result.trace[1].observation.value
    assert result.plans[1].steps[0].candidate_tool == "product_search"
    assert not _has_single_step_payment_replan(result)


def test_offline_out_of_stock_replan_picks_in_stock_same_class_product() -> None:
    store = create_demo_store()
    store.products["p1001"].stock = 0
    store.products["p1003"] = Product(
        product_id="p1003",
        shop_id="shop_001",
        title="星云降噪耳机 Lite",
        category="数码耳机",
        brand="Nebula",
        price_cents=39900,
        stock=5,
        description="主动降噪入门款，适合日常通勤。",
        sold=120,
    )
    llm = ScriptedLLM(
        goal="降噪耳机",
        initial_steps=[
            {
                "step_id": "add-empty",
                "candidate_tool": "cart_add_item",
                "args_hint": {"product_id": "p1001", "quantity": 1},
            }
        ],
        replan_steps=[
            [
                {
                    "step_id": "bad-payment",
                    "candidate_tool": "mock_payment",
                    "args_hint": {},
                }
            ]
        ],
        offline=True,
        parse_mode="deterministic-offline",
    )
    agent = TaskAgent(store=store, llm=llm)

    result = agent.run("降噪耳机", max_steps=4, max_replans=1)

    assert result.replan_count == 1
    assert [step.action_tool for step in result.trace] == [
        "cart_add_item",
        "product_search",
        "cart_add_item",
    ]
    assert result.plans[1].steps[-1].args_hint["product_id"] == "p1003"
    assert result.trace[-1].observation.blocked is False
    assert [(item.product_id, item.quantity) for item in store.cart_items("buyer_001")] == [
        ("p1003", 1)
    ]
    assert "mock_payment" not in [step.action_tool for step in result.trace]
    assert not _has_single_step_payment_replan(result)


def test_offline_out_of_stock_replan_without_same_class_uses_support_not_payment() -> None:
    store = create_demo_store()
    store.products["p1001"].stock = 0
    llm = ScriptedLLM(
        goal="降噪耳机",
        initial_steps=[
            {
                "step_id": "add-empty",
                "candidate_tool": "cart_add_item",
                "args_hint": {"product_id": "p1001", "quantity": 1},
            }
        ],
        replan_steps=[
            [
                {
                    "step_id": "bad-payment",
                    "candidate_tool": "mock_payment",
                    "args_hint": {},
                }
            ]
        ],
        offline=True,
        parse_mode="deterministic-offline",
    )
    agent = TaskAgent(store=store, llm=llm)

    result = agent.run("降噪耳机", max_steps=3, max_replans=1)

    assert result.replan_count == 1
    assert [step.action_tool for step in result.trace] == [
        "cart_add_item",
        "support_create_ticket",
    ]
    assert result.trace[-1].observation.blocked is False
    assert not [order for order in store.orders.values() if order.user_id == "buyer_001"]
    assert not store.payments
    assert not _has_single_step_payment_replan(result)


def test_out_of_stock_replans_to_available_product() -> None:
    store = create_demo_store()
    store.products["p1001"].stock = 0
    llm = ScriptedLLM(
        goal="把有货商品加入购物车",
        initial_steps=[
            {
                "step_id": "add-empty",
                "candidate_tool": "cart_add_item",
                "args_hint": {"product_id": "p1001", "quantity": 1},
            }
        ],
        replan_steps=[
            [
                {
                    "step_id": "add-alt",
                    "candidate_tool": "cart_add_item",
                    "args_hint": {"product_id": "p2001", "quantity": 1},
                }
            ]
        ],
    )
    agent = TaskAgent(store=store, force_offline=True, llm=llm)

    result = agent.run("把有货商品加入购物车", max_steps=4, max_replans=2)

    assert result.replan_count == 1
    assert len(result.plans) == 2
    assert [step.action_args["product_id"] for step in result.trace] == ["p1001", "p2001"]
    assert result.trace[0].replan_triggered is True
    assert result.trace[1].observation.blocked is False
    assert [(item.product_id, item.quantity) for item in store.cart_items("buyer_001")] == [
        ("p2001", 1)
    ]
    assert result.goal_achieved is True


def test_max_steps_and_max_replans_are_enforced() -> None:
    first_store = create_demo_store()
    first_store.products["p1001"].stock = 0
    first_llm = ScriptedLLM(
        initial_steps=[
            {
                "step_id": "add-empty",
                "candidate_tool": "cart_add_item",
                "args_hint": {"product_id": "p1001", "quantity": 1},
            }
        ],
        replan_steps=[
            [
                {
                    "step_id": "add-alt",
                    "candidate_tool": "cart_add_item",
                    "args_hint": {"product_id": "p2001", "quantity": 1},
                }
            ]
        ],
    )
    first_result = TaskAgent(store=first_store, llm=first_llm).run(
        "把商品加入购物车",
        max_steps=1,
        max_replans=3,
    )

    assert len(first_result.trace) == 1
    assert first_result.replan_count == 0
    assert first_result.trace[0].replan_triggered is True
    assert "max_steps=1" in first_result.final_answer

    second_store = create_demo_store()
    second_store.products["p1001"].stock = 0
    repeated_failure_step = {
        "step_id": "still-empty",
        "candidate_tool": "cart_add_item",
        "args_hint": {"product_id": "p1001", "quantity": 1},
    }
    second_llm = ScriptedLLM(
        initial_steps=[repeated_failure_step],
        replan_steps=[[repeated_failure_step]],
    )
    second_result = TaskAgent(store=second_store, llm=second_llm).run(
        "把商品加入购物车",
        max_steps=5,
        max_replans=1,
    )

    assert len(second_result.trace) == 2
    assert second_result.replan_count == 1
    assert second_result.trace[-1].replan_triggered is True
    assert "max_replans=1" in second_result.final_answer


def _has_single_step_payment_replan(result: Any) -> bool:
    return any(
        len(plan.steps) == 1 and plan.steps[0].candidate_tool == "mock_payment"
        for plan in result.plans[1:]
    )
