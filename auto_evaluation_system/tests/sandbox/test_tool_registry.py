from auto_evaluation_system.sandbox.tools.registry import ToolRegistry


def test_mock_tool_invocation() -> None:
    registry = ToolRegistry(mode="mock")
    registry.register_defaults()
    result = registry.invoke("get_weather", {"city": "Beijing"})
    assert result["city"] == "Beijing"
    assert registry.call_counts["get_weather"] == 1


def test_openai_tools_schema() -> None:
    registry = ToolRegistry(mode="mock")
    registry.register_defaults()
    schemas = registry.openai_tools_schema()
    names = {item["function"]["name"] for item in schemas}
    assert names == {"get_weather", "search_news"}


def test_mode_switch_to_real_when_handler_present() -> None:
    registry = ToolRegistry(mode="real")
    registry.register_defaults()
    registry.register_real("get_weather", lambda city: {"city": city, "source": "real"})
    result = registry.invoke("get_weather", {"city": "Shanghai"})
    assert result["source"] == "real"
