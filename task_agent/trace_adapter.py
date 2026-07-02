from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import sentinel_proxy as _sentinel_proxy  # Priming import avoids trace_dag package circular import.
from task_agent.models import Plan, PlanStep, TaskRunResult, TaskStep
from trace_dag.builder import build_trace_report, write_trace_artifacts
from trace_dag.models import TraceReport


def task_run_to_trace_inputs(result: TaskRunResult) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    trace_id = _trace_id(result)
    events: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    plan_metadata = _plan_metadata_by_trace_index(result)
    parent_id: str | None = "task"

    for index, step in enumerate(result.trace, start=1):
        metadata = plan_metadata[index - 1] if index - 1 < len(plan_metadata) else {}
        intercept_id = _intercept_id(index)
        event = task_step_to_trace_event(
            step,
            index=index,
            trace_id=trace_id,
            intercept_id=intercept_id,
            parent_id=parent_id,
            plan_metadata=metadata,
        )
        decision = task_step_to_trace_decision(
            result,
            step,
            index=index,
            trace_id=trace_id,
            intercept_id=intercept_id,
            plan_metadata=metadata,
        )
        events.append(event)
        decisions.append(decision)
        parent_id = event["event_id"]

    if not decisions:
        decisions.append(_empty_trace_decision(result, trace_id))
    return events, decisions


def task_step_to_trace_event(
    step: TaskStep,
    *,
    index: int,
    trace_id: str,
    intercept_id: str,
    parent_id: str | None,
    plan_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = dict(plan_metadata or {})
    blocked = bool(step.observation.blocked)
    return {
        "trace_id": trace_id,
        "event_id": f"tool:{intercept_id}",
        "event_type": "tool_call",
        "name": step.action_tool or "unknown_tool",
        "actor": "task_agent",
        "parent_id": parent_id,
        "timestamp": f"step-{index:03d}",
        "arguments": _jsonable(step.action_args),
        "result": {
            "answer": step.observation.answer,
            "blocked": blocked,
            "risk_level": step.observation.risk_level,
            "value": _jsonable(step.observation.value),
            "summary": _jsonable(step.observation.summary),
            "plan_step_id": step.plan_step_id,
            "plan_revision": metadata.get("plan_revision"),
            "candidate_tool": metadata.get("candidate_tool"),
            "thought": step.thought,
            "decision_reason": step.decision_reason,
            "replan_triggered": step.replan_triggered,
            "sentinel_intercept_id": intercept_id,
            "sentinel_decision": {
                "intercept_id": intercept_id,
                "decision": "block" if blocked else "allow",
                "reason": step.decision_reason or step.observation.answer,
                "executed": not blocked,
            },
        },
    }


def task_step_to_trace_decision(
    result: TaskRunResult,
    step: TaskStep,
    *,
    index: int,
    trace_id: str,
    intercept_id: str,
    plan_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = dict(plan_metadata or {})
    blocked = bool(step.observation.blocked)
    return {
        "trace_id": trace_id,
        "intercept_id": intercept_id,
        "context": {
            "trace_id": trace_id,
            "task": result.task_spec.raw_instruction,
            "goal": result.task_spec.goal,
            "subgoals": list(result.task_spec.subgoals),
            "constraints": _jsonable(result.task_spec.constraints),
            "plan_revision": metadata.get("plan_revision"),
            "plan_step_id": step.plan_step_id,
            "candidate_tool": metadata.get("candidate_tool"),
            "replan_count": result.replan_count,
            "goal_achieved": result.goal_achieved,
            "injection_findings": [],
        },
        "request": {
            "name": step.action_tool or "unknown_tool",
            "actor": "task_agent",
            "arguments": _jsonable(step.action_args),
            "intercept_id": intercept_id,
        },
        "decision": {
            "decision": "block" if blocked else "allow",
            "reason": step.decision_reason or step.observation.answer,
            "risk_level": step.observation.risk_level,
            "step_index": index,
            "replan_triggered": step.replan_triggered,
            "blocked": blocked,
        },
    }


def build_plan_trace_report(result: TaskRunResult) -> TraceReport:
    events, decisions = task_run_to_trace_inputs(result)
    return build_trace_report(events, decisions)


def export_plan_trace(result: TaskRunResult, out_dir: str | Path) -> dict[str, str]:
    artifacts_dir = Path(out_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    events, decisions = task_run_to_trace_inputs(result)
    return write_trace_artifacts(artifacts_dir, events, decisions)


def _empty_trace_decision(result: TaskRunResult, trace_id: str) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "intercept_id": "agent-plan-000",
        "context": {
            "trace_id": trace_id,
            "task": result.task_spec.raw_instruction,
            "goal": result.task_spec.goal,
            "subgoals": list(result.task_spec.subgoals),
            "constraints": _jsonable(result.task_spec.constraints),
            "replan_count": result.replan_count,
            "goal_achieved": result.goal_achieved,
            "injection_findings": [],
        },
        "request": {
            "name": "plan",
            "actor": "task_agent",
            "arguments": {"plans": [_jsonable(plan) for plan in result.plans]},
            "intercept_id": "agent-plan-000",
        },
        "decision": {
            "decision": "allow",
            "reason": "Plan generated but no tool step was executed.",
            "risk_level": "normal",
            "step_index": 0,
            "replan_triggered": False,
            "blocked": False,
        },
    }


def _plan_metadata_by_trace_index(result: TaskRunResult) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []
    plan_index = 0
    plans = list(result.plans)

    for step in result.trace:
        plan = plans[plan_index] if plan_index < len(plans) else None
        plan_step = _find_plan_step(plan, step.plan_step_id)
        metadata.append(
            {
                "plan_revision": plan.revision if plan else None,
                "candidate_tool": plan_step.candidate_tool if plan_step else None,
                "args_hint": _jsonable(plan_step.args_hint) if plan_step else {},
            }
        )
        if step.replan_triggered and plan_index + 1 < len(plans):
            plan_index += 1

    return metadata


def _find_plan_step(plan: Plan | None, step_id: str) -> PlanStep | None:
    if plan is None:
        return None
    for step in plan.steps:
        if step.step_id == step_id:
            return step
    return None


def _trace_id(result: TaskRunResult) -> str:
    payload = {
        "task": result.task_spec.raw_instruction,
        "plans": [_jsonable(plan) for plan in result.plans],
        "trace": [
            {
                "plan_step_id": step.plan_step_id,
                "action_tool": step.action_tool,
                "action_args": _jsonable(step.action_args),
                "blocked": step.observation.blocked,
                "replan_triggered": step.replan_triggered,
            }
            for step in result.trace
        ],
        "goal_achieved": result.goal_achieved,
        "replan_count": result.replan_count,
    }
    digest = hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()
    return f"task-agent-{digest[:12]}"


def _intercept_id(index: int) -> str:
    return f"agent-step-{index:03d}"


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _jsonable(value.to_dict())
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable(item) for item in value]
    try:
        json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


__all__ = [
    "build_plan_trace_report",
    "export_plan_trace",
    "task_run_to_trace_inputs",
    "task_step_to_trace_decision",
    "task_step_to_trace_event",
]
