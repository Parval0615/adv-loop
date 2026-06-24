from __future__ import annotations

from pathlib import Path

from auto_evaluation_system.product_api.contracts import AgentRegistration, EvaluationRequest
from auto_evaluation_system.product_api.service import ProductEvaluationService


def create_app(storage_root: str | Path = "runs/product"):
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise RuntimeError("FastAPI is not installed. Install with .[product].") from exc

    service = ProductEvaluationService(storage_root=storage_root)
    app = FastAPI(title="Agent Security Product API", version="0.1.0")

    @app.post("/v1/agents")
    def register_agent(registration: AgentRegistration):
        return service.register_agent(registration).model_dump(mode="json")

    @app.post("/v1/agents/{agent_id}/sessions")
    def create_session(agent_id: str, tenant_id: str = "private_tenant"):
        return service.create_session(tenant_id=tenant_id, agent_id=agent_id)

    @app.post("/v1/evaluations")
    def create_evaluation(request: EvaluationRequest):
        return service.run_evaluation(request).model_dump(mode="json")

    @app.get("/v1/evaluations/{evaluation_id}")
    def get_evaluation(evaluation_id: str):
        return service.get_evaluation(evaluation_id).model_dump(mode="json")

    @app.get("/v1/reports/{report_id}")
    def get_report(report_id: str):
        return service.get_report(report_id).model_dump(mode="json")

    @app.post("/v1/comparisons")
    def compare_reports(payload: dict):
        return service.compare_reports(
            before_report_id=str(payload["before_report_id"]),
            after_report_id=str(payload["after_report_id"]),
        ).model_dump(mode="json")

    @app.post("/v1/trajectories")
    def upload_trajectory(payload: dict):
        return service.upload_trajectory(
            tenant_id=str(payload.get("tenant_id") or "private_tenant"),
            agent_id=str(payload["agent_id"]),
            trajectory=dict(payload.get("trajectory") or {}),
        )

    return app
