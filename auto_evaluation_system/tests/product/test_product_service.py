from pathlib import Path

import pytest

from auto_evaluation_system.product_api.contracts import AgentRegistration, EvaluationRequest
from auto_evaluation_system.product_api.service import ProductEvaluationService


def test_product_service_registers_runs_and_reports(tmp_path: Path) -> None:
    service = ProductEvaluationService(storage_root=tmp_path)
    registration = service.register_agent(
        AgentRegistration(agent_id="ecommerce_customer_guide", name="E-commerce Guide")
    )
    session = service.create_session(registration.tenant_id, registration.agent_id)
    status = service.run_evaluation(
        EvaluationRequest(tenant_id=registration.tenant_id, agent_id=registration.agent_id)
    )
    loaded_status = service.get_evaluation(status.evaluation_id)
    report = service.get_report(status.report_id or status.evaluation_id)

    assert session["agent_id"] == registration.agent_id
    assert loaded_status.status == "completed"
    assert status.report_path
    assert report.schema_version == "agent-security-report-v0.1"
    assert report.scenario_results
    assert Path(report.artifacts.report_path).exists()
    assert Path(report.artifacts.markdown_path or "").exists()
    assert report.artifacts.audit_refs
    assert Path(report.artifacts.audit_refs[0]).exists()


def test_product_service_uploads_offline_trace(tmp_path: Path) -> None:
    service = ProductEvaluationService(storage_root=tmp_path)
    registration = service.register_agent(AgentRegistration(agent_id="agent_trace", name="Trace Agent"))
    uploaded = service.upload_trajectory(
        registration.tenant_id,
        registration.agent_id,
        {"turns": [{"message": "hello"}]},
    )

    assert uploaded["trajectory_id"].startswith("trace_")
    assert Path(uploaded["path"]).exists()


def test_product_service_does_not_count_masked_support_input_as_pii_leak(tmp_path: Path) -> None:
    service = ProductEvaluationService(storage_root=tmp_path)
    registration = service.register_agent(
        AgentRegistration(agent_id="ecommerce_customer_guide", name="E-commerce Guide")
    )
    status = service.run_evaluation(
        EvaluationRequest(
            tenant_id=registration.tenant_id,
            agent_id=registration.agent_id,
            scenarios=["support-pii-masking"],
        )
    )
    report = service.get_report(status.report_id or status.evaluation_id)

    assert status.status == "completed"
    assert report.scenario_results[0].passed is True
    assert not report.findings


def test_product_service_rejects_unsafe_artifact_ids(tmp_path: Path) -> None:
    service = ProductEvaluationService(storage_root=tmp_path)

    with pytest.raises(ValueError, match="Unsafe tenant_id"):
        service.register_agent(AgentRegistration(tenant_id="../tenant", agent_id="agent", name="Unsafe"))

    with pytest.raises(ValueError, match="Unsafe report_id"):
        service.get_report("../eval")
