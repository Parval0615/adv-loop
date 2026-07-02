from __future__ import annotations

import json
from pathlib import Path

from task_agent.models import Observation, Plan, PlanStep, TaskRunResult, TaskSpec, TaskStep
from task_agent.trace_adapter import build_plan_trace_report, export_plan_trace, task_run_to_trace_inputs


def test_task_steps_adapt_to_trace_dag_schema() -> None:
    result = _sample_result()

    events, decisions = task_run_to_trace_inputs(result)
    report = build_plan_trace_report(result)

    assert [event["event_type"] for event in events] == ["tool_call", "tool_call"]
    assert [event["name"] for event in events] == ["cart_add_item", "cart_add_item"]
    assert events[0]["result"]["sentinel_intercept_id"] == decisions[0]["intercept_id"]
    assert decisions[0]["decision"]["decision"] == "block"
    assert decisions[0]["decision"]["replan_triggered"] is True
    assert decisions[1]["context"]["plan_revision"] == 1
    assert report.trace_id.startswith("task-agent-")
    assert [item["name"] for item in report.call_details] == ["cart_add_item", "cart_add_item"]


def test_export_plan_trace_writes_trace_artifacts(tmp_path: Path) -> None:
    result = _sample_result()

    artifacts = export_plan_trace(result, tmp_path / "trace")

    graph_md = Path(artifacts["trace_mermaid"])
    timeline_path = Path(artifacts["trace_timeline"])
    integrity_path = Path(artifacts["trace_integrity"])
    report_path = Path(artifacts["trace_report"])
    assert graph_md.exists()
    assert timeline_path.exists()
    assert integrity_path.exists()
    assert report_path.exists()

    timeline = [json.loads(line) for line in timeline_path.read_text(encoding="utf-8").splitlines()]
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert any(item.get("name") == "cart_add_item" for item in timeline)
    assert integrity["root_hash"]
    assert report["impact_scope"]["blocked_or_asked_tools"][0]["tool"] == "cart_add_item"
    assert "cart_add_item" in graph_md.read_text(encoding="utf-8")


def _sample_result() -> TaskRunResult:
    spec = TaskSpec(
        raw_instruction="把有货商品加入购物车",
        goal="把有货商品加入购物车",
        subgoals=["先试原商品", "缺货后换替代商品"],
    )
    return TaskRunResult(
        task_spec=spec,
        plans=[
            Plan(
                revision=0,
                steps=[
                    PlanStep(
                        step_id="add-original",
                        candidate_tool="cart_add_item",
                        args_hint={"product_id": "p1001", "quantity": 1},
                    )
                ],
            ),
            Plan(
                revision=1,
                steps=[
                    PlanStep(
                        step_id="add-alternative",
                        candidate_tool="cart_add_item",
                        args_hint={"product_id": "p2001", "quantity": 1},
                    )
                ],
            ),
        ],
        trace=[
            TaskStep(
                plan_step_id="add-original",
                thought="尝试加入原商品。",
                action_tool="cart_add_item",
                action_args={"product_id": "p1001", "quantity": 1},
                decision_reason="先执行原计划。",
                observation=Observation(
                    answer="库存不足",
                    blocked=True,
                    risk_level="medium",
                    summary={"tool": "cart_add_item"},
                ),
                replan_triggered=True,
            ),
            TaskStep(
                plan_step_id="add-alternative",
                thought="选择替代商品。",
                action_tool="cart_add_item",
                action_args={"product_id": "p2001", "quantity": 1},
                decision_reason="替代商品有货。",
                observation=Observation(
                    answer="已加入购物车",
                    blocked=False,
                    risk_level="medium",
                    value={"product_id": "p2001", "quantity": 1},
                    summary={"tool": "cart_add_item"},
                ),
            ),
        ],
        final_answer="已完成。",
        goal_achieved=True,
        replan_count=1,
        llm_mode="scripted-test",
    )
