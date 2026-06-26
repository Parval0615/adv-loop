from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ProxyMode = Literal["observe", "enforce"]
DecisionValue = Literal["allow", "ask", "block"]
InterceptEventType = Literal["tool_call", "resource_read", "sub_dispatch"]


@dataclass(frozen=True)
class InterceptRequest:
    event_type: InterceptEventType
    actor: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    intercept_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InterceptDecision:
    decision: DecisionValue
    stage: str
    reason: str
    risk_level: str = "none"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InterceptResult:
    executed: bool
    decision: InterceptDecision
    response: Any
    intercept_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intercept_id": self.intercept_id,
            "executed": self.executed,
            "decision": self.decision.to_dict(),
            "response": self.response,
        }
