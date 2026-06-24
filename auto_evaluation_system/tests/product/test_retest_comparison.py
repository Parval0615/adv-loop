from pathlib import Path

from auto_evaluation_system.product_api.comparison import (
    build_retest_comparison,
    render_markdown_comparison,
    write_comparison_artifacts,
)
from auto_evaluation_system.product_api.contracts import (
    AgentSecurityReport,
    Finding,
    ReportArtifacts,
    ScenarioResult,
)
from auto_evaluation_system.product_api.reports import write_report_artifacts
from auto_evaluation_system.product_api.service import ProductEvaluationService


def test_retest_comparison_tracks_finding_and_scenario_delta() -> None:
    before = _report(
        score=60,
        risk="high",
        findings=[
            _finding("finding-a", "scenario-a", "high"),
            _finding("finding-b", "scenario-b", "medium"),
        ],
        scenarios=[
            _scenario("scenario-a", passed=False, decision="allow"),
            _scenario("scenario-b", passed=False, decision="allow"),
        ],
    )
    after = _report(
        score=85,
        risk="medium",
        findings=[
            _finding("finding-b", "scenario-b", "medium"),
            _finding("finding-c", "scenario-c", "low"),
        ],
        scenarios=[
            _scenario("scenario-a", passed=True, decision="block"),
            _scenario("scenario-b", passed=False, decision="allow"),
            _scenario("scenario-c", passed=False, decision="allow"),
        ],
    )

    comparison = build_retest_comparison(before, after)

    assert comparison.schema_version == "agent-security-comparison-v0.1"
    assert comparison.score_delta == 25
    assert comparison.risk_level_change == "high -> medium"
    assert [item.finding_id for item in comparison.resolved_findings] == ["finding-a"]
    assert [item.finding_id for item in comparison.new_findings] == ["finding-c"]
    assert [item.finding_id for item in comparison.persisted_findings] == ["finding-b"]
    statuses = {item.scenario_id: item.status for item in comparison.scenario_deltas}
    assert statuses["scenario-a"] == "improved"
    assert statuses["scenario-b"] == "unchanged_fail"
    assert statuses["scenario-c"] == "unchanged_fail"


def test_retest_comparison_writes_json_and_markdown(tmp_path: Path) -> None:
    comparison = build_retest_comparison(_report(), _report(score=100))

    write_comparison_artifacts(
        comparison,
        tmp_path / "agent-security-comparison-v0.1.json",
        tmp_path / "agent-security-comparison-v0.1.md",
    )
    markdown = render_markdown_comparison(comparison)

    assert (tmp_path / "agent-security-comparison-v0.1.json").exists()
    assert (tmp_path / "agent-security-comparison-v0.1.md").exists()
    assert "Agent Security Retest Comparison" in markdown
    assert "Score delta" in markdown


def test_product_service_compares_persisted_reports(tmp_path: Path) -> None:
    service = ProductEvaluationService(storage_root=tmp_path)
    before = _report(report_path=str(tmp_path / "private_tenant" / "evaluations" / "eval_before" / "agent-security-report-v0.1.json"))
    after = _report(
        score=100,
        risk="low",
        report_path=str(tmp_path / "private_tenant" / "evaluations" / "eval_after" / "agent-security-report-v0.1.json"),
    )
    write_report_artifacts(
        before,
        Path(before.artifacts.report_path),
        Path(before.artifacts.report_path).with_suffix(".md"),
    )
    write_report_artifacts(
        after,
        Path(after.artifacts.report_path),
        Path(after.artifacts.report_path).with_suffix(".md"),
    )

    comparison = service.compare_reports("eval_before", "eval_after")

    assert comparison.score_delta == 20
    assert Path(comparison.artifacts.comparison_path).exists()
    assert Path(comparison.artifacts.markdown_path or "").exists()


def _report(
    score: int = 80,
    risk: str = "medium",
    findings: list[Finding] | None = None,
    scenarios: list[ScenarioResult] | None = None,
    report_path: str = "runs/product/report.json",
) -> AgentSecurityReport:
    return AgentSecurityReport(
        tenant_id="private_tenant",
        agent_id="agent_001",
        benchmark="ecommerce-security-v0.1",
        overall_score=score,
        risk_level=risk,
        findings=findings or [],
        scenario_results=scenarios or [_scenario("scenario-a", passed=True, decision="block")],
        artifacts=ReportArtifacts(report_path=report_path),
    )


def _finding(finding_id: str, scenario_id: str, severity: str) -> Finding:
    return Finding(
        finding_id=finding_id,
        scenario_id=scenario_id,
        severity=severity,
        title=f"{scenario_id} finding",
        description="Controlled attack result changed.",
        business_impact="business_risk",
        recommendation="Tune guard policy and retest.",
    )


def _scenario(scenario_id: str, passed: bool, decision: str) -> ScenarioResult:
    return ScenarioResult(
        scenario_id=scenario_id,
        category="business_logic_abuse",
        severity="high",
        expected_decision="block",
        actual_decision=decision,
        clean_decision="allow",
        passed=passed,
        business_impact="business_risk",
        trajectory_ref=f"runs/product/{scenario_id}.json",
    )
