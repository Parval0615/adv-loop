from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

AttackRiskType = Literal["memory_poisoning", "tool_tampering", "goal_perturbation"]
AttackIntensity = Literal["light", "medium", "heavy"]
AgentFramework = Literal["direct_api", "langgraph", "autogen"]


class AttackSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attack_id: str = Field(min_length=1)
    risk_type: AttackRiskType
    strategy: str = Field(min_length=1)
    intensity: AttackIntensity
    target: str = Field(min_length=1)
    label: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    success_criteria: list[str] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioPairRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pair_id: str = Field(min_length=1)
    attack_spec_id: str = Field(min_length=1)
    risk_type: AttackRiskType
    clean_scenario: str = Field(min_length=1)
    controlled_scenario: str = Field(min_length=1)
    seed: int
    framework: AgentFramework
    controlled_label: str = Field(min_length=1)


class ScenarioManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["attack-scenarios-v0.1"] = "attack-scenarios-v0.1"
    records: list[ScenarioPairRecord] = Field(min_length=1)


def load_scenario_manifest(path: str | Path) -> ScenarioManifest:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ScenarioManifest.model_validate(data)


__all__ = [
    "AgentFramework",
    "AttackIntensity",
    "AttackRiskType",
    "AttackSpec",
    "ScenarioManifest",
    "ScenarioPairRecord",
    "load_scenario_manifest",
]
