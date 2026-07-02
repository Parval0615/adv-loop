from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from task_agent.models import Plan, PlanStep, TaskSpec
from task_agent.prompts import PLAN_GENERATION_SYSTEM_PROMPT, TASK_PARSE_SYSTEM_PROMPT
from task_agent.tool_registry import catalog_for_role


TASK_PARSE_SCHEMA_HINT: dict[str, Any] = {
    "type": "object",
    "required": ["raw_instruction", "goal", "subgoals", "constraints", "entities"],
    "properties": {
        "raw_instruction": {"type": "string"},
        "goal": {"type": "string"},
        "subgoals": {"type": "array", "items": {"type": "string"}},
        "constraints": {"type": "object"},
        "entities": {"type": "object"},
        "parse_mode": {"type": "string"},
    },
}


def parse_task(instruction: str, llm: Any) -> TaskSpec:
    instruction_text = instruction if isinstance(instruction, str) else str(instruction)
    user_payload = {"instruction": instruction_text}
    try:
        parsed = llm.complete_json(
            TASK_PARSE_SYSTEM_PROMPT,
            _json_dumps(user_payload),
            schema_hint=TASK_PARSE_SCHEMA_HINT,
            seed=0,
            max_tokens=1024,
        )
    except Exception:
        parsed = {}
    return _normalize_task_spec(instruction_text, parsed)


def make_plan(spec: TaskSpec, role: str, llm: Any) -> Plan:
    catalog = catalog_for_role(role)
    allowed_tools = [
        entry["name"]
        for entry in catalog
        if isinstance(entry, Mapping) and isinstance(entry.get("name"), str)
    ]
    schema_hint = _plan_schema_hint(allowed_tools)
    user_payload = {
        "task_spec": spec.to_dict(),
        "role": role,
        "tool_catalog": catalog,
    }
    try:
        generated = llm.complete_json(
            PLAN_GENERATION_SYSTEM_PROMPT,
            _json_dumps(user_payload),
            schema_hint=schema_hint,
            seed=1,
            max_tokens=1024,
        )
    except Exception:
        generated = {}
    return _normalize_plan(generated, allowed_tools)


def _normalize_task_spec(instruction: str, parsed: Any) -> TaskSpec:
    data = parsed if isinstance(parsed, Mapping) else {}
    raw_instruction = _text_or_default(data.get("raw_instruction"), instruction)
    goal = _text_or_default(data.get("goal"), instruction.strip())
    subgoals = _text_list(data.get("subgoals"))
    if not subgoals:
        subgoals = _derive_subgoals(instruction)
    constraints = dict(data.get("constraints")) if isinstance(data.get("constraints"), Mapping) else {}
    entities = dict(data.get("entities")) if isinstance(data.get("entities"), Mapping) else {}
    parse_mode = _text_or_default(data.get("parse_mode"), _text_or_default(data.get("mode"), "llm"))

    return TaskSpec(
        raw_instruction=raw_instruction,
        goal=goal,
        subgoals=subgoals,
        constraints=constraints,
        entities=entities,
        parse_mode=parse_mode,
    )


def _normalize_plan(generated: Any, allowed_tools: Sequence[str]) -> Plan:
    data = generated if isinstance(generated, Mapping) else {}
    revision = _non_negative_int(data.get("revision"), default=0)
    raw_steps = _raw_steps(data)
    if not raw_steps:
        raw_steps = [{"candidate_tool": data.get("choice")}]

    safe_tool = _safe_default_tool(allowed_tools)
    allowed_set = set(allowed_tools)
    steps: list[PlanStep] = []
    seen_step_ids: set[str] = set()
    for index, raw_step in enumerate(raw_steps, start=1):
        step_id, candidate_tool, args_hint = _step_fields(raw_step)
        if not step_id or step_id in seen_step_ids:
            step_id = f"step-{index}"
        seen_step_ids.add(step_id)

        if candidate_tool not in allowed_set:
            candidate_tool = safe_tool
        if not isinstance(args_hint, Mapping):
            args_hint = {}

        steps.append(
            PlanStep(
                step_id=step_id,
                candidate_tool=candidate_tool,
                args_hint=dict(args_hint),
            )
        )

    return Plan(steps=steps, revision=revision)


def _plan_schema_hint(allowed_tools: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["revision", "steps"],
        "choices": list(allowed_tools),
        "properties": {
            "revision": {"type": "integer"},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["step_id", "candidate_tool", "args_hint"],
                    "properties": {
                        "step_id": {"type": "string"},
                        "candidate_tool": {"type": "string", "enum": list(allowed_tools)},
                        "args_hint": {"type": "object"},
                    },
                },
            },
        },
    }


def _raw_steps(data: Mapping[str, Any]) -> list[Any]:
    steps = data.get("steps")
    if isinstance(steps, Mapping):
        return [steps]
    if isinstance(steps, Sequence) and not isinstance(steps, (str, bytes)):
        return list(steps)
    return []


def _step_fields(raw_step: Any) -> tuple[str, str, Any]:
    if isinstance(raw_step, Mapping):
        step_id = _clean_text(raw_step.get("step_id"))
        candidate_tool = _clean_text(
            raw_step.get("candidate_tool") or raw_step.get("tool") or raw_step.get("choice")
        )
        args_hint = raw_step.get("args_hint")
        if args_hint is None:
            args_hint = raw_step.get("arguments", {})
        return step_id, candidate_tool, args_hint
    if isinstance(raw_step, str):
        return "", raw_step.strip(), {}
    return "", "", {}


def _safe_default_tool(allowed_tools: Sequence[str]) -> str:
    for tool_name in ("product_search", "get_product_detail", "get_user_profile"):
        if tool_name in allowed_tools:
            return tool_name
    return allowed_tools[0] if allowed_tools else ""


def _derive_subgoals(instruction: str) -> list[str]:
    pieces = re.split(r"[，,。；;、]|\b(?:then|and)\b|(?:然后|再|并且|同时|以及)", instruction)
    subgoals = [piece.strip() for piece in pieces if piece.strip()]
    return subgoals or ([instruction.strip()] if instruction.strip() else [])


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return _derive_subgoals(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [text for item in value if (text := _clean_text(item))]
    return []


def _text_or_default(value: Any, default: str) -> str:
    text = _clean_text(value)
    return text if text else default


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _non_negative_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


__all__ = ["TASK_PARSE_SCHEMA_HINT", "parse_task", "make_plan"]
