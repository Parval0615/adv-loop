from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


InjectionSourceType = Literal["direct", "indirect", "memory"]
InjectionSourceKind = Literal[
    "user_task",
    "network_document",
    "workspace_document",
    "issue_ticket_email",
    "ide_source",
    "mcp_tool_result",
    "tool_registration",
    "memory_store",
    "tool_argument",
]
InjectionPattern = Literal[
    "role_spoofing",
    "instruction_override",
    "context_hijack",
    "tool_result_injection",
    "hidden_trigger",
    "data_exfiltration_intent",
]


@dataclass(frozen=True)
class InjectionFinding:
    finding_id: str
    source_type: InjectionSourceType
    source_channel: str
    pattern: InjectionPattern
    field_path: str
    span_start: int
    span_end: int
    confidence: float
    evidence: str
    normalized_text: str
    evasion_tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source_kind: str = ""
    original_span: dict = field(default_factory=dict)
    normalized_span: dict = field(default_factory=dict)
    evidence_ref: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
