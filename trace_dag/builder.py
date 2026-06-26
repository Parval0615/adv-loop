from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from trace_dag.models import TraceEdge, TraceGraph, TraceNode, TraceReport


def build_trace_report(events: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> TraceReport:
    trace_id = _trace_id(events, decisions)
    nodes: list[TraceNode] = [
        TraceNode(
            node_id="task",
            node_type="task",
            label="User task",
            actor="user",
            metadata={"task": _task(decisions)},
        )
    ]
    edges: list[TraceEdge] = []
    evidence_refs: list[dict[str, Any]] = []

    findings = _unique_findings(decisions)
    for finding in findings:
        node_id = f"finding:{finding.get('finding_id')}"
        nodes.append(
            TraceNode(
                node_id=node_id,
                node_type="injection_finding",
                label=f"{finding.get('source_type')}:{finding.get('pattern')}",
                actor=str(finding.get("source_channel", "unknown")),
                metadata=finding,
            )
        )
        edges.append(TraceEdge(source=node_id, target="task", relation="influences"))
        evidence_refs.append({"type": "injection_finding", "id": finding.get("finding_id")})

    tool_events = [event for event in events if event.get("event_type") == "tool_call"]
    tool_events_by_intercept = {
        _event_intercept_id(event): event
        for event in tool_events
        if _event_intercept_id(event)
    }
    for index, decision in enumerate(decisions, start=1):
        request = decision.get("request", {})
        intercept_id = str(decision.get("intercept_id") or request.get("intercept_id") or f"idx-{index}")
        node_id = f"decision:{intercept_id}"
        nodes.append(
            TraceNode(
                node_id=node_id,
                node_type="decision",
                label=f"{request.get('name')} -> {decision.get('decision', {}).get('decision')}",
                actor=str(request.get("actor", "sentinel_proxy")),
                metadata={**decision.get("decision", {}), "intercept_id": intercept_id},
            )
        )
        edges.append(TraceEdge(source="task", target=node_id, relation="intercepted"))
        tool_event = tool_events_by_intercept.get(intercept_id)
        if tool_event:
            edges.append(TraceEdge(source=node_id, target=tool_event["event_id"], relation="controls"))

    for event in events:
        node_id = event.get("event_id", "")
        nodes.append(
            TraceNode(
                node_id=node_id,
                node_type=str(event.get("event_type", "event")),
                label=str(event.get("name", "event")),
                actor=str(event.get("actor", "unknown")),
                metadata={
                    "arguments": event.get("arguments", {}),
                    "result": _summarize_value(event.get("result")),
                    "timestamp": event.get("timestamp"),
                },
            )
        )
        parent = event.get("parent_id")
        if parent:
            edges.append(TraceEdge(source=parent, target=node_id, relation="parent"))

    edges.extend(_dataflow_edges(events))
    graph = TraceGraph(trace_id=trace_id, nodes=nodes, edges=edges)
    call_details = [_call_detail(event) for event in tool_events]
    context_sources = [_context_source(finding) for finding in findings]
    if not context_sources:
        context_sources = [{"source_type": "user_task", "source_channel": "context.task", "field_path": "context.task", "evidence": _task(decisions)}]
    impact_scope = _impact_scope(events, decisions)
    trigger_source = context_sources[0] if context_sources else {"source_type": "user_task", "summary": _task(decisions)}

    return TraceReport(
        trace_id=trace_id,
        graph=graph,
        trigger_source=trigger_source,
        chain_nodes=[node.to_dict() for node in nodes if node.node_type in ("decision", "tool_call", "resource_read", "sub_dispatch")],
        context_sources=context_sources,
        call_details=call_details,
        impact_scope=impact_scope,
        evidence_refs=evidence_refs,
    )


def write_trace_artifacts(
    artifacts_dir: Path,
    events: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> dict[str, str]:
    report = build_trace_report(events, decisions)
    graph_path = artifacts_dir / "trace_graph.json"
    report_path = artifacts_dir / "trace_report.json"
    timeline_path = artifacts_dir / "trace_timeline.jsonl"
    mermaid_path = artifacts_dir / "trace_graph.md"
    integrity_path = artifacts_dir / "trace_integrity.json"

    graph_path.write_text(json.dumps(report.graph.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    with timeline_path.open("w", encoding="utf-8") as handle:
        for item in _timeline(events, decisions):
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    mermaid_path.write_text(_mermaid(report.graph), encoding="utf-8")
    integrity_path.write_text(json.dumps(_integrity(report.graph), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "trace_graph": str(graph_path),
        "trace_report": str(report_path),
        "trace_timeline": str(timeline_path),
        "trace_mermaid": str(mermaid_path),
        "trace_integrity": str(integrity_path),
    }


def _trace_id(events: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> str:
    for event in events:
        if event.get("trace_id"):
            return str(event["trace_id"])
    for decision in decisions:
        trace_id = decision.get("trace_id") or decision.get("context", {}).get("trace_id")
        if trace_id:
            return str(trace_id)
    return "trace-unknown"


def _task(decisions: list[dict[str, Any]]) -> str:
    for decision in decisions:
        task = decision.get("context", {}).get("task") or decision.get("context_before", {}).get("task")
        if isinstance(task, str):
            return task
    return ""


def _unique_findings(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen = set()
    for decision in decisions:
        for finding in decision.get("context", {}).get("injection_findings", []):
            finding_id = finding.get("finding_id")
            if not finding_id or finding_id in seen:
                continue
            seen.add(finding_id)
            result.append(finding)
    return result


def _context_source(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": finding.get("source_type"),
        "source_channel": finding.get("source_channel"),
        "field_path": finding.get("field_path"),
        "anchor": finding.get("metadata", {}).get("anchor", {}),
        "pattern": finding.get("pattern"),
        "confidence": finding.get("confidence"),
        "evidence": finding.get("evidence"),
    }


def _call_detail(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event.get("event_id"),
        "intercept_id": _event_intercept_id(event),
        "name": event.get("name"),
        "actor": event.get("actor"),
        "arguments": _summarize_value(event.get("arguments")),
        "sentinel_decision": event.get("result", {}).get("sentinel_decision") if isinstance(event.get("result"), dict) else None,
    }


def _event_intercept_id(event: dict[str, Any]) -> str | None:
    result = event.get("result")
    if not isinstance(result, dict):
        return None
    value = result.get("sentinel_intercept_id") or result.get("sentinel_decision", {}).get("intercept_id")
    return str(value) if value else None


def _dataflow_edges(events: list[dict[str, Any]]) -> list[TraceEdge]:
    edges: list[TraceEdge] = []
    sensitive_resources = _sensitive_resource_events(events)
    for resource_event in sensitive_resources:
        parent = resource_event.get("parent_id")
        if parent:
            edges.append(
                TraceEdge(
                    source=resource_event["event_id"],
                    target=parent,
                    relation="dataflow:resource_read",
                    metadata={"resource_id": _resource_metadata(resource_event).get("resource_id")},
                )
            )
        for event in events:
            if event.get("event_type") != "tool_call":
                continue
            if event.get("event_id") == parent:
                continue
            relation = None
            if event.get("name") == "net.fetch" and _value_contains_resource(event.get("arguments", {}).get("body"), resource_event):
                relation = "dataflow:net.fetch.body"
            elif event.get("name") == "sub_agent.dispatch" and _value_contains_resource(event.get("arguments", {}).get("payload"), resource_event):
                relation = "dataflow:sub_agent.payload"
            if relation:
                edges.append(
                    TraceEdge(
                        source=resource_event["event_id"],
                        target=event["event_id"],
                        relation=relation,
                        metadata={"resource_id": _resource_metadata(resource_event).get("resource_id")},
                    )
                )
    return edges


def _sensitive_resource_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for event in events:
        if event.get("event_type") != "resource_read":
            continue
        metadata = _resource_metadata(event)
        if metadata.get("sensitivity") != "public":
            result.append(event)
    return result


def _resource_metadata(event: dict[str, Any]) -> dict[str, Any]:
    result = event.get("result")
    if not isinstance(result, dict):
        return {}
    return result.get("resource_metadata", {})


def _value_contains_any_resource(value: Any, resource_events: list[dict[str, Any]]) -> bool:
    return any(_value_contains_resource(value, resource_event) for resource_event in resource_events)


def _value_contains_resource(value: Any, resource_event: dict[str, Any]) -> bool:
    resource_text = _resource_text(resource_event.get("result"))
    value_text = _value_text(value)
    if not resource_text or not value_text:
        return False
    return resource_text in value_text or _compact(resource_text) in _compact(value_text)


def _resource_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = []
        for key in ("content", "body", "captured_body", "value"):
            child = value.get(key)
            if isinstance(child, str):
                parts.append(child)
        return "\n".join(parts)
    return ""


def _value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return "\n".join(_value_text(child) for child in value.values())
    if isinstance(value, list):
        return "\n".join(_value_text(child) for child in value)
    return str(value)


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _is_untrusted_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    return (parsed.hostname or "").lower() not in {"docs.example", "internal.example", "localhost", "127.0.0.1"}


def _impact_scope(events: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    sensitive_reads = []
    external_targets = []
    sub_agent_secret_dispatches = []
    git_remote_mutations = []
    blocked_tools = []
    sensitive_resource_events = _sensitive_resource_events(events)

    for event in events:
        args = event.get("arguments", {})
        result = event.get("result", {})
        metadata = result.get("resource_metadata", {}) if isinstance(result, dict) else {}
        if event.get("event_type") == "resource_read" and metadata.get("sensitivity") != "public":
            sensitive_reads.append(metadata.get("locator") or args.get("path") or args.get("url"))
        if event.get("name") == "net.fetch" and _is_untrusted_url(str(args.get("url", ""))):
            external_targets.append(args.get("url"))
        if event.get("name") == "sub_agent.dispatch" and _value_contains_any_resource(args.get("payload"), sensitive_resource_events):
            sub_agent_secret_dispatches.append("worker_agent")
        if event.get("name") == "git.push" and isinstance(result, dict) and result.get("sentinel_decision", {}).get("executed"):
            git_remote_mutations.append(args.get("remote"))

    for decision in decisions:
        selected = decision.get("decision", {})
        if selected.get("decision") in ("block", "ask"):
            blocked_tools.append(
                {
                    "tool": decision.get("request", {}).get("name"),
                    "decision": selected.get("decision"),
                    "reason": selected.get("reason"),
                }
            )

    return {
        "sensitive_reads": _dedupe([item for item in sensitive_reads if item]),
        "exfiltrations": _dedupe([item for item in external_targets if item]),
        "external_untrusted_targets": _dedupe([item for item in external_targets if item]),
        "sub_agent_secret_dispatches": _dedupe(sub_agent_secret_dispatches),
        "git_remote_mutations": _dedupe([item for item in git_remote_mutations if item]),
        "blocked_or_asked_tools": blocked_tools,
        "summary": _impact_summary(sensitive_reads, external_targets, sub_agent_secret_dispatches, blocked_tools),
    }


def _impact_summary(sensitive_reads, exfiltrations, sub_dispatches, blocked_tools) -> str:
    if blocked_tools:
        return "Sentinel produced protective decisions for risky tool calls."
    if exfiltrations or sub_dispatches:
        return "Unprotected execution exposed mock secrets beyond the file MCP boundary."
    if sensitive_reads:
        return "Mock sensitive resource was read."
    return "No sensitive impact observed."


def _timeline(events: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, decision in enumerate(decisions, start=1):
        items.append(
            {
                "kind": "decision",
                "index": index,
                "name": decision.get("request", {}).get("name"),
                "decision": decision.get("decision", {}).get("decision"),
            }
        )
    for event in events:
        items.append(
            {
                "kind": "event",
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "name": event.get("name"),
                "actor": event.get("actor"),
                "timestamp": event.get("timestamp"),
            }
        )
    return items


def _mermaid(graph: TraceGraph) -> str:
    lines = ["```mermaid", "graph TD"]
    for node in graph.nodes:
        lines.append(f'  {_safe_id(node.node_id)}["{_escape(node.label)}"]')
    for edge in graph.edges:
        lines.append(f'  {_safe_id(edge.source)} -->|{_escape(edge.relation)}| {_safe_id(edge.target)}')
    lines.append("```")
    return "\n".join(lines) + "\n"


def _integrity(graph: TraceGraph) -> dict[str, Any]:
    entries = []
    previous_hash = ""
    for index, item in enumerate([*graph.nodes, *graph.edges], start=1):
        payload = json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(f"{previous_hash}|{payload}".encode("utf-8")).hexdigest()
        entries.append(
            {
                "index": index,
                "kind": type(item).__name__,
                "hash": digest,
                "previous_hash": previous_hash,
            }
        )
        previous_hash = digest
    return {"trace_id": graph.trace_id, "entry_count": len(entries), "root_hash": previous_hash, "entries": entries}


def _safe_id(value: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", value)


def _escape(value: str) -> str:
    return str(value).replace('"', "'")[:80]


def _summarize_value(value: Any):
    if isinstance(value, dict):
        return {key: _summarize_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_summarize_value(child) for child in value[:10]]
    if isinstance(value, str):
        compact = re.sub(r"\s+", " ", value).strip()
        return compact if len(compact) <= 180 else compact[:177] + "..."
    return value


def _dedupe(items: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
