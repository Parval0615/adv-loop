from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
SOURCE_DIRS = (
    "auto_attack_system/src",
    "auto_defense_system/src",
    "auto_evaluation_system/src",
    ".",
)
DEFAULT_TASK_EVAL_INSTRUCTIONS = (
    "搜索降噪耳机",
    "搜索智能手表",
    "联系平台招商客服说明订单问题",
)


def main() -> int:
    args = _parse_args()
    repo_root = REPO_ROOT
    _add_source_paths(repo_root)

    if args.agent_task is not None:
        from task_agent import TaskAgent
        from task_agent.trace_adapter import export_plan_trace

        result = TaskAgent(force_offline=args.offline).run(args.agent_task)
        run_dir = _resolve_agent_results_root(repo_root, args.results_root, "task-agent")
        artifacts = export_plan_trace(result, run_dir)
        _print_agent_summary(result, run_dir=run_dir, artifacts=artifacts)
        return 0

    if args.agent_demo:
        _run_agent_demo(repo_root=repo_root, results_root=args.results_root, force_offline=args.offline)
        return 0

    if args.task_eval:
        try:
            report, report_path = _run_task_evaluation(
                repo_root=repo_root,
                results_root=args.results_root,
                task_file=args.task_file,
                force_offline=args.offline,
            )
        except ValueError as exc:
            print(f"TASK_EVAL_ERROR={exc}", file=sys.stderr)
            return 2
        _print_task_eval_summary(report, report_path=report_path)
        return 0

    if args.evidence_pack:
        from auto_evaluation_system.comp4_evidence import run_comp4_demo

        result = run_comp4_demo(
            repo_root=repo_root,
            runs_root=args.results_root,
            force_offline=args.offline,
        )
        _print_comp4_summary(result)
        return 0 if result.metrics["asr_target_met"] else 1

    if args.defense_regression:
        from auto_defense_system.comp3_demo import run_comp3_demo

        result = run_comp3_demo(
            repo_root=repo_root,
            runs_root=args.results_root,
            force_offline=args.offline,
        )
        _print_comp3_summary(result)
        return 0 if result.metrics["exit_criteria_met"] else 1

    if args.attack_campaign:
        from auto_attack_system.comp2_campaign import run_comp2_demo

        result = run_comp2_demo(
            repo_root=repo_root,
            runs_root=args.results_root,
            force_offline=args.offline,
        )
        _print_comp2_summary(result)
        return 0 if result.metrics["coverage_target_met"] else 1

    if args.closed_loop_demo:
        from auto_evaluation_system.runner import run_comp1_demo

        result = run_comp1_demo(
            repo_root=repo_root,
            runs_root=args.results_root,
        )
        _print_demo_summary(result)
        return 0 if result.metrics["all_passed"] else 1

    from auto_evaluation_system.runner import run_closed_loop_evaluation

    results_root = _resolve_results_root(repo_root, args.results_root)
    scenario_manifest = repo_root / "auto_evaluation_system" / "configs" / "scenarios" / "manifest.yaml"
    acceptance_manifest = repo_root / "auto_evaluation_system" / "datasets" / "acceptance" / "detectors" / "manifest.yaml"

    report = run_closed_loop_evaluation(
        scenario_manifest,
        acceptance_manifest,
        repo_root=repo_root,
        results_root=results_root,
    )

    _print_summary(report)
    return 0 if all(record.passed for record in report.records) else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the deterministic offline Attack -> Defense -> Evaluation closed-loop experiment.",
    )
    parser.add_argument(
        "--closed-loop-demo",
        dest="closed_loop_demo",
        action="store_true",
        help="Run the single-command closed-loop demo and write the runs/<timestamp>/ artifact bundle.",
    )
    parser.add_argument(
        "--demo",
        dest="closed_loop_demo",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--attack-campaign",
        dest="attack_campaign",
        action="store_true",
        help=(
            "Run the Attack Agent campaign (attack history / failure reflection / "
            "replanning) and write the attack-runs/<timestamp>/ artifact bundle."
        ),
    )
    parser.add_argument(
        "--comp2",
        dest="attack_campaign",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--defense-regression",
        dest="defense_regression",
        action="store_true",
        help=(
            "Run the Defense Agent regression (auto-select hardening actions from "
            "the damage report, measure mitigation effectiveness & false-positive rate) "
            "and write the defense-runs/<timestamp>/ artifact bundle."
        ),
    )
    parser.add_argument(
        "--comp3",
        dest="defense_regression",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--evidence-pack",
        dest="evidence_pack",
        action="store_true",
        help=(
            "Run the competition evidence pack (multi-round adversarial convergence "
            "curve, damage radar, ablation study, benchmark data card) and write the "
            "evidence-runs/<timestamp>/ artifact bundle."
        ),
    )
    parser.add_argument(
        "--comp4",
        dest="evidence_pack",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--agent-task",
        default=None,
        help="Run one autonomous ecommerce TaskAgent instruction and export trace artifacts.",
    )
    parser.add_argument(
        "--agent-demo",
        action="store_true",
        help="Run preset TaskAgent demos, including a stock-failure replanning scenario.",
    )
    parser.add_argument(
        "--task-eval",
        action="store_true",
        help="Run the batch TaskAgent evaluation and write task_evaluation_report.json.",
    )
    parser.add_argument(
        "--task-file",
        type=Path,
        default=None,
        help="Task evaluation input file: line-delimited text or a JSON array of task instructions.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Force deterministic offline mode for task-agent, attack, defense, and evidence-pack runs (no LLM API calls).",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=None,
        help=(
            "Output directory. In closed-loop demo mode this is the parent of the <timestamp>/ run "
            "(defaults to runs/). Otherwise it is the closed-loop results root "
            "(defaults to runs/closed-loop-<timestamp>)."
        ),
    )
    args = parser.parse_args()
    if args.task_file is not None and not args.task_eval:
        parser.error("--task-file requires --task-eval")
    return args


def _add_source_paths(repo_root: Path) -> None:
    for rel_path in reversed(SOURCE_DIRS):
        source_path = str(repo_root / rel_path)
        if source_path not in sys.path:
            sys.path.insert(0, source_path)


def _default_results_root(repo_root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return repo_root / "runs" / f"closed-loop-{stamp}"


def _resolve_results_root(repo_root: Path, requested: Path | None) -> Path:
    if requested is None:
        return _default_results_root(repo_root)
    if requested.is_absolute():
        return requested
    return repo_root / requested


def _resolve_agent_results_root(repo_root: Path, requested: Path | None, prefix: str) -> Path:
    if requested is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return repo_root / "runs" / f"{prefix}-{stamp}"
    if requested.is_absolute():
        return requested
    return repo_root / requested


def _print_summary(report) -> None:
    print(f"REPORT_PATH={report.metadata['report_path']}")
    print(f"SCHEMA={report.schema_version}")
    print(f"RECORDS={len(report.records)}")

    for record in report.records:
        print(
            f"{record.pair_id} | "
            f"risk={record.risk_type} | "
            f"metric={record.metric} | "
            f"detector={record.detector_output.decision} | "
            f"clean={record.clean_defense_decision.decision} | "
            f"controlled={record.controlled_defense_decision.decision} | "
            f"audit={record.audit_integrity.valid} | "
            f"passed={record.passed}"
        )
        if record.failure_notes:
            for note in record.failure_notes:
                print(f"  failure: {note}")


def _run_task_evaluation(
    *,
    repo_root: Path,
    results_root: Path | None,
    task_file: Path | None,
    force_offline: bool,
):
    from auto_evaluation_system.task_eval import evaluate_task_runs
    from task_agent import TaskAgent

    instructions = _load_task_eval_instructions(task_file)
    results = [
        TaskAgent(force_offline=force_offline).run(instruction)
        for instruction in instructions
    ]
    report = evaluate_task_runs(results)

    run_dir = _resolve_agent_results_root(repo_root, results_root, "task-eval")
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "task_evaluation_report.json"
    report_path.write_text(_task_eval_report_json(report), encoding="utf-8")
    return report, report_path


def _load_task_eval_instructions(task_file: Path | None) -> list[str]:
    if task_file is None:
        return list(DEFAULT_TASK_EVAL_INSTRUCTIONS)

    try:
        content = task_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read task file {task_file}: {exc}") from exc

    if not content.strip():
        raise ValueError(f"task file {task_file} is empty or contains no task instructions")

    stripped = content.lstrip()
    if task_file.suffix.lower() == ".json" or stripped.startswith("["):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"task file {task_file} must be a JSON array of strings") from exc
        if not isinstance(parsed, list):
            raise ValueError(f"task file {task_file} must be a JSON array of strings")
        return _normalize_task_eval_instructions(parsed, source=f"task file {task_file}")

    return _normalize_task_eval_instructions(content.splitlines(), source=f"task file {task_file}")


def _normalize_task_eval_instructions(values, *, source: str) -> list[str]:
    instructions: list[str] = []
    for index, value in enumerate(values, start=1):
        if not isinstance(value, str):
            raise ValueError(f"{source} item {index} must be a string")
        text = value.strip()
        if text:
            instructions.append(text)
    if not instructions:
        raise ValueError(f"{source} is empty or contains no task instructions")
    return instructions


def _task_eval_report_json(report) -> str:
    data = report.model_dump() if hasattr(report, "model_dump") else report.dict()
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _print_task_eval_summary(report, *, report_path: Path) -> None:
    metrics = report.metrics
    print(f"TASK_EVAL_REPORT={report_path}")
    print(f"schema_version={report.schema_version}")
    print(f"total_tasks={metrics.total_tasks}")
    print(f"achieved_tasks={metrics.achieved_tasks}")
    print(f"task_achievement_rate={metrics.task_achievement_rate:.6f}")
    print(f"average_steps={metrics.average_steps:.6f}")
    print(f"replan_success_rate={metrics.replan_success_rate:.6f}")
    print(f"invalid_tool_call_rate={metrics.invalid_tool_call_rate:.6f}")


def _run_agent_demo(*, repo_root: Path, results_root: Path | None, force_offline: bool) -> None:
    from auto_defense_system.ecommerce_agent.fixtures import create_demo_store
    from task_agent import TaskAgent
    from task_agent.trace_adapter import export_plan_trace

    run_dir = _resolve_agent_results_root(repo_root, results_root, "agent-demo")

    search_result = TaskAgent(force_offline=force_offline).run("搜索降噪耳机", max_steps=4)
    search_artifacts = export_plan_trace(search_result, run_dir / "basic-search")
    _print_agent_summary(
        search_result,
        scenario_id="basic-search",
        run_dir=run_dir / "basic-search",
        artifacts=search_artifacts,
    )

    store = create_demo_store()
    store.products["p1001"].stock = 0
    replan_result = TaskAgent(
        store=store,
        force_offline=force_offline,
        llm=_DemoReplanLLM(),
    ).run("把有货商品加入购物车", max_steps=4, max_replans=2)
    replan_artifacts = export_plan_trace(replan_result, run_dir / "replan-stock-recovery")
    _print_agent_summary(
        replan_result,
        scenario_id="replan-stock-recovery",
        run_dir=run_dir / "replan-stock-recovery",
        artifacts=replan_artifacts,
    )


class _DemoReplanLLM:
    mode = "scripted-demo-offline"

    def __init__(self) -> None:
        self._replanned = False

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint,
        seed: int = 0,
        max_tokens: int = 1024,
    ) -> dict:
        from task_agent.prompts import (
            ARGUMENT_GENERATION_SYSTEM_PROMPT,
            EXECUTION_THOUGHT_SYSTEM_PROMPT,
            GOAL_JUDGE_SYSTEM_PROMPT,
            PLAN_GENERATION_SYSTEM_PROMPT,
            REPLAN_SYSTEM_PROMPT,
            TASK_PARSE_SYSTEM_PROMPT,
        )

        if system == TASK_PARSE_SYSTEM_PROMPT:
            return {
                "raw_instruction": "把有货商品加入购物车",
                "goal": "把有货商品加入购物车",
                "subgoals": ["尝试加入目标商品", "失败后选择有货替代商品"],
                "constraints": {},
                "entities": {"demo": "stock_replan"},
                "parse_mode": "scripted-demo",
            }
        if system == PLAN_GENERATION_SYSTEM_PROMPT:
            return {
                "revision": 0,
                "steps": [
                    {
                        "step_id": "add-original",
                        "candidate_tool": "cart_add_item",
                        "args_hint": {"product_id": "p1001", "quantity": 1},
                    }
                ],
            }
        if system == REPLAN_SYSTEM_PROMPT:
            self._replanned = True
            return {
                "revision": 1,
                "steps": [
                    {
                        "step_id": "add-alternative",
                        "candidate_tool": "cart_add_item",
                        "args_hint": {"product_id": "p2001", "quantity": 1},
                    }
                ],
            }
        if system == EXECUTION_THOUGHT_SYSTEM_PROMPT:
            return {"thought": "执行当前计划，观察真实库存和业务规则反馈。"}
        if system == ARGUMENT_GENERATION_SYSTEM_PROMPT:
            return {}
        if system == GOAL_JUDGE_SYSTEM_PROMPT:
            return {"goal_achieved": self._replanned, "reason": "demo state rules should decide"}
        return {}

    def decide(self, system: str, user: str, *, choices: list[str], seed: int = 0) -> dict:
        choice = choices[0] if choices else None
        return {"choice": choice, "reason": "scripted demo chooses the planned tool"}


def _print_agent_summary(result, *, run_dir: Path | None = None, artifacts: dict[str, str] | None = None, scenario_id: str | None = None) -> None:
    if scenario_id:
        print(f"SCENARIO={scenario_id}")
    if run_dir is not None:
        print(f"RUN_DIR={run_dir}")
    if artifacts:
        print(f"TRACE_GRAPH_MD={artifacts.get('trace_mermaid', '')}")
        print(f"TRACE_TIMELINE={artifacts.get('trace_timeline', '')}")
        print(f"TRACE_INTEGRITY={artifacts.get('trace_integrity', '')}")
    print(f"AGENT_TASK={_one_line(result.task_spec.raw_instruction)}")
    print(f"LLM_MODE={result.llm_mode}")
    print(f"GOAL_ACHIEVED={result.goal_achieved}")
    print(f"STEPS={len(result.trace)}")
    print(f"PLANS={len(result.plans)}")
    print(f"REPLANS={result.replan_count}")
    print(f"FINAL_ANSWER={_one_line(result.final_answer)}")
    if result.trace:
        print(
            "TRACE="
            + " > ".join(
                f"{index}:{step.action_tool}:{'blocked' if step.observation.blocked else 'ok'}"
                f"{':replan' if step.replan_triggered else ''}"
                for index, step in enumerate(result.trace, start=1)
            )
        )


def _one_line(value, *, limit: int = 500) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _print_demo_summary(result) -> None:
    metrics = result.metrics
    print(f"RUN_DIR={result.run_dir}")
    print("ARTIFACTS=" + ",".join(sorted(result.artifacts)))
    print(f"THREATS_COVERED={metrics['threat_category_count']}")
    print(f"ASR_BEFORE={metrics['asr_before_defense']}")
    print(f"ASR_AFTER={metrics['asr_after_defense']}")
    print(f"MITIGATION={metrics['mitigation_effectiveness']}")
    print(f"FALSE_POSITIVE_RATE={metrics['false_positive_rate']}")
    print(f"AUDIT_CHAIN_VALID={metrics['audit_chain_valid']}")
    print(f"PASSED={metrics['passed_pairs']}/{metrics['total_attack_pairs']}")


def _print_comp2_summary(result) -> None:
    metrics = result.metrics
    print(f"RUN_DIR={result.run_dir}")
    print("ARTIFACTS=" + ",".join(sorted(result.artifacts)))
    print(f"LLM_MODE={metrics['llm_mode']}")
    print(f"ROUNDS={metrics['rounds']}")
    print(
        f"COVERAGE={metrics['coverage_final']}/{metrics['total_threat_categories']} "
        f"({metrics['coverage_rate']:.0%})"
    )
    print(f"COVERAGE_FIRST_ROUND={metrics['coverage_first_round']}")
    print(f"REFLECTION_GAIN=+{metrics['coverage_gain_from_reflection']}")
    print(f"ESCALATIONS={metrics['escalations']}")
    print(f"ATTEMPTS={metrics['successful_attempts']}/{metrics['total_attempts']}")
    print(f"COVERAGE_TARGET_MET={metrics['coverage_target_met']}")


def _print_comp3_summary(result) -> None:
    metrics = result.metrics
    print(f"RUN_DIR={result.run_dir}")
    print("ARTIFACTS=" + ",".join(sorted(result.artifacts)))
    print(f"LLM_MODE={metrics['llm_mode']}")
    print(f"ASR_BEFORE={metrics['asr_before']:.0%}")
    print(f"ASR_AFTER={metrics['asr_after']:.0%}")
    print(
        f"MITIGATION={metrics['mitigation_effectiveness']:.0%} "
        f"(target>=70%, met={metrics['mitigation_target_met']})"
    )
    print(
        f"FALSE_POSITIVE_TARGETED={metrics['false_positive_rate_targeted']:.0%} "
        f"(target<=5%, met={metrics['false_positive_target_met']})"
    )
    print(
        f"FALSE_POSITIVE_BLANKET={metrics['false_positive_rate_blanket']:.0%} "
        f"(ablation)"
    )
    print(
        f"HARDENED={metrics['hardened_count']} categories | "
        f"benign_blocked targeted={metrics['benign_blocked_targeted']}/"
        f"{metrics['benign_total']} blanket={metrics['benign_blocked_blanket']}/"
        f"{metrics['benign_total']}"
    )
    print(f"EXIT_CRITERIA_MET={metrics['exit_criteria_met']}")


def _print_comp4_summary(result) -> None:
    metrics = result.metrics
    print(f"RUN_DIR={result.run_dir}")
    print("ARTIFACTS=" + ",".join(sorted(result.artifacts)))
    print(f"LLM_MODE={metrics['llm_mode']}")
    print(f"ASR_INITIAL={metrics['asr_initial']:.0%}")
    print(f"ASR_FINAL={metrics['asr_final']:.0%}")
    print(f"CONVERGENCE_ROUNDS={metrics['convergence_rounds']}")
    print(f"ASR_MONOTONIC_DECREASING={metrics['asr_monotonic_decreasing']}")
    print(f"ASR_TARGET_MET(<=10%)={metrics['asr_target_met']}")
    print(
        f"ABLATION_NO_DEFENSE_ASR={metrics['ablation_no_defense_asr']:.0%} "
        f"(vs full {metrics['ablation_full_asr']:.0%})"
    )
    print(
        f"ABLATION_NO_REFLECTION_COVERAGE={metrics['ablation_no_reflection_coverage']}/"
        f"{metrics['total_threat_categories']} "
        f"(vs full {metrics['ablation_full_coverage']}/{metrics['total_threat_categories']})"
    )


if __name__ == "__main__":
    raise SystemExit(main())
