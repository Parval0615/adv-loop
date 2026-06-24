from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["low", "medium", "high", "critical"]
EvaluationMode = Literal["sdk", "hosted_api", "offline_trace"]
EvaluationState = Literal["queued", "running", "completed", "failed"]
FindingComparisonStatus = Literal["resolved", "new", "persisted"]
ScenarioComparisonStatus = Literal["improved", "regressed", "unchanged_pass", "unchanged_fail"]


class ToolSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    risk_level: str = Field(min_length=1)
    description: str = Field(min_length=1)


class AgentRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["agent-registration-v0.1"] = "agent-registration-v0.1"
    tenant_id: str = Field(default="private_tenant", min_length=1)
    agent_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    framework: str = Field(default="sdk", min_length=1)
    adapter_type: Literal["ecommerce_demo", "external_sdk", "http_endpoint"] = "ecommerce_demo"
    endpoint_url: str | None = None
    tool_specs: list[ToolSpecModel] = Field(default_factory=list)
    data_boundary: dict[str, Any] = Field(default_factory=dict)


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="private_tenant", min_length=1)
    agent_id: str = Field(min_length=1)
    benchmark: str = Field(default="ecommerce-security-v0.1", min_length=1)
    mode: EvaluationMode = "sdk"
    pilot_preset: str | None = None
    attack_intensity: Literal["light", "medium", "heavy"] = "medium"
    scenarios: list[str] = Field(default_factory=list)
    policy: dict[str, Any] = Field(default_factory=lambda: {
        "no_real_payment": True,
        "no_external_attack": True,
        "single_tenant": True,
    })


class EvaluationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    status: EvaluationState
    report_id: str | None = None
    report_path: str | None = None
    error: str | None = None


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    severity: RiskLevel
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    business_impact: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class ScenarioResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: RiskLevel
    expected_decision: Literal["allow", "block"]
    actual_decision: Literal["allow", "block"]
    clean_decision: Literal["allow", "block"]
    passed: bool
    business_impact: str = Field(min_length=1)
    trajectory_ref: str = Field(min_length=1)


class ReportArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trajectory_refs: list[str] = Field(default_factory=list)
    audit_refs: list[str] = Field(default_factory=list)
    report_path: str = Field(min_length=1)
    markdown_path: str | None = None
    dashboard_path: str | None = None


class AgentSecurityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["agent-security-report-v0.1"] = "agent-security-report-v0.1"
    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    benchmark: str = Field(min_length=1)
    overall_score: int = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high", "critical"]
    summary: dict[str, Any] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    scenario_results: list[ScenarioResult] = Field(default_factory=list)
    guard_effectiveness: dict[str, Any] = Field(default_factory=dict)
    false_positive_rate: float = Field(default=0.0, ge=0)
    attack_success_rate: float = Field(default=0.0, ge=0)
    business_impact: dict[str, Any] = Field(default_factory=dict)
    artifacts: ReportArtifacts


class ComparisonFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    severity: RiskLevel
    title: str = Field(min_length=1)
    status: FindingComparisonStatus
    recommendation: str = Field(min_length=1)


class ComparisonScenarioDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    before_passed: bool | None = None
    after_passed: bool | None = None
    before_decision: str | None = None
    after_decision: str | None = None
    status: ScenarioComparisonStatus


class ComparisonArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before_report_path: str = Field(min_length=1)
    after_report_path: str = Field(min_length=1)
    comparison_path: str = Field(min_length=1)
    markdown_path: str | None = None


class AgentSecurityComparisonReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["agent-security-comparison-v0.1"] = "agent-security-comparison-v0.1"
    comparison_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    benchmark: str = Field(min_length=1)
    before_score: int = Field(ge=0, le=100)
    after_score: int = Field(ge=0, le=100)
    score_delta: int
    before_risk_level: RiskLevel
    after_risk_level: RiskLevel
    risk_level_change: str = Field(min_length=1)
    resolved_findings: list[ComparisonFinding] = Field(default_factory=list)
    new_findings: list[ComparisonFinding] = Field(default_factory=list)
    persisted_findings: list[ComparisonFinding] = Field(default_factory=list)
    scenario_deltas: list[ComparisonScenarioDelta] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    artifacts: ComparisonArtifacts
