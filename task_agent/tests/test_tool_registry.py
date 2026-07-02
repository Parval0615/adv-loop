from __future__ import annotations

import inspect

import pytest

from auto_defense_system.ecommerce_agent import tools as ecommerce_tools
from auto_defense_system.ecommerce_agent.fixtures import create_demo_store
from task_agent.tool_registry import TOOL_CATALOG, catalog_for_role, invoke


def test_tool_catalog_covers_public_ecommerce_tools() -> None:
    public_tool_names = {
        name
        for name, value in vars(ecommerce_tools).items()
        if inspect.isfunction(value) and value.__module__ == ecommerce_tools.__name__ and not name.startswith("_")
    }
    catalog_names = {entry["name"] for entry in TOOL_CATALOG}

    assert len(TOOL_CATALOG) == 13
    assert catalog_names == public_tool_names


def test_catalog_for_role_filters_merchant_tools_from_buyer() -> None:
    buyer_names = {entry["name"] for entry in catalog_for_role("buyer")}
    merchant_names = {entry["name"] for entry in catalog_for_role("merchant")}

    assert "merchant_update_price" not in buyer_names
    assert "merchant_update_stock" not in buyer_names
    assert "cart_add_item" in buyer_names
    assert "merchant_update_price" in merchant_names
    assert "merchant_update_stock" in merchant_names


def test_invoke_cart_add_item_calls_real_tool_and_mutates_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store = create_demo_store()
    original_cart_add_item = ecommerce_tools.cart_add_item
    calls = []

    def spy_cart_add_item(real_store, *, user_id: str, role: str, product_id: str, quantity: int = 1):
        calls.append(
            {
                "store": real_store,
                "user_id": user_id,
                "role": role,
                "product_id": product_id,
                "quantity": quantity,
            }
        )
        return original_cart_add_item(
            real_store,
            user_id=user_id,
            role=role,
            product_id=product_id,
            quantity=quantity,
        )

    monkeypatch.setattr(ecommerce_tools, "cart_add_item", spy_cart_add_item)

    result = invoke(
        "cart_add_item",
        {"product_id": "p1001", "quantity": 2},
        store=store,
        user_id="buyer_001",
        role="buyer",
    )

    assert result.blocked is False
    assert calls == [
        {
            "store": store,
            "user_id": "buyer_001",
            "role": "buyer",
            "product_id": "p1001",
            "quantity": 2,
        }
    ]
    assert [(item.product_id, item.quantity) for item in store.cart_items("buyer_001")] == [("p1001", 2)]


def test_invoke_unknown_tool_returns_blocked_execution() -> None:
    result = invoke(
        "transfer_money",
        {"amount_cents": 100},
        store=create_demo_store(),
        user_id="buyer_001",
        role="buyer",
    )

    assert result.blocked is True
    assert result.risk_level == "high"
    assert result.tool_calls[0].allowed is False
    assert "未知电商工具" in result.answer


@pytest.mark.parametrize(
    ("tool_name", "args"),
    [
        ("get_product_detail", {}),
        ("cart_add_item", {"product_id": "p1001", "quantity": "two"}),
    ],
)
def test_invoke_parameter_errors_return_blocked_execution(tool_name: str, args: dict) -> None:
    result = invoke(
        tool_name,
        args,
        store=create_demo_store(),
        user_id="buyer_001",
        role="buyer",
    )

    assert result.blocked is True
    assert result.risk_level == "high"
    assert result.tool_calls[0].allowed is False
    assert "工具参数错误或调用失败" in result.answer
