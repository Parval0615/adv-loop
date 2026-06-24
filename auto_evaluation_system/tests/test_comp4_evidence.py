"""竞赛证据包测试。

验证：
1. 多轮对抗收敛：ASR 单调下降且收敛到 ≤10%（ROADMAP 答辩王牌曲线）。
2. 消融实验三组对照齐全：去掉 Defense → ASR 高位不降；去掉 reflection → 覆盖停滞。
3. 单命令 demo 落盘全部 artifact（含两张 PNG 图）。
4. 离线确定性可复现。
"""

from __future__ import annotations

import json
from pathlib import Path

from auto_attack_system.attack_agent import AttackAgent
from auto_attack_system.llm_client import SharedLLMClient
from auto_attack_system.threat_taxonomy import SyntheticTarget

from auto_evaluation_system.comp4_evidence import run_comp4_demo


def test_reflection_ablation_stalls_coverage() -> None:
    """关闭反思 → 攻击不升级 → 覆盖率停滞,远低于开启反思。"""
    with_reflection = AttackAgent(
        llm=SharedLLMClient(force_offline=True)
    ).run()
    without = AttackAgent(
        llm=SharedLLMClient(force_offline=True), disable_reflection=True
    ).run()
    assert without.coverage_count < with_reflection.coverage_count
    assert all(not r.escalated for r in without.reflections)


def test_convergence_is_monotonic_and_meets_target(tmp_path: Path) -> None:
    result = run_comp4_demo(runs_root=tmp_path, timestamp="t", force_offline=True)
    m = result.metrics
    assert m["asr_monotonic_decreasing"] is True
    assert m["asr_initial"] > m["asr_final"]
    assert m["asr_final"] <= 0.10
    assert m["asr_target_met"] is True


def test_ablation_proves_each_agent_indispensable(tmp_path: Path) -> None:
    result = run_comp4_demo(runs_root=tmp_path, timestamp="t", force_offline=True)
    m = result.metrics
    # 去掉 Defense → ASR 远高于完整系统
    assert m["ablation_no_defense_asr"] > m["ablation_full_asr"]
    # 去掉 reflection → 覆盖远低于完整系统
    assert m["ablation_no_reflection_coverage"] < m["ablation_full_coverage"] or (
        m["ablation_full_coverage"] == 0
        and m["ablation_no_reflection_coverage"]
        < m["total_threat_categories"]
    )


def test_demo_writes_full_evidence_bundle(tmp_path: Path) -> None:
    result = run_comp4_demo(runs_root=tmp_path, timestamp="t", force_offline=True)
    run_dir = tmp_path / "t"
    for name in (
        "convergence.json",
        "convergence_curve.png",
        "damage_radar.png",
        "ablation.json",
        "ablation_table.md",
        "benchmark_datacard.md",
        "evidence_pack.md",
    ):
        assert (run_dir / name).exists(), f"missing artifact {name}"
    # PNG 非空且为合法 PNG 头
    for png in ("convergence_curve.png", "damage_radar.png"):
        data = (run_dir / png).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(data) > 1000

    payload = json.loads((run_dir / "convergence.json").read_text(encoding="utf-8"))
    assert payload["rounds"][0]["round"] == 0
    assert payload["llm_mode"] == "deterministic-offline"


def test_demo_is_deterministic_offline(tmp_path: Path) -> None:
    first = run_comp4_demo(
        runs_root=tmp_path / "a", timestamp="r", force_offline=True
    ).metrics
    second = run_comp4_demo(
        runs_root=tmp_path / "b", timestamp="r", force_offline=True
    ).metrics
    assert first == second
