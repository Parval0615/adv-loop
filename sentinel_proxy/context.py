from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SentinelContext:
    task: str
    scenario_id: str
    trace_id: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    normalizations: list[dict[str, Any]] = field(default_factory=list)
    injection_findings: list[dict[str, Any]] = field(default_factory=list)
    intent_verdicts: list[dict[str, Any]] = field(default_factory=list)
    policy_decisions: list[dict[str, Any]] = field(default_factory=list)
    trace_refs: list[dict[str, Any]] = field(default_factory=list)
    resource_reads: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    sub_dispatches: list[dict[str, Any]] = field(default_factory=list)
    source_documents: list[dict[str, Any]] = field(default_factory=list)
    tool_registry: list[dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def record_tool_call(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        result: Any,
        decision: dict[str, Any],
        executed: bool,
        intercept_id: str | None = None,
    ) -> None:
        self.tool_calls.append(
            {
                "intercept_id": intercept_id,
                "name": name,
                "arguments": deepcopy(arguments),
                "result": deepcopy(result),
                "decision": deepcopy(decision),
                "executed": executed,
            }
        )

    def record_normalization(self, normalized_field: dict[str, Any]) -> None:
        self.normalizations.append(deepcopy(normalized_field))

    def record_injection_finding(self, finding: dict[str, Any]) -> None:
        finding_id = finding.get("finding_id")
        if finding_id and any(item.get("finding_id") == finding_id for item in self.injection_findings):
            return
        self.injection_findings.append(deepcopy(finding))

    def record_intent_verdict(self, verdict: dict[str, Any]) -> None:
        verdict_id = verdict.get("verdict_id")
        if verdict_id and any(item.get("verdict_id") == verdict_id for item in self.intent_verdicts):
            return
        self.intent_verdicts.append(deepcopy(verdict))

    def record_policy_decision(self, decision: dict[str, Any]) -> None:
        self.policy_decisions.append(deepcopy(decision))

    def record_trace_ref(self, trace_ref: dict[str, Any]) -> None:
        self.trace_refs.append(deepcopy(trace_ref))

    def record_resource_read(
        self,
        *,
        source: str,
        arguments: dict[str, Any],
        result: Any,
        source_event_id: str | None = None,
        intercept_id: str | None = None,
    ) -> dict[str, Any]:
        metadata = _resource_metadata(
            source=source,
            arguments=arguments,
            result=result,
            source_event_id=source_event_id,
            intercept_id=intercept_id,
            index=len(self.resource_reads) + 1,
        )
        self.resource_reads.append(
            {
                **metadata,
                "source": source,
                "arguments": deepcopy(arguments),
                "result": deepcopy(result),
            }
        )
        return metadata

    def record_sub_dispatch(
        self,
        *,
        task: str,
        payload: dict[str, Any],
        result: Any,
        source_event_id: str | None = None,
        intercept_id: str | None = None,
    ) -> None:
        self.sub_dispatches.append(
            {
                "source_event_id": source_event_id,
                "intercept_id": intercept_id,
                "task": task,
                "payload_summary": _summarize_payload(payload),
                "result": deepcopy(result),
            }
        )


def _summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            summary[key] = {
                "type": "str",
                "length": len(value),
                "preview": value[:32],
            }
        else:
            summary[key] = {"type": type(value).__name__, "value": deepcopy(value)}
    return summary


def _resource_metadata(
    *,
    source: str,
    arguments: dict[str, Any],
    result: Any,
    source_event_id: str | None,
    intercept_id: str | None,
    index: int,
) -> dict[str, Any]:
    text = _resource_text(result)
    locator = str(arguments.get("path") or arguments.get("url") or source)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
    resource_id = f"res-{hashlib.sha1(f'{source}|{locator}|{index}|{digest}'.encode('utf-8')).hexdigest()[:12]}"
    return {
        "resource_id": resource_id,
        "source_event_id": source_event_id,
        "intercept_id": intercept_id,
        "locator": locator,
        "sensitivity": _sensitivity(locator, text),
        "content_hash": digest,
        "preview": _preview(text),
    }


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


def _sensitivity(locator: str, text: str) -> str:
    lowered = f"{locator}\n{text}".lower()
    if any(token in lowered for token in (".ssh", "id_rsa", "mock_private_key", "private key", "credential", "api key", "token")):
        return "secret"
    return "public"


def _preview(text: str, limit: int = 96) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
