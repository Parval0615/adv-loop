from auto_evaluation_system.product_api.contracts import (
    AgentRegistration,
    AgentSecurityReport,
    EvaluationRequest,
    EvaluationStatus,
    ReportArtifacts,
)


def test_product_contracts_import_and_validate() -> None:
    registration = AgentRegistration(agent_id="agent_001", name="Demo Agent")
    request = EvaluationRequest(agent_id=registration.agent_id)
    status = EvaluationStatus(
        evaluation_id="eval_001",
        tenant_id=request.tenant_id,
        agent_id=request.agent_id,
        status="queued",
    )
    report = AgentSecurityReport(
        tenant_id=request.tenant_id,
        agent_id=request.agent_id,
        benchmark=request.benchmark,
        overall_score=100,
        risk_level="low",
        artifacts=ReportArtifacts(report_path="runs/product/report.json"),
    )

    assert registration.schema_version == "agent-registration-v0.1"
    assert request.benchmark == "ecommerce-security-v0.1"
    assert request.pilot_preset is None
    assert status.status == "queued"
    assert report.schema_version == "agent-security-report-v0.1"
