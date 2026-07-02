"""Attack Agent 战役测试。

验证：
1. 共享 LLM 客户端离线确定性（同输入同输出，无需 API key）。
2. 反思可见提升覆盖率，最终覆盖 ≥6 类威胁（ROADMAP 退出标准）。
3. 单命令 demo 落盘全部 5 个 artifact。
4. 覆盖率随轮次单调不降（收敛曲线可用）。
5. 攻击历史中失败尝试带反思、成功尝试沉淀进经验库。
"""

from __future__ import annotations

import json
from pathlib import Path

from auto_attack_system.attack_agent import AttackAgent
from auto_attack_system.comp2_campaign import run_comp2_demo
from auto_attack_system.llm_client import SharedLLMClient
from auto_attack_system.threat_taxonomy import (
    THREAT_CATEGORIES,
    SyntheticTarget,
    ladder_for,
)


class _InvalidChoiceLLM:
    offline = False
    mode = "fake-online"

    def __init__(self) -> None:
        self.decide_calls: list[list[str]] = []
        self.complete_json_calls = 0

    def complete(
        self,
        system: str,
        user: str,
        *,
        seed: int = 0,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> str:
        return "诊断：当前攻击被目标防御拦截，需要调整方向。"

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint: object,
        seed: int = 0,
        max_tokens: int = 1024,
    ) -> dict:
        self.complete_json_calls += 1
        if "在线裁判" in system:
            return {"payload": "invalid judge shape"}
        return {
            "payload": "LLM 生成的下一条合成 payload",
            "rationale": "基于历史失败信号调整 payload。",
        }

    def decide(
        self,
        system: str,
        user: str,
        *,
        choices: list[str],
        seed: int = 0,
    ) -> dict:
        self.decide_calls.append(list(choices))
        return {"choice": "not-a-valid-choice"}


def test_shared_llm_offline_is_deterministic() -> None:
    client = SharedLLMClient(force_offline=True)
    assert client.offline is True
    assert client.mode == "deterministic-offline"
    first = client.complete("sys", "user", seed=7)
    second = client.complete("sys", "user", seed=7)
    assert first == second
    # 不同 seed → 不同输出
    assert client.complete("sys", "user", seed=7) != client.complete(
        "sys", "user", seed=8
    )


def test_reflection_improves_coverage_to_target() -> None:
    agent = AttackAgent(
        target=SyntheticTarget(),
        llm=SharedLLMClient(force_offline=True),
        max_rounds=6,
    )
    result = agent.run()

    # 首轮只能打穿少数类别（阈值为 0 的类别）
    first_round = result.coverage_timeline[0]["breached_count"]
    assert first_round < result.coverage_count

    # 反思升级后覆盖 ≥6/7（ROADMAP 退出标准）
    assert result.coverage_count >= 6
    assert (result.coverage_count - first_round) > 0

    # 确有策略升级发生
    assert any(r.escalated for r in result.reflections)


def test_invalid_reflection_choice_falls_back_to_legacy_escalation() -> None:
    llm = _InvalidChoiceLLM()
    agent = AttackAgent(
        target=SyntheticTarget(),
        llm=llm,  # type: ignore[arg-type]
        categories=["kb_poisoning"],
        max_rounds=2,
    )
    result = agent.run()

    assert llm.decide_calls
    assert result.coverage_count == 1
    assert result.reflections[0].escalated is True
    assert result.reflections[0].next_ladder_index == 1


def test_offline_reflection_uses_reproducible_decide_choice() -> None:
    def reflect_once() -> dict[str, tuple[bool, int | None, str | None]]:
        reflections = {}
        for category in THREAT_CATEGORIES:
            strategy = ladder_for(category)[0]
            reflection = AttackAgent(
                target=SyntheticTarget(),
                llm=SharedLLMClient(force_offline=True),
                categories=[category],
            )._reflect(category, strategy, ladder_index=0, round_index=1)
            reflections[category] = (
                reflection.escalated,
                reflection.next_ladder_index,
                reflection.next_strategy,
            )
        return reflections

    first = reflect_once()
    second = reflect_once()

    assert first == second
    assert any(escalated for escalated, _, _ in first.values())
    assert any(not escalated for escalated, _, _ in first.values())
    for category, (escalated, next_index, next_strategy) in first.items():
        if escalated:
            assert next_index == 1
            assert next_strategy == ladder_for(category)[1].name
        else:
            assert next_index is None
            assert next_strategy is None


def test_plan_uses_llm_json_payload_when_online() -> None:
    llm = _InvalidChoiceLLM()
    result = AttackAgent(
        target=SyntheticTarget(),
        llm=llm,  # type: ignore[arg-type]
        categories=["prompt_injection"],
        max_rounds=1,
    ).run()

    assert llm.complete_json_calls > 0
    assert result.attempts[0].payload == "LLM 生成的下一条合成 payload"


def test_offline_plan_payload_falls_back_to_ladder_deterministically() -> None:
    category = "kb_poisoning"
    first = AttackAgent(
        target=SyntheticTarget(),
        llm=SharedLLMClient(force_offline=True),
        categories=[category],
        max_rounds=1,
    ).run()
    second = AttackAgent(
        target=SyntheticTarget(),
        llm=SharedLLMClient(force_offline=True),
        categories=[category],
        max_rounds=1,
    ).run()

    expected = ladder_for(category)[0].sample_payload
    assert first.attempts[0].payload == expected
    assert second.attempts[0].payload == expected


def test_synthetic_target_online_judge_overrides_or_falls_back() -> None:
    target = SyntheticTarget()
    judged = target.attempt(
        "prompt_injection",
        0,
        online_judge=lambda _: {
            "success": False,
            "blocked": True,
            "reason": "online judge blocked",
            "defense_signal": "blocked",
        },
    )
    fallback = target.attempt(
        "prompt_injection",
        0,
        online_judge=lambda _: {"payload": "invalid judge shape"},
    )

    assert judged.success is False
    assert judged.blocked is True
    assert fallback.success is True


def test_coverage_timeline_is_monotonic() -> None:
    result = AttackAgent(llm=SharedLLMClient(force_offline=True)).run()
    counts = [t["breached_count"] for t in result.coverage_timeline]
    assert counts == sorted(counts), "覆盖率应随轮次单调不降"


def test_demo_writes_full_artifact_bundle(tmp_path: Path) -> None:
    result = run_comp2_demo(
        runs_root=tmp_path,
        timestamp="testrun",
        force_offline=True,
    )
    run_dir = tmp_path / "testrun"
    for name in (
        "attack_history.jsonl",
        "reflection_log.json",
        "coverage_table.json",
        "coverage_table.md",
        "campaign_summary.md",
    ):
        assert (run_dir / name).exists(), f"missing artifact {name}"

    assert result.metrics["coverage_target_met"] is True
    assert result.metrics["llm_mode"] == "deterministic-offline"


def test_attack_history_records_reflection_and_experience(tmp_path: Path) -> None:
    result = run_comp2_demo(
        runs_root=tmp_path,
        timestamp="testrun",
        force_offline=True,
    )
    history_lines = (
        (tmp_path / "testrun" / "attack_history.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )
    attempts = [json.loads(line) for line in history_lines]

    failed = [a for a in attempts if not a["success"]]
    succeeded = [a for a in attempts if a["success"]]
    assert failed, "应存在被拦截的失败尝试"
    assert all(a["reflection"] for a in failed), "失败尝试必须带反思"

    # 每个攻破的类别都应在经验库里
    breached = {e["category"] for e in result.campaign.experience_library}
    assert breached == set(a["category"] for a in succeeded)
    assert len(breached) == result.metrics["coverage_final"]


def test_coverage_table_covers_all_seven_threats(tmp_path: Path) -> None:
    run_comp2_demo(runs_root=tmp_path, timestamp="testrun", force_offline=True)
    payload = json.loads(
        (tmp_path / "testrun" / "coverage_table.json").read_text(encoding="utf-8")
    )
    rows = payload["rows"]
    assert {r["category"] for r in rows} == set(THREAT_CATEGORIES)
