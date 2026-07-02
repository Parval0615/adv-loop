from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from task_agent.models import TaskRunResult, TaskStep
from task_agent.tool_registry import TOOL_CATALOG


TASK_EVAL_JUDGE_SYSTEM_PROMPT = """You are an evaluator for ecommerce task-agent runs.
Decide whether the task goal was actually achieved from the provided TaskRunResult, store evidence, and trace.
Return only JSON with goal_achieved and reason. Be conservative when evidence is missing or contradictory."""

_VALID_TOOL_NAMES = {str(entry["name"]) for entry in TOOL_CATALOG if "name" in entry}


class TaskEvaluationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_goal: str = Field(min_length=1)
    task_achieved: bool
    result_goal_achieved: bool
    store_goal_achieved: bool | None = None
    judge_goal_achieved: bool | None = None
    judge_reason: str = ""
    steps: int = Field(ge=0)
    replan_count: int = Field(ge=0)
    replan_triggered: bool
    replan_succeeded: bool
    invalid_tool_calls: int = Field(ge=0)
    total_tool_calls: int = Field(ge=0)


class TaskEvaluationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_tasks: int = Field(ge=0)
    achieved_tasks: int = Field(ge=0)
    task_achievement_rate: float = Field(ge=0.0, le=1.0)
    average_steps: float = Field(ge=0.0)
    replan_triggered_tasks: int = Field(ge=0)
    replan_trigger_rate: float = Field(ge=0.0, le=1.0)
    replan_successful_tasks: int = Field(ge=0)
    replan_success_rate: float = Field(ge=0.0, le=1.0)
    invalid_tool_calls: int = Field(ge=0)
    total_tool_calls: int = Field(ge=0)
    invalid_tool_call_rate: float = Field(ge=0.0, le=1.0)


class TaskEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["task-evaluation-report-v0.1"] = "task-evaluation-report-v0.1"
    metrics: TaskEvaluationMetrics
    records: list[TaskEvaluationRecord] = Field(default_factory=list)


def evaluate_task_runs(
    results: Sequence[TaskRunResult],
    *,
    store: Any | None = None,
    llm: Any | None = None,
    user_id: str = "buyer_001",
    role: str = "buyer",
) -> TaskEvaluationReport:
    """Evaluate task achievement and autonomy metrics for a batch of TaskRunResult objects."""

    records = [
        evaluate_task_run(result, store=store, llm=llm, user_id=user_id, role=role)
        for result in results
    ]
    return TaskEvaluationReport(metrics=_aggregate_metrics(records), records=records)


def evaluate_task_run(
    result: TaskRunResult,
    *,
    store: Any | None = None,
    llm: Any | None = None,
    user_id: str = "buyer_001",
    role: str = "buyer",
) -> TaskEvaluationRecord:
    store_evidence = _store_evidence(store, user_id=user_id, role=role)
    store_goal_achieved = _infer_store_goal_achieved(result, store_evidence)
    judge_goal_achieved, judge_reason = _judge_goal_achievement(
        result,
        store_evidence,
        llm=llm,
        store_goal_achieved=store_goal_achieved,
    )
    task_achieved = _combine_goal_signals(
        result_goal_achieved=bool(result.goal_achieved),
        store_goal_achieved=store_goal_achieved,
        judge_goal_achieved=judge_goal_achieved,
    )
    replan_triggered = _replan_triggered(result)
    invalid_tool_calls = sum(1 for step in result.trace if _is_invalid_tool_call(step))

    return TaskEvaluationRecord(
        task_goal=_task_goal(result),
        task_achieved=task_achieved,
        result_goal_achieved=bool(result.goal_achieved),
        store_goal_achieved=store_goal_achieved,
        judge_goal_achieved=judge_goal_achieved,
        judge_reason=judge_reason,
        steps=len(result.trace),
        replan_count=max(0, int(result.replan_count)),
        replan_triggered=replan_triggered,
        replan_succeeded=replan_triggered and task_achieved,
        invalid_tool_calls=invalid_tool_calls,
        total_tool_calls=len(result.trace),
    )


def _aggregate_metrics(records: Sequence[TaskEvaluationRecord]) -> TaskEvaluationMetrics:
    total_tasks = len(records)
    achieved_tasks = sum(1 for record in records if record.task_achieved)
    total_steps = sum(record.steps for record in records)
    replan_triggered_tasks = sum(1 for record in records if record.replan_triggered)
    replan_successful_tasks = sum(1 for record in records if record.replan_succeeded)
    invalid_tool_calls = sum(record.invalid_tool_calls for record in records)
    total_tool_calls = sum(record.total_tool_calls for record in records)

    return TaskEvaluationMetrics(
        total_tasks=total_tasks,
        achieved_tasks=achieved_tasks,
        task_achievement_rate=_rate(achieved_tasks, total_tasks),
        average_steps=_rate(total_steps, total_tasks),
        replan_triggered_tasks=replan_triggered_tasks,
        replan_trigger_rate=_rate(replan_triggered_tasks, total_tasks),
        replan_successful_tasks=replan_successful_tasks,
        replan_success_rate=_rate(replan_successful_tasks, replan_triggered_tasks),
        invalid_tool_calls=invalid_tool_calls,
        total_tool_calls=total_tool_calls,
        invalid_tool_call_rate=_rate(invalid_tool_calls, total_tool_calls),
    )


def _combine_goal_signals(
    *,
    result_goal_achieved: bool,
    store_goal_achieved: bool | None,
    judge_goal_achieved: bool | None,
) -> bool:
    if not result_goal_achieved:
        return False
    if store_goal_achieved is False:
        return False
    if judge_goal_achieved is False:
        return False
    return True


def _judge_goal_achievement(
    result: TaskRunResult,
    store_evidence: dict[str, Any],
    *,
    llm: Any | None,
    store_goal_achieved: bool | None,
) -> tuple[bool | None, str]:
    if llm is None or not hasattr(llm, "complete_json"):
        return None, ""

    try:
        judge = llm.complete_json(
            TASK_EVAL_JUDGE_SYSTEM_PROMPT,
            _json_dumps(
                {
                    "task_result": _jsonable(result),
                    "store_evidence": store_evidence,
                    "deterministic_store_goal_achieved": store_goal_achieved,
                }
            ),
            schema_hint={
                "type": "object",
                "required": ["goal_achieved", "reason"],
                "properties": {
                    "goal_achieved": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
            },
            seed=211,
            max_tokens=512,
        )
    except Exception as exc:
        return None, f"judge_error: {exc}"

    reason = judge.get("reason")
    if not isinstance(reason, str):
        reason = ""
    if judge.get("goal_achieved") is True:
        return True, reason
    if judge.get("goal_achieved") is False:
        return False, reason
    return None, reason


def _infer_store_goal_achieved(result: TaskRunResult, evidence: dict[str, Any]) -> bool | None:
    if not evidence.get("available"):
        return None
    if not result.trace:
        return False

    goal_text = _goal_text(result)
    successful_tools = {
        step.action_tool
        for step in result.trace
        if not bool(getattr(step.observation, "blocked", False))
    }
    orders = evidence.get("orders") if isinstance(evidence.get("orders"), list) else []
    paid_orders = [
        order
        for order in orders
        if _field_value(order, "payment_id")
        and _field_value(order, "status") in {"paid", "shipped", "refund_requested"}
    ]
    checks: list[bool] = []

    wants_order_status = _has_any(goal_text, ("订单状态", "物流", "order status", "shipping", "logistics"))
    wants_refund = _has_any(goal_text, ("退款", "退货", "refund", "return"))
    wants_support = _has_any(goal_text, ("客服", "工单", "support", "ticket"))
    wants_payment = _has_any(goal_text, ("支付", "付款", "pay", "payment"))
    wants_order = _has_any(goal_text, ("下单", "购买", "买", "订购", "order", "purchase", "buy"))
    wants_cart = _has_any(goal_text, ("购物车", "加购", "加入购物车", "cart"))
    wants_search = _has_any(goal_text, ("搜索", "查找", "找", "详情", "商品", "search", "find", "detail", "product"))

    if wants_order_status:
        checks.append("get_order_status" in successful_tools)
    if wants_refund:
        checks.append(bool(evidence.get("refunds")) and "request_refund" in successful_tools)
    if wants_support:
        checks.append(bool(evidence.get("tickets")) and "support_create_ticket" in successful_tools)
    if wants_payment:
        checks.append(bool(paid_orders) and "mock_payment" in successful_tools)
    elif wants_order:
        checks.append(bool(orders) and "create_order" in successful_tools)
    elif wants_cart:
        checks.append(bool(evidence.get("cart_items")) and "cart_add_item" in successful_tools)
    elif wants_search:
        checks.append(_has_successful_search_or_detail(result.trace))

    if not checks:
        return None
    return all(checks)


def _store_evidence(store: Any | None, *, user_id: str, role: str) -> dict[str, Any]:
    if store is None:
        return {"available": False, "user_id": user_id, "role": role}

    orders = [
        item
        for item in _values(getattr(store, "orders", {}))
        if _field_value(item, "user_id") == user_id
    ]
    order_ids = {
        str(order_id)
        for order in orders
        if (order_id := _field_value(order, "order_id"))
    }
    payments = [
        item
        for item in _values(getattr(store, "payments", {}))
        if _field_value(item, "order_id") in order_ids
    ]
    refunds = [
        item
        for item in _values(getattr(store, "refunds", {}))
        if _field_value(item, "order_id") in order_ids
    ]
    tickets = [
        item
        for item in _values(getattr(store, "tickets", {}))
        if _field_value(item, "user_id") == user_id
    ]

    return {
        "available": True,
        "user_id": user_id,
        "role": role,
        "cart_items": [_jsonable(item) for item in _cart_items(store, user_id)],
        "orders": [_jsonable(item) for item in orders],
        "payments": [_jsonable(item) for item in payments],
        "refunds": [_jsonable(item) for item in refunds],
        "tickets": [_jsonable(item) for item in tickets],
    }


def _cart_items(store: Any, user_id: str) -> list[Any]:
    cart_items = getattr(store, "cart_items", None)
    if callable(cart_items):
        try:
            return list(cart_items(user_id))
        except Exception:
            return []

    carts = getattr(store, "carts", {})
    if isinstance(carts, Mapping):
        user_cart = carts.get(user_id, {})
        return list(_values(user_cart))
    return []


def _is_invalid_tool_call(step: TaskStep) -> bool:
    if step.action_tool not in _VALID_TOOL_NAMES:
        return True
    if not isinstance(step.action_args, Mapping):
        return True
    if bool(getattr(step.observation, "blocked", False)):
        return True
    for call in _tool_calls(step):
        if _field_value(call, "tool_name") not in _VALID_TOOL_NAMES:
            return True
        if _field_value(call, "allowed") is False:
            return True
    return False


def _tool_calls(step: TaskStep) -> list[Any]:
    summary = getattr(step.observation, "summary", {})
    if not isinstance(summary, Mapping):
        return []
    calls = summary.get("tool_calls", [])
    if not isinstance(calls, Sequence) or isinstance(calls, (str, bytes)):
        return []
    return list(calls)


def _replan_triggered(result: TaskRunResult) -> bool:
    return bool(result.replan_count > 0 or any(step.replan_triggered for step in result.trace))


def _has_successful_search_or_detail(trace: Sequence[TaskStep]) -> bool:
    for step in trace:
        if bool(getattr(step.observation, "blocked", False)):
            continue
        if step.action_tool not in {"product_search", "get_product_detail"}:
            continue
        value = getattr(step.observation, "value", None)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            if len(value) > 0:
                return True
            continue
        if value is not None:
            return True
    return False


def _task_goal(result: TaskRunResult) -> str:
    goal = _clean_text(getattr(result.task_spec, "goal", ""))
    if goal:
        return goal
    raw_instruction = _clean_text(getattr(result.task_spec, "raw_instruction", ""))
    return raw_instruction or "unknown-task"


def _goal_text(result: TaskRunResult) -> str:
    task_spec = result.task_spec
    parts = [
        getattr(task_spec, "raw_instruction", ""),
        getattr(task_spec, "goal", ""),
        *list(getattr(task_spec, "subgoals", []) or []),
    ]
    return " ".join(_clean_text(part).lower() for part in parts if _clean_text(part))


def _has_any(text: str, markers: Sequence[str]) -> bool:
    return any(marker in text for marker in markers)


def _values(value: Any) -> list[Any]:
    if isinstance(value, Mapping):
        return list(value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    return []


def _field_value(value: Any, field_name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_jsonable(item) for item in value]
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


__all__ = [
    "TASK_EVAL_JUDGE_SYSTEM_PROMPT",
    "TaskEvaluationMetrics",
    "TaskEvaluationRecord",
    "TaskEvaluationReport",
    "evaluate_task_run",
    "evaluate_task_runs",
]
