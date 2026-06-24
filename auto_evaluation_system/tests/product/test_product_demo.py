from pathlib import Path

from auto_evaluation_system.product_api.demo import run_private_ecommerce_demo


def test_private_ecommerce_demo_generates_report(tmp_path: Path) -> None:
    result = run_private_ecommerce_demo(storage_root=tmp_path)
    report = result["report"]

    assert result["status"]["status"] == "completed"
    assert report["schema_version"] == "agent-security-report-v0.1"
    assert report["scenario_results"]
    assert Path(report["artifacts"]["report_path"]).exists()
    assert Path(report["artifacts"]["markdown_path"]).exists()
    assert Path(report["artifacts"]["dashboard_path"]).exists()
    assert report["artifacts"]["audit_refs"]
    assert Path(report["artifacts"]["audit_refs"][0]).exists()


def test_private_ecommerce_demo_accepts_pilot_preset(tmp_path: Path) -> None:
    result = run_private_ecommerce_demo(storage_root=tmp_path, pilot_preset="merchant_operations")
    report = result["report"]

    assert result["status"]["status"] == "completed"
    assert report["summary"]["pilot_preset"] == "merchant_operations"
    assert {item["scenario_id"] for item in report["scenario_results"]} == {
        "buyer-merchant-tool-abuse",
        "tool-tampering-stock-abuse",
    }
