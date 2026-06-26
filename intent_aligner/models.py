from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class TaskIntent:
    intent_id: str
    summary: str
    expected_tools: list[str]
    expected_resources: list[str]
    risk_tolerance: str = "normal"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionPlan:
    tool_sequence: list[str]
    resource_sequence: list[str]
    current_tool: str
    current_arguments: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DeviationFinding:
    finding_id: str
    tool_name: str
    reason: str
    related_resources: list[str] = field(default_factory=list)
    related_injection_findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AlignmentVerdict:
    verdict_id: str
    aligned: bool
    original_intent: TaskIntent
    actual_plan: ExecutionPlan
    deviation_score: float
    deviated_tool_call_ids: list[str]
    attack_type: str
    rationale: str
    deviations: list[DeviationFinding] = field(default_factory=list)
    decision_hint: str = "allow"

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["original_intent"] = self.original_intent.to_dict()
        payload["actual_plan"] = self.actual_plan.to_dict()
        payload["deviations"] = [item.to_dict() for item in self.deviations]
        return payload
