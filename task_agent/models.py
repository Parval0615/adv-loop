from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TaskSpec:
    raw_instruction: str
    goal: str
    subgoals: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    entities: dict[str, Any] = field(default_factory=dict)
    parse_mode: str = "llm"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlanStep:
    step_id: str
    candidate_tool: str
    args_hint: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Plan:
    steps: list[PlanStep] = field(default_factory=list)
    revision: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Observation:
    answer: str = ""
    blocked: bool = False
    risk_level: str = "normal"
    value: Any = None
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskStep:
    plan_step_id: str
    thought: str
    action_tool: str
    action_args: dict[str, Any]
    decision_reason: str
    observation: Observation
    replan_triggered: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskRunResult:
    task_spec: TaskSpec
    plans: list[Plan]
    trace: list[TaskStep]
    final_answer: str
    goal_achieved: bool
    replan_count: int
    llm_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
