from __future__ import annotations

from typing import Any

from auto_defense_system.ecommerce_agent.fixtures import create_demo_store
from task_agent.executor import Executor
from task_agent.models import PlanStep
from task_agent.prompts import EXECUTION_THOUGHT_SYSTEM_PROMPT


class ScriptedLLM:
    def __init__(self, *, choice: str = "cart_add_item", offline: bool = False) -> None:
        self.choice = choice
        self.offline = offline
        self.decide_calls: list[dict[str, Any]] = []
        self.complete_json_calls: list[dict[str, Any]] = []

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
        if system == EXECUTION_THOUGHT_SYSTEM_PROMPT:
            return {"thought": "Add the planned item to the cart."}
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
        return {"choice": self.choice, "reason": f"Selected {self.choice}."}


def test_step_calls_real_tool() -> None:
    store = create_demo_store()
    llm = ScriptedLLM()
    executor = Executor(
        store=store,
        user_id="buyer_001",
        role="buyer",
        llm=llm,
    )
    step = PlanStep(
        step_id="step-1",
        candidate_tool="cart_add_item",
        args_hint={"product_id": "p1001"},
    )

    result = executor.run_step(step, history=[])

    assert llm.decide_calls
    assert llm.decide_calls[0]["choices"] == ["cart_add_item"]
    assert result.action_tool == "cart_add_item"
    assert result.action_args == {"product_id": "p1001", "quantity": 1}
    assert result.observation.blocked is False
    assert result.observation.summary["tool_calls"][0]["tool_name"] == "cart_add_item"
    assert [(item.product_id, item.quantity) for item in store.cart_items("buyer_001")] == [
        ("p1001", 1)
    ]


def test_offline_decide_action_accepts_legal_non_first_choice() -> None:
    store = create_demo_store()
    llm = ScriptedLLM(choice="get_user_profile", offline=True)
    executor = Executor(
        store=store,
        user_id="buyer_001",
        role="buyer",
        llm=llm,
    )
    step = PlanStep(
        step_id="step-1",
        candidate_tool="",
        args_hint={},
    )

    action_tool, action_args, decision_reason = executor._decide_action(
        step, history=[]
    )

    assert llm.decide_calls
    assert llm.decide_calls[0]["choices"][0] == "product_search"
    assert action_tool == "get_user_profile"
    assert action_args == {}
    assert decision_reason == "Selected get_user_profile."
