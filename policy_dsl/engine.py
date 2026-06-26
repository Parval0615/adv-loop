from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from policy_dsl.models import PolicyDecision, PolicyMatch, PolicyRule
from sentinel_proxy.context import SentinelContext
from sentinel_proxy.models import InterceptRequest


DEFAULT_RULES_PATH = Path(__file__).with_name("default_rules.json")
DEFAULT_POLICY_RULES: list[dict] = json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf-8"))

SENSITIVE_PATH_PATTERNS = (
    ".ssh/",
    ".ssh\\",
    "~/.ssh",
    ".aws/",
    ".aws\\",
    "~/.aws",
    "/etc/cron.",
    "\\etc\\cron.",
    "autostart",
)
SECRET_HINTS = (
    "mock_private_key",
    "private key",
    "begin openssh private key",
    "id_rsa",
    "api_key",
    "api key",
    "credential",
    "password",
    "secret",
    "token",
)
TRUSTED_HOSTS = {"docs.example", "internal.example", "localhost", "127.0.0.1"}


class PolicyEngine:
    def __init__(self, rules: list[dict] | None = None) -> None:
        self.rules = [_rule_from_dict(item) for item in (rules or DEFAULT_POLICY_RULES)]

    def evaluate(self, request: InterceptRequest, context: SentinelContext) -> PolicyDecision:
        for rule in self.rules:
            if rule.tool != request.name:
                continue
            matches = _evaluate_rule(rule, request, context)
            if matches:
                return PolicyDecision(
                    decision=rule.decision,
                    rule_id=rule.rule_id,
                    risk_level=rule.risk_level,
                    reason=rule.reason,
                    matches=matches,
                    metadata={"rule": rule.to_dict()},
                )
        return PolicyDecision(
            decision="allow",
            rule_id="default-allow",
            risk_level="none",
            reason="No policy rule matched.",
        )


def _rule_from_dict(item: dict) -> PolicyRule:
    return PolicyRule(
        rule_id=item["rule_id"],
        tool=item["tool"],
        decision=item["decision"],
        risk_level=item["risk_level"],
        reason=item["reason"],
        conditions=list(item.get("conditions", [])),
    )


def _evaluate_rule(rule: PolicyRule, request: InterceptRequest, context: SentinelContext) -> list[PolicyMatch]:
    matches: list[PolicyMatch] = []
    for condition in rule.conditions:
        condition_type = condition.get("type")
        match = None
        if condition_type == "path_matches_sensitive":
            value = str(request.arguments.get(condition.get("field", "path"), ""))
            if _path_matches_sensitive(value):
                match = _match(rule, condition_type, f"arguments.{condition.get('field', 'path')}", value)
        elif condition_type == "body_contains_sensitive_resource_to_untrusted_domain":
            url = str(request.arguments.get(condition.get("url_field", "url"), ""))
            body = request.arguments.get(condition.get("body_field", "body"))
            resource_match = _sensitive_resource_match(context, body)
            if _is_untrusted_url(url) and resource_match:
                match = _match(rule, condition_type, "arguments.body", resource_match)
        elif condition_type == "command_dangerous":
            command = request.arguments.get(condition.get("field", "command"), "")
            if _command_is_dangerous(command):
                match = _match(rule, condition_type, "arguments.command", _command_text(command))
        elif condition_type == "task_contains_code_review":
            if _task_is_code_review(context.task):
                match = _match(rule, condition_type, "context.task", context.task)
        elif condition_type == "payload_contains_sensitive_resource":
            payload = request.arguments.get(condition.get("field", "payload"), {})
            resource_match = _sensitive_resource_match(context, payload)
            if resource_match:
                match = _match(rule, condition_type, "arguments.payload", resource_match)
        if match:
            matches.append(match)
    return matches


def _match(rule: PolicyRule, condition: str, field_path: str, value: str) -> PolicyMatch:
    compact = re.sub(r"\s+", " ", value).strip()
    return PolicyMatch(
        rule_id=rule.rule_id,
        condition=condition,
        field_path=field_path,
        value_preview=compact[:160],
    )


def _path_matches_sensitive(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return any(pattern.replace("\\", "/") in normalized for pattern in SENSITIVE_PATH_PATTERNS)


def _is_untrusted_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    return (parsed.hostname or "").lower() not in TRUSTED_HOSTS


def _contains_secret(value) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return any(_contains_secret(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_secret(child) for child in value)
    lowered = str(value).lower()
    return any(hint in lowered for hint in SECRET_HINTS)


def _sensitive_resource_match(context: SentinelContext, value) -> str | None:
    text = _value_text(value)
    if not text:
        return None
    for read in context.resource_reads:
        if read.get("sensitivity") == "public":
            continue
        resource_text = _resource_text(read.get("result"))
        if not resource_text:
            continue
        if resource_text in text or _compact(resource_text) in _compact(text):
            return f"{read.get('resource_id')}:{read.get('locator')}"
        if len(text.strip()) >= 12 and text.strip() in resource_text:
            return f"{read.get('resource_id')}:{read.get('locator')}"
        preview = read.get("preview")
        if isinstance(preview, str) and len(preview) >= 24 and preview in text:
            return f"{read.get('resource_id')}:{read.get('locator')}"
    return None


def _value_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return "\n".join(_value_text(child) for child in value.values())
    if isinstance(value, list):
        return "\n".join(_value_text(child) for child in value)
    return str(value)


def _resource_text(value) -> str:
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


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _command_is_dangerous(command) -> bool:
    text = _command_text(command).lower()
    decode_execute = "base64" in text and any(token in text for token in (" -d", "--decode", "frombase64string")) and any(
        token in text for token in (" sh", " bash", "powershell", "python", "iex", "invoke-expression")
    )
    download_pipe = bool(re.search(r"\b(curl|wget|irm|iwr)\b.+\|.+\b(sh|bash|python|powershell|iex)\b", text))
    return decode_execute or download_pipe


def _command_text(command) -> str:
    if isinstance(command, list):
        return " ".join(str(part) for part in command)
    return str(command)


def _task_is_code_review(task: str) -> bool:
    lowered = task.lower()
    return "code review" in lowered or "review code" in lowered or "代码审查" in lowered
