from __future__ import annotations

import json
from typing import Any

from auto_defense_system.ecommerce_agent.fixtures import create_demo_store

from auto_evaluation_system.task_eval import TASK_EVAL_JUDGE_SYSTEM_PROMPT, evaluate_task_runs
from task_agent.models import Observation, Plan, PlanStep, TaskRunResult, TaskSpec, TaskStep


class ScriptedJudgeLLM:
    mode = "scripted-judge"

    def __init__(self, *judgements: dict[str, Any]) -> None:
        self.judgements = list(judgements)
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
        if self.judgements:
            return self.judgements.pop(0)
        return {"goal_achieved": False, "reason": "no scripted judgement"}


def test_evaluate_task_runs_calculates_metrics_without_store_or_judge() -> None:
    successful = _result(
        goal="search product",
        achieved=True,
        trace=[
            _step(
                "product_search",
                value=[{"product_id": "p1001"}],
            )
        ],
    )
    failed = _result(
        goal="transfer money",
        achieved=False,
        trace=[
            _step(
                "transfer_money",
                blocked=True,
                allowed=False,
                answer="unknown ecommerce tool",
            )
        ],
    )

    report = evaluate_task_runs([successful, failed])

    assert report.schema_version == "task-evaluation-report-v0.1"
    assert report.metrics.total_tasks == 2
    assert report.metrics.achieved_tasks == 1
    assert report.metrics.task_achievement_rate == 0.5
    assert report.metrics.average_steps == 1.0
    assert report.metrics.replan_trigger_rate == 0.0
    assert report.metrics.replan_success_rate == 0.0
    assert report.metrics.invalid_tool_calls == 1
    assert report.metrics.total_tool_calls == 2
    assert report.metrics.invalid_tool_call_rate == 0.5
    assert report.records[0].task_achieved is True
    assert report.records[1].invalid_tool_calls == 1


def test_empty_trace_is_safe() -> None:
    empty_batch = evaluate_task_runs([])

    assert empty_batch.metrics.total_tasks == 0
    assert empty_batch.metrics.task_achievement_rate == 0.0
    assert empty_batch.metrics.average_steps == 0.0
    assert empty_batch.metrics.invalid_tool_call_rate == 0.0

    report = evaluate_task_runs(
        [
            _result(
                goal="add product to cart",
                achieved=False,
                trace=[],
            )
        ]
    )

    record = report.records[0]
    assert record.steps == 0
    assert record.total_tool_calls == 0
    assert record.invalid_tool_calls == 0
    assert record.task_achieved is False
    assert report.metrics.average_steps == 0.0


def test_failed_trace_uses_llm_judge_to_veto_agent_success() -> None:
    llm = ScriptedJudgeLLM({"goal_achieved": False, "reason": "the only tool call failed"})
    result = _result(
        goal="add product to cart",
        achieved=True,
        trace=[
            _step(
                "cart_add_item",
                blocked=True,
                allowed=False,
                answer="tool call failed",
            )
        ],
    )

    report = evaluate_task_runs([result], llm=llm)

    assert report.records[0].result_goal_achieved is True
    assert report.records[0].judge_goal_achieved is False
    assert report.records[0].judge_reason == "the only tool call failed"
    assert report.records[0].task_achieved is False
    assert report.metrics.achieved_tasks == 0
    assert llm.calls[0]["system"] == TASK_EVAL_JUDGE_SYSTEM_PROMPT
    prompt_payload = json.loads(llm.calls[0]["user"])
    assert "task_result" in prompt_payload
    assert prompt_payload["store_evidence"]["available"] is False


def test_successful_replan_trace_uses_store_and_counts_replan_success() -> None:
    store = create_demo_store()
    store.add_cart_item("buyer_001", "p2001", 1)
    llm = ScriptedJudgeLLM({"goal_achieved": True, "reason": "cart contains the replanned item"})
    result = _result(
        goal="add product to cart",
        achieved=True,
        replan_count=1,
        trace=[
            _step(
                "cart_add_item",
                args={"product_id": "p1001", "quantity": 1},
                blocked=True,
                allowed=False,
                answer="stock insufficient",
                replan_triggered=True,
            ),
            _step(
                "cart_add_item",
                args={"product_id": "p2001", "quantity": 1},
                value={"product_id": "p2001", "quantity": 1},
            ),
        ],
    )

    report = evaluate_task_runs([result], store=store, llm=llm)

    record = report.records[0]
    assert record.store_goal_achieved is True
    assert record.judge_goal_achieved is True
    assert record.task_achieved is True
    assert record.replan_triggered is True
    assert record.replan_succeeded is True
    assert report.metrics.task_achievement_rate == 1.0
    assert report.metrics.average_steps == 2.0
    assert report.metrics.replan_trigger_rate == 1.0
    assert report.metrics.replan_success_rate == 1.0
    assert report.metrics.invalid_tool_call_rate == 0.5


def _result(
    *,
    goal: str,
    achieved: bool,
    trace: list[TaskStep],
    replan_count: int = 0,
) -> TaskRunResult:
    task_spec = TaskSpec(raw_instruction=goal, goal=goal)
    return TaskRunResult(
        task_spec=task_spec,
        plans=[Plan(steps=[PlanStep(step_id="step-1", candidate_tool="product_search")])],
        trace=trace,
        final_answer="done" if achieved else "failed",
        goal_achieved=achieved,
        replan_count=replan_count,
        llm_mode="test",
    )


def _step(
    tool_name: str,
    *,
    args: dict[str, Any] | None = None,
    value: Any = None,
    blocked: bool = False,
    allowed: bool = True,
    answer: str = "ok",
    replan_triggered: bool = False,
) -> TaskStep:
    arguments = args or {}
    return TaskStep(
        plan_step_id=f"{tool_name}-step",
        thought=f"run {tool_name}",
        action_tool=tool_name,
        action_args=arguments,
        decision_reason="test",
        observation=Observation(
            answer=answer,
            blocked=blocked,
            risk_level="high" if blocked else "normal",
            value=value,
            summary={
                "tool": tool_name,
                "tool_calls": [
                    {
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "allowed": allowed,
                        "result": answer,
                        "risk_level": "high" if blocked else "normal",
                        "reason": answer,
                    }
                ],
                "business_events": [],
                "audit_events": [],
            },
        ),
        replan_triggered=replan_triggered,
    )
