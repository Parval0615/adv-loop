from __future__ import annotations

from copy import deepcopy
from typing import Any

from auto_defense_system.ecommerce_agent import tools as ecommerce_tools
from auto_defense_system.ecommerce_agent.models import RiskLevel, ToolCallRecord, ToolExecution
from auto_defense_system.ecommerce_agent.store import EcommerceStore


TOOL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": "product_search",
        "description": "搜索公开商品，返回匹配商品 ID 列表和简要信息。",
        "risk_level": "low",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "搜索关键词，可为空。"}},
            "required": [],
        },
    },
    {
        "name": "get_product_detail",
        "description": "读取商品详情、价格、库存和评价摘要。",
        "risk_level": "low",
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "string", "description": "商品 ID。"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "get_user_profile",
        "description": "读取当前用户的最小画像；管理员可指定目标用户。",
        "risk_level": "medium",
        "parameters": {
            "type": "object",
            "properties": {
                "target_user_id": {"type": "string", "description": "目标用户 ID，省略时读取当前用户。"},
            },
            "required": [],
        },
    },
    {
        "name": "cart_add_item",
        "description": "将商品加入当前用户购物车，库存和数量由真实 store 校验。",
        "risk_level": "medium",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "商品 ID。"},
                "quantity": {"type": "integer", "description": "新增数量，默认 1。"},
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "cart_update_quantity",
        "description": "修改当前用户购物车中某个商品的数量，数量小于等于 0 时移除。",
        "risk_level": "medium",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "商品 ID。"},
                "quantity": {"type": "integer", "description": "目标数量。"},
            },
            "required": ["product_id", "quantity"],
        },
    },
    {
        "name": "get_order_status",
        "description": "查询当前用户有权限访问的订单状态和物流状态。",
        "risk_level": "medium",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "订单 ID。"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "support_create_ticket",
        "description": "为当前用户创建客服工单，可关联订单。",
        "risk_level": "medium",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "客服问题描述。"},
                "order_id": {"type": "string", "description": "可选订单 ID。"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "apply_coupon",
        "description": "为当前用户购物车应用优惠券。",
        "risk_level": "high",
        "parameters": {
            "type": "object",
            "properties": {"coupon_id": {"type": "string", "description": "优惠券 ID。"}},
            "required": ["coupon_id"],
        },
    },
    {
        "name": "create_order",
        "description": "基于当前用户购物车和地址创建订单，金额由服务端重新计算。",
        "risk_level": "high",
        "parameters": {
            "type": "object",
            "properties": {"address_id": {"type": "string", "description": "当前用户地址 ID。"}},
            "required": ["address_id"],
        },
    },
    {
        "name": "mock_payment",
        "description": "对当前用户订单执行模拟支付，支付金额必须等于服务端订单金额。",
        "risk_level": "high",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单 ID。"},
                "amount_cents": {"type": "integer", "description": "支付金额，单位分。"},
            },
            "required": ["order_id", "amount_cents"],
        },
    },
    {
        "name": "request_refund",
        "description": "为当前用户已支付或已发货订单发起退款申请。",
        "risk_level": "high",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单 ID。"},
                "reason": {"type": "string", "description": "退款原因。"},
            },
            "required": ["order_id", "reason"],
        },
    },
    {
        "name": "merchant_update_price",
        "description": "商家或管理员修改商品价格。",
        "risk_level": "critical",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "商品 ID。"},
                "new_price_cents": {"type": "integer", "description": "新价格，单位分。"},
            },
            "required": ["product_id", "new_price_cents"],
        },
    },
    {
        "name": "merchant_update_stock",
        "description": "商家或管理员修改商品库存。",
        "risk_level": "critical",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "商品 ID。"},
                "new_stock": {"type": "integer", "description": "新库存。"},
            },
            "required": ["product_id", "new_stock"],
        },
    },
)

_TOOL_NAMES = {entry["name"] for entry in TOOL_CATALOG}


def catalog_for_role(role: str) -> list[dict[str, Any]]:
    catalog = []
    for entry in TOOL_CATALOG:
        if role == "buyer" and entry["name"].startswith("merchant_"):
            continue
        catalog.append(deepcopy(entry))
    return catalog


def invoke(
    tool_name: str,
    args: dict[str, Any] | None,
    *,
    store: EcommerceStore,
    user_id: str,
    role: str,
) -> ToolExecution:
    if not isinstance(tool_name, str) or tool_name not in _TOOL_NAMES:
        return _blocked_execution(tool_name, args, f"未知电商工具被默认拦截: {tool_name!r}", "high")
    if not isinstance(args, dict):
        return _blocked_execution(tool_name, args, "工具参数必须是 JSON object。", "high")

    try:
        tool_fn = getattr(ecommerce_tools, tool_name)
    except AttributeError:
        return _blocked_execution(tool_name, args, f"工具目录和真实工具实现不一致: {tool_name}", "high")

    try:
        result = tool_fn(store, user_id=user_id, role=role, **args)
    except Exception as exc:
        risk_level = getattr(exc, "risk_level", "high")
        return _blocked_execution(tool_name, args, f"工具参数错误或调用失败: {exc}", risk_level)

    if not isinstance(result, ToolExecution):
        return _blocked_execution(tool_name, args, f"真实工具返回类型异常: {type(result).__name__}", "high")
    return result


def _blocked_execution(tool_name: Any, args: Any, reason: str, risk_level: RiskLevel) -> ToolExecution:
    name = tool_name if isinstance(tool_name, str) else "<invalid_tool_name>"
    return ToolExecution(
        answer=reason,
        tool_calls=[
            ToolCallRecord(
                tool_name=name,
                arguments=_safe_arguments(args),
                allowed=False,
                result=reason,
                risk_level=risk_level,
                reason=reason,
            )
        ],
        blocked=True,
        risk_level=risk_level,
    )


def _safe_arguments(args: Any) -> dict[str, Any]:
    if isinstance(args, dict):
        try:
            return deepcopy(args)
        except Exception:
            return {"_invalid_args": repr(args)}
    return {"_invalid_args": repr(args)}


__all__ = ["TOOL_CATALOG", "catalog_for_role", "invoke"]
