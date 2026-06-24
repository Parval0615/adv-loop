from agent_security_sdk import EcommerceEnterpriseAdapter


def test_ecommerce_sdk_adapter_sends_lists_and_exports() -> None:
    adapter = EcommerceEnterpriseAdapter(session_id="sdk-test")

    tools = adapter.list_tools()
    result = adapter.send_message("buyer_001", "搜索 耳机", {"role": "buyer"})
    trajectory = adapter.export_trajectory()

    assert any(tool.name == "product_search" for tool in tools)
    assert result.blocked is False
    assert "p1001" in result.answer
    assert trajectory["session_id"] == "sdk-test"
    assert trajectory["turns"][0]["tool_calls"]


def test_ecommerce_sdk_adapter_masks_sensitive_message_in_trajectory() -> None:
    adapter = EcommerceEnterpriseAdapter(session_id="sdk-pii")

    adapter.send_message("buyer_001", "联系客服 我的手机号 13812345678 包装破损", {"role": "buyer"})
    trajectory = adapter.export_trajectory()

    assert "13812345678" not in str(trajectory)
    assert "138****5678" in str(trajectory)
