from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from sentinel_proxy.models import DecisionValue


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    tool: str
    decision: DecisionValue
    risk_level: Literal["none", "low", "medium", "high", "critical"]
    reason: str
    conditions: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PolicyMatch:
    rule_id: str
    condition: str
    field_path: str
    value_preview: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PolicyDecision:
    decision: DecisionValue
    rule_id: str
    risk_level: str
    reason: str
    matches: list[PolicyMatch] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["matches"] = [match.to_dict() for match in self.matches]
        return payload
