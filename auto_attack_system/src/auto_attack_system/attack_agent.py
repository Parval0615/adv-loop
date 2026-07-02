"""Attack Agent —— 攻击历史 / 失败反思 / 重规划。

闭环（单个威胁类别）：
    规划(plan) → 执行(execute) → 命中? → 是: 记入经验库 / 否: 反思(reflect) → 重规划(replan)

整体战役 ``run_attack_campaign`` 在 7 类威胁上迭代：
    1. 每轮对所有"尚未攻破"的类别发起当前成熟度的攻击；
    2. 失败的类别触发 reflection，把攻击成熟度沿 escalation ladder 升级；
    3. 成功的类别沉淀进 *攻击经验库*（attack memory），不再重复攻击；
    4. 覆盖率 = 已攻破类别 / 7，随反思迭代单调上升。

LLM 用法：攻击规划通过共享 LLM 客户端生成 JSON payload，失败反思通过
``decide()`` 从候选升级方向里选择；非法输出或异常时回退旧 ladder 行为，
保证整条收敛曲线可复现。
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


@dataclass(frozen=True)
class PlannedAttack:
    payload: str
    rationale: str


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
    def _plan(
        self,
        category: str,
        strategy: AttackStrategy,
        round_index: int,
        *,
        history: list[AttackAttempt] | None = None,
    ) -> PlannedAttack:
        """用 LLM JSON 生成下一条 payload；离线时回退到 ladder 样本。"""
        relevant_history = [
            {
                "round": attempt.round_index,
                "strategy": attempt.strategy,
                "payload": attempt.payload,
                "success": attempt.success,
                "blocked": attempt.blocked,
                "target_reason": attempt.target_reason,
            }
            for attempt in (history or self.attempts)
            if attempt.category == category
        ][-3:]
        candidate_payloads = [
            {
                "ladder_index": i,
                "name": item.name,
                "intensity": item.intensity,
                "technique": item.technique,
                "sample_payload": item.sample_payload,
            }
            for i, item in enumerate(ladder_for(category))
        ]
        system = (
            "你是红队攻击规划器，只在本地合成电商靶场上工作。"
            "给定威胁类别、历史失败信号和候选 payload，生成下一条合成 payload。"
            "只能输出 JSON 对象，不要生成真实世界攻击步骤。"
        )
        user = (
            f"威胁类别：{THREAT_CATEGORIES[category]}({category})\n"
            f"攻击手法：{strategy.name} / 强度 {strategy.intensity}\n"
            f"机理：{strategy.technique}\n"
            f"当前 ladder 样本：{strategy.sample_payload}\n"
            f"候选池：{json.dumps(candidate_payloads, ensure_ascii=False)}\n"
            f"历史：{json.dumps(relevant_history, ensure_ascii=False)}\n"
            f"这是第 {round_index} 轮。"
            "请返回 {payload, rationale, candidate_strategy}。"
        )
        try:
            result = self.llm.complete_json(
                system,
                user,
                schema_hint={
                    "type": "object",
                    "required": ["payload", "rationale"],
                    "properties": {
                        "payload": "string synthetic local payload",
                        "rationale": "string short intent",
                        "candidate_strategy": [c["name"] for c in candidate_payloads],
                    },
                },
                seed=round_index * 100 + len(category),
            )
        except Exception as exc:
            result = {"reason": f"complete_json failed: {type(exc).__name__}"}
        payload = result.get("payload")
        if (
            getattr(self.llm, "offline", False)
            or not isinstance(payload, str)
            or not payload.strip()
        ):
            payload = strategy.sample_payload
        rationale = result.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            rationale = str(result.get("reason") or "deterministic payload fallback")
        return PlannedAttack(payload=payload.strip(), rationale=rationale.strip())

    # -- 反思 -----------------------------------------------------------
    def _reflect(
        self, category: str, strategy: AttackStrategy, ladder_index: int, round_index: int
    ) -> ReflectionEntry:
        """失败后反思：由 LLM 从候选升级方向里选择下一步。"""
        ladder = ladder_for(category)
        next_index = ladder_index + 1
        has_next = next_index < len(ladder)
        legacy_next_strategy = ladder[next_index].name if has_next else None

        system = (
            "你是红队反思器。攻击失败后，诊断原因并决定是否升级到更强手法。"
        )
        user = (
            f"威胁类别：{THREAT_CATEGORIES[category]}\n"
            f"失败手法：{strategy.name}(L{ladder_index})，被靶场拦截。\n"
            f"是否还有更强手法：{'有 → ' + (legacy_next_strategy or '') if has_next else '无'}\n"
            "请用一句话给出诊断。"
        )
        try:
            diagnosis = self.llm.complete(
                system, user, seed=round_index * 200 + ladder_index
            ).strip()
        except Exception as exc:
            diagnosis = f"deterministic diagnosis fallback: {type(exc).__name__}"

        choices_to_index: dict[str, int | None] = {}
        if has_next and not self.disable_reflection:
            choices_to_index[
                f"escalate_to_L{next_index}:{legacy_next_strategy}"
            ] = next_index
            choices_to_index[f"retry_L{ladder_index}:{strategy.name}"] = ladder_index
        else:
            choices_to_index[f"retry_L{ladder_index}:{strategy.name}"] = ladder_index
            choices_to_index["stop:no_viable_escalation"] = None

        fallback_choice = next(iter(choices_to_index))
        try:
            decision = self.llm.decide(
                "你是红队升级决策器。基于失败诊断，从候选方向中选择下一步。",
                (
                    f"威胁类别：{THREAT_CATEGORIES[category]}({category})\n"
                    f"失败手法：{strategy.name}(L{ladder_index})\n"
                    f"失败诊断：{diagnosis}\n"
                    f"候选方向："
                    f"{json.dumps(list(choices_to_index), ensure_ascii=False)}"
                ),
                choices=list(choices_to_index),
                seed=round_index * 300 + ladder_index,
            )
        except Exception as exc:
            decision = {"choice": fallback_choice, "fallback_reason": type(exc).__name__}
        choice = decision.get("choice")
        if choice not in choices_to_index:
            choice = fallback_choice
        selected_index = choices_to_index[choice]
        will_escalate = (
            selected_index is not None
            and selected_index != ladder_index
            and not self.disable_reflection
        )
        if will_escalate:
            self._maturity[category] = selected_index

        return ReflectionEntry(
            round_index=round_index,
            category=category,
            category_cn=THREAT_CATEGORIES[category],
            failed_strategy=strategy.name,
            failed_ladder_index=ladder_index,
            diagnosis=diagnosis,
            next_strategy=ladder[selected_index].name if will_escalate else None,
            next_ladder_index=selected_index if will_escalate else None,
            escalated=will_escalate,
        )

    def _online_judge(self, context: dict[str, Any]) -> dict:
        """在线模式下让 LLM 裁判攻击结果；失败会由 SyntheticTarget 阈值兜底。"""
        return self.llm.complete_json(
            "你是本地合成电商靶场的在线裁判，只返回 JSON。",
            (
                "根据威胁类别、payload、ladder 成熟度和防御阈值判断是否突破。"
                f"\n上下文：{json.dumps(context, ensure_ascii=False)}"
            ),
            schema_hint={
                "type": "object",
                "required": ["success", "blocked", "reason", "defense_signal"],
                "properties": {
                    "success": "boolean",
                    "blocked": "boolean",
                    "reason": "string",
                    "defense_signal": ["bypassed", "blocked"],
                },
            },
            seed=int(context.get("ladder_index", 0)) * 1000
            + len(str(context.get("category", ""))),
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
            planned = self._plan(
                category, strategy, round_index, history=self.attempts
            )
            response = self.target.attempt(
                category,
                ladder_index,
                payload=planned.payload,
                online_judge=(
                    None if getattr(self.llm, "offline", False) else self._online_judge
                ),
            )

            attempt = AttackAttempt(
                round_index=round_index,
                category=category,
                category_cn=THREAT_CATEGORIES[category],
                ladder_index=ladder_index,
                strategy=strategy.name,
                intensity=strategy.intensity,
                technique=strategy.technique,
                payload=planned.payload,
                rationale=planned.rationale,
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
                        "payload": planned.payload,
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
    "PlannedAttack",
    "AttackAgent",
]
