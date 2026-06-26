from __future__ import annotations

import hashlib
import re
from typing import Any

from evasion_shield import normalize_text
from injection_radar.models import InjectionFinding, InjectionPattern, InjectionSourceKind, InjectionSourceType
from sentinel_proxy.context import SentinelContext
from sentinel_proxy.models import InterceptRequest


PATTERN_RULES: tuple[tuple[InjectionPattern, re.Pattern[str], float], ...] = (
    (
        "instruction_override",
        re.compile(r"\b(ignore|disregard|override|bypass|forget)\b.{0,80}\b(previous|prior|system|instructions?|rules?)\b|忽略.{0,20}(之前|系统|指令)", re.I),
        0.92,
    ),
    (
        "role_spoofing",
        re.compile(r"\b(you are now|act as|pretend to be|switch to)\b.{0,80}\b(admin|root|developer|system|jailbroken|free mode)\b|管理员模式|自由模式", re.I),
        0.86,
    ),
    (
        "context_hijack",
        re.compile(r"\b(end of system prompt|new prompt|system prompt ends|ignore the above|new instructions?)\b|系统提示|新的指令", re.I),
        0.84,
    ),
    (
        "tool_result_injection",
        re.compile(r"\b(tool result|mcp response|document says|web page says)\b.{0,120}\b(ignore|override|follow these instructions?)\b", re.I),
        0.82,
    ),
    (
        "hidden_trigger",
        re.compile(r"\b(when|if)\b.{0,80}\b(user says|trigger|keyword|next time)\b.{0,120}\b(ignore|admin|secret|exfiltrate)\b|隐藏触发|触发词", re.I),
        0.8,
    ),
    (
        "data_exfiltration_intent",
        re.compile(r"\b(send|post|upload|exfiltrate|leak|collect)\b.{0,100}\b(secret|credential|token|private key|id_rsa|api key)\b|外发|泄露", re.I),
        0.9,
    ),
)

SENSITIVE_RESULT_HINTS = ("private key", "mock_private_key", "id_rsa", "credential", "token", "secret")


def detect_injections(
    text: str,
    *,
    source_type: InjectionSourceType,
    source_channel: str,
    source_kind: InjectionSourceKind | str | None = None,
    field_path: str,
    evasion_tags: list[str] | None = None,
    evidence_ref: str | None = None,
) -> list[InjectionFinding]:
    normalized = normalize_text(text)
    normalized_text = normalized.normalized_text
    tags = _dedupe([*(evasion_tags or []), *normalized.evasion_tags])
    findings: list[InjectionFinding] = []

    for pattern, regex, confidence in PATTERN_RULES:
        for match in regex.finditer(normalized_text):
            findings.append(
                _build_finding(
                    source_type=source_type,
                    source_channel=source_channel,
                    source_kind=source_kind or _source_kind(source_type, source_channel),
                    pattern=pattern,
                    field_path=field_path,
                    span_start=match.start(),
                    span_end=match.end(),
                    confidence=confidence,
                    evidence=match.group(0),
                    normalized_text=normalized_text,
                    evasion_tags=tags,
                    evidence_ref=evidence_ref or field_path,
                )
            )

    if tags and _has_instruction_signal(normalized_text):
        findings.append(
            _build_finding(
                source_type=source_type,
                source_channel=source_channel,
                source_kind=source_kind or _source_kind(source_type, source_channel),
                pattern="instruction_override",
                field_path=field_path,
                span_start=0,
                span_end=min(len(normalized_text), 120),
                confidence=0.76,
                evidence=normalized_text[:120],
                normalized_text=normalized_text,
                evasion_tags=tags,
                evidence_ref=evidence_ref or field_path,
            )
        )

    return _dedupe_findings(findings)


def scan_request(request: InterceptRequest, context: SentinelContext) -> list[InjectionFinding]:
    findings: list[InjectionFinding] = []

    findings.extend(
        detect_injections(
            context.task,
            source_type="direct",
            source_channel="user_task",
            source_kind="user_task",
            field_path="context.task",
            evidence_ref="context.task",
        )
    )
    for index, item in enumerate(context.history):
        content = item.get("content")
        if not isinstance(content, str):
            continue
        source_type: InjectionSourceType = "memory" if item.get("role") == "memory" else "direct"
        source_kind = "memory_store" if source_type == "memory" else "user_task"
        findings.extend(
            detect_injections(
                content,
                source_type=source_type,
                source_channel=f"history.{item.get('role', 'unknown')}",
                source_kind=source_kind,
                field_path=f"context.history[{index}].content",
                evidence_ref=f"context.history[{index}]",
            )
        )

    for index, document in enumerate(context.source_documents):
        content = document.get("content")
        if not isinstance(content, str):
            continue
        source_kind = str(document.get("source_kind", "workspace_document"))
        findings.extend(
            detect_injections(
                content,
                source_type="memory" if source_kind == "memory_store" else "indirect",
                source_channel=str(document.get("source_channel", source_kind)),
                source_kind=source_kind,
                field_path=f"context.source_documents[{index}].content",
                evidence_ref=str(document.get("evidence_ref", f"context.source_documents[{index}]")),
            )
        )

    for index, tool in enumerate(context.tool_registry):
        content = tool.get("description")
        if not isinstance(content, str):
            continue
        findings.extend(
            detect_injections(
                content,
                source_type="indirect",
                source_channel=str(tool.get("name", "tool_registry")),
                source_kind="tool_registration",
                field_path=f"context.tool_registry[{index}].description",
                evidence_ref=str(tool.get("evidence_ref", f"context.tool_registry[{index}]")),
            )
        )

    for field_path, value in _iter_text_fields(request.arguments, "request.arguments"):
        findings.extend(
            detect_injections(
                value,
                source_type="direct",
                source_channel=f"tool_argument:{request.name}",
                source_kind="tool_argument",
                field_path=field_path,
                evasion_tags=_tags_for_field(context, field_path),
                evidence_ref=field_path,
            )
        )

    for index, read in enumerate(context.resource_reads):
        text = _resource_text(read.get("result"))
        if text:
            findings.extend(
                detect_injections(
                    text,
                    source_type="indirect",
                    source_channel=str(read.get("source", "resource")),
                    source_kind=_resource_source_kind(read),
                    field_path=f"context.resource_reads[{index}].result",
                    evidence_ref=str(read.get("resource_id", f"context.resource_reads[{index}]")),
                )
            )

    for index, call in enumerate(context.tool_calls):
        result_text = _resource_text(call.get("result"))
        if result_text and _looks_like_sensitive_tool_result(result_text):
            findings.extend(
                detect_injections(
                    result_text,
                    source_type="indirect",
                    source_channel=f"tool_result:{call.get('name')}",
                    source_kind="mcp_tool_result",
                    field_path=f"context.tool_calls[{index}].result",
                    evidence_ref=str(call.get("intercept_id", f"context.tool_calls[{index}]")),
                )
            )

    return _dedupe_findings(findings)


def _build_finding(
    *,
    source_type: InjectionSourceType,
    source_channel: str,
    source_kind: str,
    pattern: InjectionPattern,
    field_path: str,
    span_start: int,
    span_end: int,
    confidence: float,
    evidence: str,
    normalized_text: str,
    evasion_tags: list[str],
    evidence_ref: str,
) -> InjectionFinding:
    preview = _preview(evidence)
    identity = "|".join([source_type, source_channel, pattern, field_path, str(span_start), preview])
    finding_id = f"inj-{hashlib.sha1(identity.encode('utf-8')).hexdigest()[:12]}"
    return InjectionFinding(
        finding_id=finding_id,
        source_type=source_type,
        source_channel=source_channel,
        pattern=pattern,
        field_path=field_path,
        span_start=span_start,
        span_end=span_end,
        confidence=confidence,
        evidence=preview,
        normalized_text=_preview(normalized_text, limit=240),
        evasion_tags=evasion_tags,
        metadata={"anchor": {"start": span_start, "end": span_end}},
        source_kind=source_kind,
        original_span={"start": span_start, "end": span_end},
        normalized_span={"start": span_start, "end": span_end},
        evidence_ref=evidence_ref,
    )


def _iter_text_fields(value: Any, prefix: str):
    if isinstance(value, str):
        yield prefix, value
        return
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_text_fields(child, f"{prefix}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_text_fields(child, f"{prefix}[{index}]")


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


def _tags_for_field(context: SentinelContext, field_path: str) -> list[str]:
    tags: list[str] = []
    for item in context.normalizations:
        if item.get("field_path") == field_path:
            result = item.get("result", {})
            tags.extend(result.get("evasion_tags", []))
    return _dedupe(tags)


def _source_kind(source_type: InjectionSourceType, source_channel: str) -> str:
    if source_type == "memory":
        return "memory_store"
    if source_channel == "network_mcp":
        return "network_document"
    if source_channel == "file_mcp":
        return "workspace_document"
    if source_channel.startswith("tool_result:"):
        return "mcp_tool_result"
    if source_channel.startswith("tool_argument:"):
        return "tool_argument"
    return "user_task" if source_type == "direct" else "workspace_document"


def _resource_source_kind(read: dict[str, Any]) -> str:
    if read.get("source") == "network_mcp":
        return "network_document"
    if read.get("source") == "file_mcp":
        return "workspace_document"
    return "mcp_tool_result"


def _has_instruction_signal(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("ignore", "instruction", "system prompt", "jailbreak", "free mode", "admin"))


def _looks_like_sensitive_tool_result(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in SENSITIVE_RESULT_HINTS)


def _dedupe(items: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _dedupe_findings(findings: list[InjectionFinding]) -> list[InjectionFinding]:
    result: list[InjectionFinding] = []
    seen = set()
    for finding in findings:
        if finding.finding_id in seen:
            continue
        seen.add(finding.finding_id)
        result.append(finding)
    return result


def _preview(text: str, *, limit: int = 160) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
