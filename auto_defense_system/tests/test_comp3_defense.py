"""Defense Agent 回归测试。

验证：
1. Defense Agent 据损伤报告对每个被攻破类别选出精准加固动作。
2. 加固后靶场重打 → ASR 显著下降，加固有效率 ≥70%（ROADMAP 退出标准）。
3. 精准加固不误伤良性请求（误伤率 ≤5%）；一刀切(blanket)消融全量误伤。
4. 单命令 demo 落盘全部 3 个 artifact。
5. 综合退出标准（有效率≥70% 且 误伤率≤5%）达标。
6. 离线确定性可复现。
"""

from __future__ import annotations

import json
from pathlib import Path

from auto_attack_system.llm_client import SharedLLMClient
from auto_attack_system.threat_taxonomy import (
    THREAT_CATEGORIES,
    SyntheticTarget,
)

from auto_defense_system.comp3_demo import (
    FALSE_POSITIVE_TARGET,
    MITIGATION_TARGET,
    run_comp3_demo,
)
from auto_defense_system.defense_agent import (
    DEFENSE_PLAYBOOK,
    DefenseAgent,
    HARDENED_RESISTANCE,
    _defense_candidates,
)


class _InvalidDefenseLLM:
    offline = False
    mode = "fake-online"

    def __init__(self) -> None:
        self.decide_calls: list[list[str]] = []

    def decide(
        self,
        system: str,
        user: str,
        *,
        choices: list[str],
        seed: int = 0,
    ) -> dict:
        self.decide_calls.append(list(choices))
        return {"choice": "not-a-candidate"}

    def complete(
        self,
        system: str,
        user: str,
        *,
        seed: int = 0,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> str:
        return "选择该动作以针对性降低已攻破类别风险。"


def test_playbook_covers_all_seven_threats() -> None:
    assert set(DEFENSE_PLAYBOOK) == set(THREAT_CATEGORIES)


def test_harden_selects_targeted_action_per_breached_category() -> None:
    breached = ["prompt_injection", "tool_tampering", "sensitive_leakage"]
    agent = DefenseAgent(llm=SharedLLMClient(force_offline=True))
    result = agent.harden(breached, base_target=SyntheticTarget())

    assert result.hardened_categories == breached
    for decision in result.decisions:
        assert decision.action.precision == "targeted"
        assert decision.action.category == decision.category
        assert decision.resistance_after == HARDENED_RESISTANCE
        # 加固后阈值高于任何攻击阶梯 → 不可突破
        assert result.hardened_target.resistance[decision.category] == HARDENED_RESISTANCE


def test_invalid_hardening_choice_falls_back_to_playbook() -> None:
    llm = _InvalidDefenseLLM()
    result = DefenseAgent(llm=llm).harden(  # type: ignore[arg-type]
        ["tool_tampering"], base_target=SyntheticTarget()
    )

    assert llm.decide_calls
    assert result.decisions[0].action.name == DEFENSE_PLAYBOOK["tool_tampering"].name
    assert result.decisions[0].action.category == "tool_tampering"


def test_offline_hardening_uses_reproducible_decide_choice() -> None:
    breached = list(THREAT_CATEGORIES)
    first = DefenseAgent(llm=SharedLLMClient(force_offline=True)).harden(
        breached, base_target=SyntheticTarget()
    )
    second = DefenseAgent(llm=SharedLLMClient(force_offline=True)).harden(
        breached, base_target=SyntheticTarget()
    )

    first_actions = [d.action.name for d in first.decisions]
    assert first_actions == [d.action.name for d in second.decisions]
    for category, action_name in zip(breached, first_actions, strict=True):
        legal_names = {
            action.name for action in _defense_candidates(category, "targeted")
        }
        assert action_name in legal_names

    playbook_selected = [
        action_name == DEFENSE_PLAYBOOK[category].name
        for category, action_name in zip(breached, first_actions, strict=True)
    ]
    assert any(playbook_selected)
    assert not all(playbook_selected)


def test_blanket_strategy_produces_blanket_actions() -> None:
    breached = ["prompt_injection", "kb_poisoning"]
    agent = DefenseAgent(llm=SharedLLMClient(force_offline=True), strategy="blanket")
    result = agent.harden(breached, base_target=SyntheticTarget())
    assert all(d.action.precision == "blanket" for d in result.decisions)
    # 一刀切误伤全部良性请求
    assert all(e["blocked"] for e in result.benign_evaluations)


def test_targeted_hardening_does_not_block_benign_requests() -> None:
    agent = DefenseAgent(llm=SharedLLMClient(force_offline=True))
    result = agent.harden(
        list(THREAT_CATEGORIES), base_target=SyntheticTarget()
    )
    assert result.benign_evaluations  # 确有良性请求被评估
    assert all(not e["blocked"] for e in result.benign_evaluations)


def test_mitigation_and_false_positive_targets_met(tmp_path: Path) -> None:
    result = run_comp3_demo(
        runs_root=tmp_path, timestamp="testrun", force_offline=True
    )
    m = result.metrics
    # ASR 下降
    assert m["asr_after"] < m["asr_before"]
    # 加固有效率 ≥70%
    assert m["mitigation_effectiveness"] >= MITIGATION_TARGET
    assert m["mitigation_target_met"] is True
    # 误伤率 ≤5%
    assert m["false_positive_rate_targeted"] <= FALSE_POSITIVE_TARGET
    assert m["false_positive_target_met"] is True
    # 综合退出标准达标
    assert m["exit_criteria_met"] is True


def test_blanket_ablation_shows_false_positives(tmp_path: Path) -> None:
    result = run_comp3_demo(
        runs_root=tmp_path, timestamp="testrun", force_offline=True
    )
    m = result.metrics
    # 一刀切误伤率显著高于精准（证明精准选型必要性）
    assert m["false_positive_rate_blanket"] > m["false_positive_rate_targeted"]
    assert m["benign_blocked_blanket"] > m["benign_blocked_targeted"]


def test_demo_writes_full_artifact_bundle(tmp_path: Path) -> None:
    run_comp3_demo(runs_root=tmp_path, timestamp="testrun", force_offline=True)
    run_dir = tmp_path / "testrun"
    for name in (
        "hardening_decisions.json",
        "regression_report.json",
        "defense_summary.md",
    ):
        assert (run_dir / name).exists(), f"missing artifact {name}"

    payload = json.loads(
        (run_dir / "regression_report.json").read_text(encoding="utf-8")
    )
    assert payload["metrics"]["llm_mode"] == "deterministic-offline"
    assert payload["damage_report"]["breached_categories"]


def test_demo_is_deterministic_offline(tmp_path: Path) -> None:
    first = run_comp3_demo(
        runs_root=tmp_path / "a", timestamp="r", force_offline=True
    ).metrics
    second = run_comp3_demo(
        runs_root=tmp_path / "b", timestamp="r", force_offline=True
    ).metrics
    assert first == second
