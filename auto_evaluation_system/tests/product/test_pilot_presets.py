from pathlib import Path

from auto_evaluation_system.product_api.attack_pack import load_ecommerce_attack_pack
from auto_evaluation_system.product_api.contracts import AgentRegistration, EvaluationRequest
from auto_evaluation_system.product_api.presets import get_pilot_preset, load_pilot_presets
from auto_evaluation_system.product_api.service import ProductEvaluationService


def test_pilot_presets_load_and_reference_existing_scenarios() -> None:
    manifest = load_pilot_presets()
    attack_pack = load_ecommerce_attack_pack()
    attack_scenario_ids = {scenario.scenario_id for scenario in attack_pack.scenarios}

    assert manifest.schema_version == "pilot-presets-v0.1"
    assert {preset.preset_id for preset in manifest.presets} == {
        "customer_service",
        "shopping_guide",
        "merchant_operations",
    }
    for preset in manifest.presets:
        assert set(preset.scenario_ids) <= attack_scenario_ids
        assert preset.demo_data_boundary["no_real_payment"] is True
        assert preset.demo_data_boundary["no_external_attack"] is True


def test_get_pilot_preset_rejects_unknown_preset() -> None:
    try:
        get_pilot_preset("unknown")
    except ValueError as exc:
        assert "Pilot preset not found" in str(exc)
    else:
        raise AssertionError("unknown pilot preset should fail")


def test_service_runs_each_pilot_preset(tmp_path: Path) -> None:
    service = ProductEvaluationService(storage_root=tmp_path)
    registration = service.register_agent(
        AgentRegistration(agent_id="ecommerce_customer_guide", name="E-commerce Guide")
    )

    for preset in load_pilot_presets().presets:
        status = service.run_evaluation(
            EvaluationRequest(
                tenant_id=registration.tenant_id,
                agent_id=registration.agent_id,
                pilot_preset=preset.preset_id,
            )
        )
        report = service.get_report(status.report_id or status.evaluation_id)

        assert status.status == "completed"
        assert report.summary["pilot_preset"] == preset.preset_id
        assert {item.scenario_id for item in report.scenario_results} == set(preset.scenario_ids)
        assert Path(report.artifacts.dashboard_path or "").exists()
