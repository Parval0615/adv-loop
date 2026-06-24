from pathlib import Path

import yaml


def test_product_openapi_contract_covers_hosted_api_surface() -> None:
    spec = yaml.safe_load(Path("docs/api/openapi.yaml").read_text(encoding="utf-8"))

    assert spec["openapi"] == "3.1.0"
    assert {
        "/v1/agents",
        "/v1/agents/{agent_id}/sessions",
        "/v1/evaluations",
        "/v1/evaluations/{evaluation_id}",
        "/v1/reports/{report_id}",
        "/v1/comparisons",
        "/v1/trajectories",
    } <= set(spec["paths"])

    schemas = spec["components"]["schemas"]
    assert {
        "AgentRegistration",
        "EvaluationRequest",
        "EvaluationStatus",
        "AgentSecurityReport",
        "AgentSecurityComparisonReport",
    } <= set(schemas)
    assert "pilot_preset" in schemas["EvaluationRequest"]["properties"]
    assert "dashboard_path" in schemas["ReportArtifacts"]["properties"]
    assert "audit_refs" in schemas["ReportArtifacts"]["properties"]
