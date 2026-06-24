"""Attack Agent —— 攻击历史 / 失败反思 / 重规划。

闭环（单个威胁类别）：
    规划(plan) → 执行(execute) → 命中? → 是: 记入经验库 / 否: 反思(reflect) → 重规划(replan)

整体战役 ``run_attack_campaign`` 在 7 类威胁上迭代：
    1. 每轮对所有"尚未攻破"的类别发起当前成熟度的攻击；
    2. 失败的类别触发 reflection，把攻击成熟度沿 escalation ladder 升级；
    3. 成功的类别沉淀进 *攻击经验库*（attack memory），不再重复攻击；
    4. 覆盖率 = 已攻破类别 / 7，随反思迭代单调上升。

LLM 用法：攻击规划话术(rationale)由共享 LLM 客户端生成；是否突破由确定性
靶场判定，因此即使离线（无 API key）整条收敛曲线也完全可复现。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_attack_system.llm_client import SharedLLMClient
from auto_attack_system.threat_taxonomy import (
    THREAT_CATEGORIES,
    AttackStrategy,
    SyntheticTarget,
    ladder_for,
)


@dataclass
class AttackAttempt:
    """单次攻击尝试的完整记录（写入 attack_history）。"""

    round_index: int
    category: str
    category_cn: str
    ladder_index: int
    strategy: str
    intensity: str
    technique: str
    payload: str
    rationale: str
    success: bool
    blocked: bool
    target_reason: str
    reflection: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReflectionEntry:
    """一次失败反思的记录（写入 reflection_log）。"""

    round_index: int
    category: str
    category_cn: str
    failed_strategy: str
    failed_ladder_index: int
    diagnosis: str
    next_strategy: str | None
    next_ladder_index: int | None
    escalated: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignResult:
    attempts: list[AttackAttempt]
    reflections: list[ReflectionEntry]
    coverage_timeline: list[dict[str, Any]]
    breached_categories: list[str]
    experience_library: list[dict[str, Any]]
    rounds: int
    llm_mode: str

    @property
    def coverage_count(self) -> int:
        return len(self.breached_categories)

    @property
    def coverage_rate(self) -> float:
        return self.coverage_count / len(THREAT_CATEGORIES)


class AttackAgent:
    """带攻击历史、失败反思与重规划能力的攻击 Agent。"""

    def __init__(
        self,
        target: SyntheticTarget | None = None,
        llm: SharedLLMClient | None = None,
        *,
        categories: list[str] | None = None,
        max_rounds: int = 6,
        disable_reflection: bool = False,
    ) -> None:
        self.target = target or SyntheticTarget()
        self.llm = llm or SharedLLMClient()
        self.categories = categories or list(THREAT_CATEGORIES.keys())
        self.max_rounds = max_rounds
        # 消融开关：关闭反思 -> 攻击不升级（覆盖率停滞，用于证明反思贡献）。
        self.disable_reflection = disable_reflection

        # 状态
        self._maturity: dict[str, int] = {c: 0 for c in self.categories}
        self._breached: set[str] = set()
        self._experience: list[dict[str, Any]] = []
        self.attempts: list[AttackAttempt] = []
        self.reflections: list[ReflectionEntry] = []
        self.coverage_timeline: list[dict[str, Any]] = []

    # -- 规划 -----------------------------------------------------------
    def _plan(self, category: str, strategy: AttackStrategy, round_index: int) -> str:
        """用 LLM 生成攻击话术(rationale)；离线时为确定性合成文本。"""
        system = (
            "你是红队攻击规划器，只在本地合成电商靶场上工作。"
            "给定威胁类别和攻击手法，用一句话说明此次攻击的意图与预期突破点。"
        )
        user = (
            f"威胁类别：{THREAT_CATEGORIES[category]}({category})\n"
            f"攻击手法：{strategy.name} / 强度 {strategy.intensity}\n"
            f"机理：{strategy.technique}\n"
            f"合成样本：{strategy.sample_payload}\n"
            f"这是第 {round_index} 轮。请输出攻击意图。"
        )
        rationale = self.llm.complete(system, user, seed=round_index * 100 + len(category))
        return rationale.strip()

    # -- 反思 -----------------------------------------------------------
    def _reflect(
        self, category: str, strategy: AttackStrategy, ladder_index: int, round_index: int
    ) -> ReflectionEntry:
        """失败后反思：沿 ladder 升级到下一更强手法。"""
        ladder = ladder_for(category)
        next_index = ladder_index + 1
        has_next = next_index < len(ladder)
        next_strategy = ladder[next_index].name if has_next else None
        # 消融：关闭反思时不升级（攻击停在初始手法，覆盖率停滞）。
        will_escalate = has_next and not self.disable_reflection

        system = (
            "你是红队反思器。攻击失败后，诊断原因并决定是否升级到更强手法。"
        )
        user = (
            f"威胁类别：{THREAT_CATEGORIES[category]}\n"
            f"失败手法：{strategy.name}(L{ladder_index})，被靶场拦截。\n"
            f"是否还有更强手法：{'有 → ' + (next_strategy or '') if has_next else '无'}\n"
            "请用一句话给出诊断。"
        )
        diagnosis = self.llm.complete(
            system, user, seed=round_index * 200 + ladder_index
        ).strip()

        if will_escalate:
            self._maturity[category] = next_index

        return ReflectionEntry(
            round_index=round_index,
            category=category,
            category_cn=THREAT_CATEGORIES[category],
            failed_strategy=strategy.name,
            failed_ladder_index=ladder_index,
            diagnosis=diagnosis,
            next_strategy=next_strategy if will_escalate else None,
            next_ladder_index=next_index if will_escalate else None,
            escalated=will_escalate,
        )

    # -- 执行一轮 -------------------------------------------------------
    def _run_round(self, round_index: int) -> None:
        for category in self.categories:
            if category in self._breached:
                continue  # 已攻破，经验库已沉淀，跳过

            ladder = ladder_for(category)
            ladder_index = self._maturity[category]
            if ladder_index >= len(ladder):
                continue  # 手法已用尽仍未突破

            strategy = ladder[ladder_index]
            rationale = self._plan(category, strategy, round_index)
            response = self.target.attempt(category, ladder_index)

            attempt = AttackAttempt(
                round_index=round_index,
                category=category,
                category_cn=THREAT_CATEGORIES[category],
                ladder_index=ladder_index,
                strategy=strategy.name,
                intensity=strategy.intensity,
                technique=strategy.technique,
                payload=strategy.sample_payload,
                rationale=rationale,
                success=response.success,
                blocked=response.blocked,
                target_reason=response.reason,
            )

            if response.success:
                self._breached.add(category)
                self._experience.append(
                    {
                        "category": category,
                        "category_cn": THREAT_CATEGORIES[category],
                        "winning_strategy": strategy.name,
                        "intensity": strategy.intensity,
                        "ladder_index": ladder_index,
                        "payload": strategy.sample_payload,
                        "round_breached": round_index,
                    }
                )
            else:
                reflection = self._reflect(category, strategy, ladder_index, round_index)
                attempt.reflection = reflection.diagnosis
                self.reflections.append(reflection)

            self.attempts.append(attempt)

        self.coverage_timeline.append(
            {
                "round": round_index,
                "breached_count": len(self._breached),
                "coverage_rate": round(len(self._breached) / len(THREAT_CATEGORIES), 4),
                "breached_categories": sorted(self._breached),
            }
        )

    # -- 战役入口 -------------------------------------------------------
    def run(self) -> CampaignResult:
        for round_index in range(1, self.max_rounds + 1):
            self._run_round(round_index)
            if len(self._breached) == len(self.categories):
                break
            # 若没有任何类别还能升级，则收敛终止
            if all(
                category in self._breached
                or self._maturity[category] >= len(ladder_for(category))
                for category in self.categories
            ):
                break

        return CampaignResult(
            attempts=self.attempts,
            reflections=self.reflections,
            coverage_timeline=self.coverage_timeline,
            breached_categories=sorted(self._breached),
            experience_library=self._experience,
            rounds=self.coverage_timeline[-1]["round"] if self.coverage_timeline else 0,
            llm_mode=self.llm.mode,
        )


__all__ = [
    "AttackAttempt",
    "ReflectionEntry",
    "CampaignResult",
    "AttackAgent",
]
