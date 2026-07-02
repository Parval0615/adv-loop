from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from run import DEFAULT_TASK_EVAL_INSTRUCTIONS


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_agent_task_cli_writes_trace_artifacts(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "run.py",
            "--agent-task",
            "搜索降噪耳机",
            "--offline",
            "--results-root",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "AGENT_TASK=搜索降噪耳机" in completed.stdout
    assert "GOAL_ACHIEVED=True" in completed.stdout
    assert "TRACE_GRAPH_MD=" in completed.stdout

    report = json.loads((tmp_path / "trace_report.json").read_text(encoding="utf-8"))
    assert report["call_details"][0]["name"] == "product_search"
    assert (tmp_path / "trace_graph.md").exists()
    assert (tmp_path / "trace_timeline.jsonl").exists()
    assert (tmp_path / "trace_integrity.json").exists()


def test_agent_demo_cli_contains_replan_scenario(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "run.py",
            "--agent-demo",
            "--offline",
            "--results-root",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "SCENARIO=basic-search" in completed.stdout
    assert "SCENARIO=replan-stock-recovery" in completed.stdout
    assert "REPLANS=1" in completed.stdout
    assert "TRACE=1:cart_add_item:blocked:replan > 2:cart_add_item:ok" in completed.stdout
    assert (tmp_path / "basic-search" / "trace_integrity.json").exists()
    assert (tmp_path / "replan-stock-recovery" / "trace_integrity.json").exists()


def test_task_eval_cli_uses_default_tasks_and_writes_report(tmp_path: Path) -> None:
    completed = _run_cli(
        [
            "--task-eval",
            "--offline",
            "--results-root",
            str(tmp_path),
        ]
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert f"TASK_EVAL_REPORT={tmp_path / 'task_evaluation_report.json'}" in completed.stdout
    assert "task_achievement_rate=" in completed.stdout
    assert "average_steps=" in completed.stdout
    assert "replan_success_rate=" in completed.stdout
    assert "invalid_tool_call_rate=" in completed.stdout

    report = json.loads((tmp_path / "task_evaluation_report.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == "task-evaluation-report-v0.1"
    assert report["metrics"]["total_tasks"] == len(DEFAULT_TASK_EVAL_INSTRUCTIONS)
    assert len(report["records"]) == len(DEFAULT_TASK_EVAL_INSTRUCTIONS)


def test_task_eval_cli_reads_txt_task_file(tmp_path: Path) -> None:
    task_file = tmp_path / "tasks.txt"
    task_file.write_text("搜索降噪耳机\n\n联系平台招商客服\n", encoding="utf-8")
    results_root = tmp_path / "txt-results"

    completed = _run_cli(
        [
            "--task-eval",
            "--offline",
            "--task-file",
            str(task_file),
            "--results-root",
            str(results_root),
        ]
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads((results_root / "task_evaluation_report.json").read_text(encoding="utf-8"))
    assert report["metrics"]["total_tasks"] == 2
    assert [record["task_goal"] for record in report["records"]] == ["搜索降噪耳机", "联系平台招商客服"]


def test_task_eval_cli_reads_json_task_file(tmp_path: Path) -> None:
    task_file = tmp_path / "tasks.json"
    task_file.write_text(json.dumps(["搜索降噪耳机", "把降噪耳机加入购物车"], ensure_ascii=False), encoding="utf-8")
    results_root = tmp_path / "json-results"

    completed = _run_cli(
        [
            "--task-eval",
            "--offline",
            "--task-file",
            str(task_file),
            "--results-root",
            str(results_root),
        ]
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads((results_root / "task_evaluation_report.json").read_text(encoding="utf-8"))
    assert report["metrics"]["total_tasks"] == 2
    assert [record["task_goal"] for record in report["records"]] == ["搜索降噪耳机", "把降噪耳机加入购物车"]


def test_task_eval_cli_rejects_empty_task_file(tmp_path: Path) -> None:
    task_file = tmp_path / "empty.txt"
    task_file.write_text("\n", encoding="utf-8")

    completed = _run_cli(
        [
            "--task-eval",
            "--offline",
            "--task-file",
            str(task_file),
            "--results-root",
            str(tmp_path / "empty-results"),
        ]
    )

    assert completed.returncode == 2
    assert "TASK_EVAL_ERROR=" in completed.stderr
    assert "empty or contains no task instructions" in completed.stderr


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "run.py", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
