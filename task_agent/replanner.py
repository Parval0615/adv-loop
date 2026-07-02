from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

from task_agent.models import Observation, Plan, TaskSpec
from task_agent.planner import _normalize_plan, _plan_schema_hint
from task_agent.prompts import REPLAN_SYSTEM_PROMPT
from task_agent.tool_registry import catalog_for_role


_NO_MATCH_MARKERS = (
    "没有找到匹配",
    "无匹配",
    "未找到匹配",
    "no match",
    "no results",
)
_STOCK_MARKERS = (
    "库存不足",
    "缺货",
    "无库存",
    "售罄",
    "stock_insufficient",
    "out of stock",
)
_PAYMENT_FAILURE_MARKERS = (
    "支付失败",
    "不允许支付",
    "支付金额必须",
    "payment_",
    "payment failed",
)
_ORDER_FAILURE_MARKERS = (
    "下单失败",
    "订单创建失败",
    "不能创建订单",
    "禁止下单",
    "empty_cart",
    "address_owner_mismatch",
)
_TOOL_ERROR_MARKERS = (
    "工具参数错误或调用失败",
    "未知电商工具",
    "工具目录和真实工具实现不一致",
    "真实工具返回类型异常",
    "tool error",
    "exception",
    "traceback",
    "异常",
)


def should_replan(obs: Observation, spec: TaskSpec) -> tuple[bool, str]:
    budget_cents = _budget_cents(spec)
    amount_cents = _amount_cents(obs)
    if budget_cents is not None and amount_cents is not None and amount_cents > budget_cents:
        return (
            True,
            f"预算不足: 工具结果金额 {amount_cents} 分超过预算 {budget_cents} 分，需要寻找更低价替代方案。",
        )

    tool_name = _tool_name(obs)
    answer_text = _clean_text(getattr(obs, "answer", ""))
    full_text = _observation_text(obs)

    if _is_search_no_match(obs, tool_name, full_text):
        return True, "搜索无匹配: 当前查询没有找到候选商品，需要调整关键词或选择替代商品。"

    if _is_out_of_stock(obs, full_text):
        return True, "缺货: 当前商品库存不足，需要尝试有货替代商品、调整数量或改走客服路径。"

    if _is_payment_failure(obs, tool_name, answer_text):
        return True, f"支付失败: {answer_text or '支付工具返回失败信号，需要重新生成支付或订单处理路径。'}"

    if _is_order_failure(obs, tool_name, answer_text):
        return True, f"下单失败: {answer_text or '下单工具返回失败信号，需要重新生成下单路径。'}"

    if _has_marker(full_text, _TOOL_ERROR_MARKERS):
        return True, f"工具异常: {answer_text or '工具调用返回异常信号，需要选择可用工具重试。'}"

    if bool(getattr(obs, "blocked", False)):
        return True, f"工具调用被阻断: {answer_text or '真实环境拦截了本次动作，需要绕开失败动作重规划。'}"

    return False, ""


def replan(
    spec: TaskSpec,
    history: Sequence[Any],
    failure: Any,
    role: str,
    llm: Any,
) -> Plan:
    catalog = catalog_for_role(role)
    allowed_tools = [
        entry["name"]
        for entry in catalog
        if isinstance(entry, Mapping) and isinstance(entry.get("name"), str)
    ]
    previous_revision = _max_revision(history)
    minimum_revision = previous_revision + 1 if previous_revision >= 0 else 1
    schema_hint = _plan_schema_hint(allowed_tools)
    schema_hint["minimum_revision"] = minimum_revision

    user_payload = {
        "task_spec": spec.to_dict(),
        "role": role,
        "tool_catalog": catalog,
        "history": _history_payload(history),
        "failure": _jsonable(failure),
        "previous_max_revision": previous_revision,
        "minimum_revision": minimum_revision,
    }
    try:
        generated = llm.complete_json(
            REPLAN_SYSTEM_PROMPT,
            _json_dumps(user_payload),
            schema_hint=schema_hint,
            seed=37 + max(previous_revision, 0),
            max_tokens=1024,
        )
    except Exception:
        generated = {}

    plan = _normalize_plan(generated, allowed_tools)
    if plan.revision < minimum_revision:
        plan.revision = minimum_revision
    return plan


def _budget_cents(spec: TaskSpec) -> int | None:
    constraints = getattr(spec, "constraints", {})
    if not isinstance(constraints, Mapping):
        return None
    for key in ("budget_cents", "max_budget_cents", "max_price_cents", "price_limit_cents"):
        cents = _int_or_none(constraints.get(key))
        if cents is not None:
            return cents
    for key in ("budget_yuan", "max_budget_yuan"):
        amount = _float_or_none(constraints.get(key))
        if amount is not None:
            return int(amount * 100)
    return None


def _amount_cents(obs: Observation) -> int | None:
    value = getattr(obs, "value", None)
    for field_name in ("amount_cents", "total_cents", "payable_cents", "payment_amount_cents", "price_cents"):
        amount = _field_value(value, field_name)
        cents = _int_or_none(amount)
        if cents is not None:
            return cents
    answer = _clean_text(getattr(obs, "answer", ""))
    match = re.search(r"(?:金额|价格|支付)[^\d]*(\d+(?:\.\d+)?)\s*元", answer)
    if match:
        amount = _float_or_none(match.group(1))
        if amount is not None:
            return int(amount * 100)
    return None


def _is_search_no_match(obs: Observation, tool_name: str, text: str) -> bool:
    value = getattr(obs, "value", None)
    if tool_name == "product_search" and isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 0:
        return True
    return _has_marker(text, _NO_MATCH_MARKERS)


def _is_out_of_stock(obs: Observation, text: str) -> bool:
    stock = _int_or_none(_field_value(getattr(obs, "value", None), "stock"))
    if stock is not None and stock <= 0:
        return True
    if re.search(r"(?:库存|stock)[^\d-]*0\b", text, flags=re.IGNORECASE):
        return True
    return _has_marker(text, _STOCK_MARKERS)


def _is_payment_failure(obs: Observation, tool_name: str, answer_text: str) -> bool:
    if tool_name == "mock_payment" and bool(getattr(obs, "blocked", False)):
        return True
    return _has_marker(answer_text, _PAYMENT_FAILURE_MARKERS)


def _is_order_failure(obs: Observation, tool_name: str, answer_text: str) -> bool:
    if tool_name == "create_order" and bool(getattr(obs, "blocked", False)):
        return True
    return _has_marker(answer_text, _ORDER_FAILURE_MARKERS)


def _tool_name(obs: Observation) -> str:
    summary = getattr(obs, "summary", {})
    if not isinstance(summary, Mapping):
        return ""
    tool = summary.get("tool")
    if isinstance(tool, str) and tool:
        return tool
    tool_calls = summary.get("tool_calls")
    if isinstance(tool_calls, Sequence) and not isinstance(tool_calls, (str, bytes)) and tool_calls:
        first = tool_calls[0]
        if isinstance(first, Mapping):
            tool = first.get("tool_name")
            if isinstance(tool, str):
                return tool
    return ""


def _observation_text(obs: Observation) -> str:
    parts = [
        _clean_text(getattr(obs, "answer", "")),
        _clean_text(getattr(obs, "risk_level", "")),
    ]
    summary = getattr(obs, "summary", None)
    value = getattr(obs, "value", None)
    for item in (summary, value):
        if item is None:
            continue
        parts.append(_json_dumps(_jsonable(item)))
    return "\n".join(part for part in parts if part)


def _has_marker(text: str, markers: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _field_value(value: Any, field_name: str) -> Any:
    if isinstance(value, Mapping):
        if field_name in value:
            return value[field_name]
        for nested in value.values():
            found = _field_value(nested, field_name)
            if found is not None:
                return found
        return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            found = _field_value(item, field_name)
            if found is not None:
                return found
        return None
    return getattr(value, field_name, None)


def _max_revision(history: Sequence[Any] | None) -> int:
    if history is None:
        return -1
    max_revision = -1
    for item in history:
        revision = _revision_from_item(item)
        if revision is not None:
            max_revision = max(max_revision, revision)
    return max_revision


def _revision_from_item(item: Any) -> int | None:
    if isinstance(item, Mapping):
        for key in ("revision", "plan_revision"):
            revision = _int_or_none(item.get(key))
            if revision is not None:
                return revision
        for key in ("plan", "current_plan"):
            nested = item.get(key)
            revision = _revision_from_item(nested)
            if revision is not None:
                return revision
        plans = item.get("plans")
        if isinstance(plans, Sequence) and not isinstance(plans, (str, bytes)):
            revisions = [_revision_from_item(plan) for plan in plans]
            revisions = [revision for revision in revisions if revision is not None]
            return max(revisions) if revisions else None
        return None
    revision = _int_or_none(getattr(item, "revision", None))
    if revision is not None:
        return revision
    plan = getattr(item, "plan", None)
    if plan is not None:
        return _revision_from_item(plan)
    plans = getattr(item, "plans", None)
    if isinstance(plans, Sequence) and not isinstance(plans, (str, bytes)):
        revisions = [_revision_from_item(plan_item) for plan_item in plans]
        revisions = [revision for revision in revisions if revision is not None]
        return max(revisions) if revisions else None
    return None


def _history_payload(history: Sequence[Any] | None) -> list[Any]:
    if history is None:
        return []
    return [_jsonable(item) for item in history]


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


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["should_replan", "replan"]
