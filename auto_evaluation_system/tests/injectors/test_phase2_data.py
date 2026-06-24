import json
from pathlib import Path

from jsonschema import validate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "trajectory-v1.schema.json").read_text(encoding="utf-8"))
MANIFEST = ROOT / "datasets" / "annotated" / "phase2" / "manifest.json"


def test_phase2_manifest_points_to_schema_valid_labeled_trajectories() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == "phase2-annotated-v0.1"
    assert {record["risk_type"] for record in manifest["records"]} == {
        "memory_poisoning",
        "tool_tampering",
        "goal_perturbation",
    }
    for record in manifest["records"]:
        scenario_path = ROOT / record["scenario_path"]
        trajectory_path = ROOT / record["trajectory_path"]
        assert scenario_path.exists()
        assert trajectory_path.exists()
        trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
        validate(instance=trajectory, schema=SCHEMA)
        injection = trajectory["metadata"]["injections"][0]
        assert injection["label"] == record["label"]
        assert injection["injection_id"] == record["injection_id"]
