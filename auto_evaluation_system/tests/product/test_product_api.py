import pytest

from auto_evaluation_system.product_api.app import create_app


def test_fastapi_app_is_optional(tmp_path) -> None:
    fastapi = pytest.importorskip("fastapi")
    app = create_app(storage_root=tmp_path)

    routes = {route.path for route in app.routes}
    assert "/v1/agents" in routes
    assert "/v1/evaluations" in routes
    assert "/v1/reports/{report_id}" in routes
