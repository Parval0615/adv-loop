from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
SOURCE_DIRS = (
    "auto_attack_system/src",
    "auto_defense_system/src",
    "auto_evaluation_system/src",
)


def main() -> int:
    args = _parse_args()
    repo_root = REPO_ROOT
    _add_source_paths(repo_root)

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
        "--offline",
        action="store_true",
        help="Force deterministic offline mode for attack, defense, and evidence-pack runs (no LLM API calls).",
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
    return parser.parse_args()


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
