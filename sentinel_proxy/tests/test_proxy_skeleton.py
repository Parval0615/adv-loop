from __future__ import annotations

import json
from pathlib import Path

from arena.dev_agent import DevAgent, SCENARIO_TASKS
from sentinel_proxy.pipeline import SentinelPipeline, ToolNameDecisionStage


def _tool_events(result):
    return [event for event in result.events if event.event_type == "tool_call"]


def _pipeline_for(decisions: dict[str, str]) -> SentinelPipeline:
    return SentinelPipeline(stages=[("test_stub", ToolNameDecisionStage(decisions))])


def test_observe_mode_allows_smoke_all_tools_and_records_allow_decisions(tmp_path: Path) -> None:
    result = DevAgent(force_offline=True, artifacts_root=tmp_path, proxy_mode="observe").run(
        SCENARIO_TASKS["smoke-all-tools"],
        scenario_id="smoke-all-tools",
    )

    tool_events = _tool_events(result)
    assert {
        "fs.read",
        "fs.write",
        "net.fetch",
        "exec",
        "git.push",
        "sub_agent.dispatch",
    }.issubset({event.name for event in tool_events})
    assert len(result.sentinel_decisions) == len(tool_events)
    assert all(event.result["sentinel_decision"]["decision"] == "allow" for event in tool_events)
    assert all(event.result["sentinel_decision"]["executed"] is True for event in tool_events)
    assert (result.artifacts_dir / "sentinel_decisions.jsonl").exists()


def test_observe_mode_records_block_but_still_executes(tmp_path: Path) -> None:
    result = DevAgent(
        force_offline=True,
        artifacts_root=tmp_path,
        proxy_mode="observe",
        sentinel_pipeline=_pipeline_for({"net.fetch": "block"}),
    ).run(SCENARIO_TASKS["clean-docs"], scenario_id="clean-docs")

    net_event = next(event for event in _tool_events(result) if event.name == "net.fetch")
    assert net_event.result["sentinel_decision"]["decision"] == "block"
    assert net_event.result["sentinel_decision"]["executed"] is True
    assert net_event.result["status"] == 200
    assert "GET /health" in result.final_answer


def test_enforce_mode_blocks_net_fetch_without_calling_network_mcp(tmp_path: Path) -> None:
    result = DevAgent(
        force_offline=True,
        artifacts_root=tmp_path,
        proxy_mode="enforce",
        sentinel_pipeline=_pipeline_for({"net.fetch": "block"}),
    ).run(SCENARIO_TASKS["clean-docs"], scenario_id="clean-docs")

    net_event = next(event for event in _tool_events(result) if event.name == "net.fetch")
    assert net_event.result["blocked"] is True
    assert net_event.result["sentinel_decision"]["executed"] is False
    assert not [event for event in result.events if event.event_type == "resource_read" and event.actor == "network_mcp"]


def test_enforce_mode_ask_for_git_push_does_not_create_remote(tmp_path: Path) -> None:
    result = DevAgent(
        force_offline=True,
        artifacts_root=tmp_path,
        proxy_mode="enforce",
        sentinel_pipeline=_pipeline_for({"git.push": "ask"}),
    ).run(SCENARIO_TASKS["smoke-all-tools"], scenario_id="smoke-all-tools")

    git_event = next(event for event in _tool_events(result) if event.name == "git.push")
    assert git_event.result["requires_confirmation"] is True
    assert git_event.result["sentinel_decision"]["decision"] == "ask"
    assert git_event.result["sentinel_decision"]["executed"] is False
    assert not (result.artifacts_dir / "remote.git").exists()


def test_resource_read_event_carries_sentinel_context(tmp_path: Path) -> None:
    result = DevAgent(force_offline=True, artifacts_root=tmp_path).run(
        SCENARIO_TASKS["clean-readme"],
        scenario_id="clean-readme",
    )

    resource_event = next(event for event in result.events if event.event_type == "resource_read")
    context = resource_event.result["sentinel_context"]
    assert context["task"] == SCENARIO_TASKS["clean-readme"]
    assert context["scenario_id"] == "clean-readme"
    assert context["resource_reads"][-1]["arguments"]["path"] == "README.md"
    assert context["tool_calls"][-1]["name"] == "fs.read"


def test_sub_dispatch_event_carries_sentinel_context(tmp_path: Path) -> None:
    result = DevAgent(force_offline=True, artifacts_root=tmp_path).run(
        SCENARIO_TASKS["attack-sub-agent-secret"],
        scenario_id="attack-sub-agent-secret",
    )

    dispatch_event = next(event for event in result.events if event.event_type == "sub_dispatch")
    context = dispatch_event.result["sentinel_context"]
    assert context["task"] == SCENARIO_TASKS["attack-sub-agent-secret"]
    assert context["tool_calls"][-1]["name"] == "sub_agent.dispatch"
    assert context["sub_dispatches"][-1]["payload_summary"]["secret"]["type"] == "str"


def test_each_tp00_tool_call_has_one_proxy_decision(tmp_path: Path) -> None:
    for scenario_id, task in SCENARIO_TASKS.items():
        result = DevAgent(force_offline=True, artifacts_root=tmp_path / scenario_id).run(
            task,
            scenario_id=scenario_id,
        )
        assert len(result.sentinel_decisions) == len(_tool_events(result))


def test_sentinel_decisions_jsonl_contains_context_snapshot(tmp_path: Path) -> None:
    result = DevAgent(force_offline=True, artifacts_root=tmp_path).run(
        SCENARIO_TASKS["clean-readme"],
        scenario_id="clean-readme",
    )

    lines = (result.artifacts_dir / "sentinel_decisions.jsonl").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert records[0]["mode"] == "observe"
    assert records[0]["request"]["name"] == "fs.read"
    assert records[0]["context"]["task"] == SCENARIO_TASKS["clean-readme"]
    assert records[0]["decision"]["decision"] == "allow"
