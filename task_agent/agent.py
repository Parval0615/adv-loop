from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

from auto_attack_system.llm_client import SharedLLMClient
from auto_defense_system.ecommerce_agent.fixtures import create_demo_store
from auto_defense_system.ecommerce_agent.store import EcommerceStore

from task_agent.executor import Executor
from task_agent.models import Plan, PlanStep, TaskRunResult, TaskSpec, TaskStep
from task_agent.planner import make_plan, parse_task
from task_agent.prompts import GOAL_JUDGE_SYSTEM_PROMPT
from task_agent.replanner import replan, should_replan


class TaskAgent:
    def __init__(
        self,
        *,
        store: EcommerceStore | None = None,
        user_id: str = "buyer_001",
        role: str = "buyer",
        force_offline: bool = False,
        llm: Any | None = None,
    ) -> None:
        self.store = store or create_demo_store()
        self.user_id = user_id
        self.role = role
        self.force_offline = force_offline
        self.llm = llm or SharedLLMClient(force_offline=force_offline)

    def run(
        self,
        instruction: str,
        *,
        max_steps: int = 12,
        max_replans: int = 3,
    ) -> TaskRunResult:
        step_limit = _non_negative_int(max_steps, default=12)
        replan_limit = _non_negative_int(max_replans, default=3)

        task_spec = parse_task(instruction, self.llm)
        current_plan = make_plan(task_spec, self.role, self.llm)
        current_plan = self._stabilize_offline_plan(task_spec, current_plan)
        plans = [current_plan]
        trace: list[TaskStep] = []
        replan_count = 0
        stopped_reason = ""

        executor = Executor(
            store=self.store,
            user_id=self.user_id,
            role=self.role,
            llm=self.llm,
        )

        while len(trace) < step_limit:
            if not current_plan.steps:
                stopped_reason = "当前计划没有可执行步骤。"
                break

            replanned = False
            for plan_step in current_plan.steps:
                if len(trace) >= step_limit:
                    stopped_reason = f"达到 max_steps={step_limit}，停止继续执行。"
                    break

                task_step = executor.run_step(plan_step, trace)
                trace.append(task_step)

                triggered, failure = should_replan(task_step.observation, task_spec)
                if not triggered:
                    continue

                task_step.replan_triggered = True
                if len(trace) >= step_limit:
                    stopped_reason = f"达到 max_steps={step_limit}，无法继续重规划执行。"
                    break
                if replan_count >= replan_limit:
                    stopped_reason = f"达到 max_replans={replan_limit}，停止重规划。"
                    break

                failure_payload = {
                    "reason": failure,
                    "failed_step": task_step.to_dict(),
                }
                current_plan = replan(
                    task_spec,
                    history=[*plans, *trace],
                    failure=failure_payload,
                    role=self.role,
                    llm=self.llm,
                )
                current_plan = self._stabilize_offline_replan(
                    task_spec,
                    current_plan,
                    failure_payload,
                )
                plans.append(current_plan)
                replan_count += 1
                replanned = True
                break

            if replanned:
                continue
            break

        if step_limit == 0 and not stopped_reason:
            stopped_reason = "达到 max_steps=0，未执行工具步骤。"

        final_answer = self._summarize_result(
            task_spec,
            plans,
            trace,
            replan_count=replan_count,
            stopped_reason=stopped_reason,
        )
        goal_achieved = self._verify_goal(task_spec, plans, trace, final_answer)

        return TaskRunResult(
            task_spec=task_spec,
            plans=plans,
            trace=trace,
            final_answer=final_answer,
            goal_achieved=goal_achieved,
            replan_count=replan_count,
            llm_mode=getattr(self.llm, "mode", "unknown"),
        )

    def _summarize_result(
        self,
        task_spec: TaskSpec,
        plans: Sequence[Plan],
        trace: Sequence[TaskStep],
        *,
        replan_count: int,
        stopped_reason: str = "",
    ) -> str:
        if not trace:
            pieces = [
                f"任务目标：{task_spec.goal}",
                f"已生成 {len(plans)} 个计划版本，但没有执行工具步骤。",
            ]
            if stopped_reason:
                pieces.append(stopped_reason)
            return " ".join(pieces)

        successful_tools = [
            step.action_tool for step in trace if not step.observation.blocked
        ]
        failed_steps = [step for step in trace if step.observation.blocked]
        last_answer = _clean_text(trace[-1].observation.answer)
        pieces = [
            f"任务目标：{task_spec.goal}",
            f"已执行 {len(trace)} 个工具步骤，生成 {len(plans)} 个计划版本，重规划 {replan_count} 次。",
        ]
        if successful_tools:
            pieces.append(f"成功工具：{', '.join(successful_tools)}。")
        if failed_steps:
            pieces.append(f"失败或拦截：{_clean_text(failed_steps[-1].observation.answer)}")
        if last_answer:
            pieces.append(f"最新结果：{last_answer}")
        state = self._user_state_summary()
        if state:
            pieces.append(state)
        if stopped_reason:
            pieces.append(stopped_reason)
        return " ".join(piece for piece in pieces if piece)

    def _verify_goal(
        self,
        task_spec: TaskSpec,
        plans: Sequence[Plan],
        trace: Sequence[TaskStep],
        final_answer: str,
    ) -> bool:
        state_result = self._verify_goal_from_state(task_spec, trace)
        if state_result is not None:
            return state_result

        try:
            judge = self.llm.complete_json(
                GOAL_JUDGE_SYSTEM_PROMPT,
                _json_dumps(
                    {
                        "task_spec": task_spec.to_dict(),
                        "store_evidence": self._store_evidence(),
                        "plans": [plan.to_dict() for plan in plans],
                        "trace": [step.to_dict() for step in trace],
                        "final_answer": final_answer,
                    }
                ),
                schema_hint={
                    "type": "object",
                    "required": ["goal_achieved", "reason"],
                    "properties": {
                        "goal_achieved": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                },
                seed=101,
                max_tokens=512,
            )
        except Exception:
            return False
        return judge.get("goal_achieved") is True

    def _stabilize_offline_plan(self, task_spec: TaskSpec, plan: Plan) -> Plan:
        if not self._uses_deterministic_fallback(task_spec):
            return plan

        goal_text = _goal_text(task_spec)
        wants_order_status = _has_any(goal_text, ("订单状态", "物流", "order status"))
        wants_refund = _has_any(goal_text, ("退款", "退货", "refund"))
        wants_support = _has_any(goal_text, ("客服", "工单", "ticket", "support"))
        wants_payment = _has_any(goal_text, ("支付", "付款", "pay"))
        wants_order = _has_any(goal_text, ("下单", "购买", "买", "订购", "order", "purchase"))
        wants_cart = _has_any(goal_text, ("购物车", "加购", "加入购物车", "cart"))
        wants_search = _has_any(goal_text, ("搜索", "查找", "找", "详情", "商品", "search", "find"))

        steps: list[PlanStep] = []
        if wants_order_status:
            order_id = self._latest_user_order_id()
            if order_id:
                steps.append(
                    PlanStep(
                        step_id="offline-order-status",
                        candidate_tool="get_order_status",
                        args_hint={"order_id": order_id},
                    )
                )
        elif wants_refund:
            order_id = self._latest_user_order_id(statuses={"paid", "shipped"})
            if order_id:
                steps.append(
                    PlanStep(
                        step_id="offline-refund",
                        candidate_tool="request_refund",
                        args_hint={"order_id": order_id, "reason": "用户申请退款。"},
                    )
                )
        elif wants_support:
            steps.append(
                PlanStep(
                    step_id="offline-support",
                    candidate_tool="support_create_ticket",
                    args_hint={"message": task_spec.raw_instruction},
                )
            )
        elif wants_payment or wants_order or wants_cart:
            product_id = self._best_product_id(goal_text)
            query = _search_query(task_spec)
            steps.append(
                PlanStep(
                    step_id="offline-search",
                    candidate_tool="product_search",
                    args_hint={"query": query},
                )
            )
            if product_id:
                steps.append(
                    PlanStep(
                        step_id="offline-cart-add",
                        candidate_tool="cart_add_item",
                        args_hint={"product_id": product_id, "quantity": 1},
                    )
                )
            if wants_order or wants_payment:
                steps.append(
                    PlanStep(
                        step_id="offline-create-order",
                        candidate_tool="create_order",
                    )
                )
            if wants_payment:
                steps.append(
                    PlanStep(
                        step_id="offline-payment",
                        candidate_tool="mock_payment",
                    )
                )
        elif wants_search:
            query = _search_query(task_spec)
            steps.append(
                PlanStep(
                    step_id="offline-search",
                    candidate_tool="product_search",
                    args_hint={"query": query},
                )
            )

        return Plan(steps=steps, revision=plan.revision) if steps else plan

    def _stabilize_offline_replan(
        self,
        task_spec: TaskSpec,
        plan: Plan,
        failure: Any,
    ) -> Plan:
        if not self._uses_deterministic_fallback(task_spec):
            return plan

        failure_text = _failure_text(failure)
        if _has_any(failure_text, ("搜索无匹配", "没有找到匹配", "无匹配", "no match", "no results")):
            return self._offline_search_recovery_plan(task_spec, plan)
        if _has_any(failure_text, ("缺货", "库存不足", "stock_insufficient", "out of stock")):
            return self._offline_stock_recovery_plan(task_spec, plan, failure)

        stabilized = self._stabilize_offline_plan(task_spec, plan)
        if self._is_orderless_payment_plan(stabilized):
            return self._offline_support_plan(
                task_spec,
                stabilized.revision,
                "没有可支付订单，不能直接发起支付，请客服协助继续处理。",
            )
        return stabilized

    def _offline_search_recovery_plan(self, task_spec: TaskSpec, plan: Plan) -> Plan:
        goal_text = _goal_text(task_spec)
        wants_payment = _has_any(goal_text, ("支付", "付款", "pay"))
        wants_order = _has_any(goal_text, ("下单", "购买", "买", "订购", "order", "purchase"))
        wants_cart = _has_any(goal_text, ("购物车", "加购", "加入购物车", "cart"))

        query = _search_query(task_spec)
        product_id = self._best_product_id(goal_text)
        steps = [
            PlanStep(
                step_id="offline-replan-search",
                candidate_tool="product_search",
                args_hint={"query": query},
            )
        ]
        if product_id and (wants_cart or wants_order or wants_payment):
            steps.append(
                PlanStep(
                    step_id="offline-replan-cart-add",
                    candidate_tool="cart_add_item",
                    args_hint={"product_id": product_id, "quantity": 1},
                )
            )
        if product_id and (wants_order or wants_payment):
            steps.append(
                PlanStep(
                    step_id="offline-replan-create-order",
                    candidate_tool="create_order",
                )
            )
        if product_id and wants_payment:
            steps.append(
                PlanStep(
                    step_id="offline-replan-payment",
                    candidate_tool="mock_payment",
                )
            )
        return Plan(steps=steps, revision=plan.revision)

    def _offline_stock_recovery_plan(
        self,
        task_spec: TaskSpec,
        plan: Plan,
        failure: Any,
    ) -> Plan:
        goal_text = _goal_text(task_spec)
        wants_payment = _has_any(goal_text, ("支付", "付款", "pay"))
        wants_order = _has_any(goal_text, ("下单", "购买", "买", "订购", "order", "purchase"))
        failed_product_id = _nested_field_value(failure, "product_id")
        replacement_id = self._available_same_class_product_id(
            task_spec,
            str(failed_product_id) if failed_product_id else None,
        )
        if not replacement_id:
            return self._offline_support_plan(
                task_spec,
                plan.revision,
                "目标商品缺货，未找到有货同类商品，请客服协助处理。",
            )

        query = replacement_id
        steps = []
        if query:
            steps.append(
                PlanStep(
                    step_id="offline-replan-search",
                    candidate_tool="product_search",
                    args_hint={"query": query},
                )
            )
        steps.append(
            PlanStep(
                step_id="offline-replan-cart-add",
                candidate_tool="cart_add_item",
                args_hint={"product_id": replacement_id, "quantity": 1},
            )
        )
        if wants_order or wants_payment:
            steps.append(
                PlanStep(
                    step_id="offline-replan-create-order",
                    candidate_tool="create_order",
                )
            )
        if wants_payment:
            steps.append(
                PlanStep(
                    step_id="offline-replan-payment",
                    candidate_tool="mock_payment",
                )
            )
        return Plan(steps=steps, revision=plan.revision)

    def _offline_support_plan(
        self,
        task_spec: TaskSpec,
        revision: int,
        message: str,
    ) -> Plan:
        return Plan(
            steps=[
                PlanStep(
                    step_id="offline-replan-support",
                    candidate_tool="support_create_ticket",
                    args_hint={"message": f"{message} 原始需求：{task_spec.raw_instruction}"},
                )
            ],
            revision=revision,
        )

    def _is_orderless_payment_plan(self, plan: Plan) -> bool:
        tools = [step.candidate_tool for step in plan.steps]
        if tools != ["mock_payment"]:
            return False
        return self._latest_user_order_id(statuses={"pending_payment"}) is None

    def _available_same_class_product_id(
        self,
        task_spec: TaskSpec,
        failed_product_id: str | None,
    ) -> str | None:
        failed_product = self.store.products.get(failed_product_id) if failed_product_id else None
        query = _search_query(task_spec)
        candidates = []
        for product in self.store.products.values():
            product_id = _field_value(product, "product_id")
            if not product_id or str(product_id) == failed_product_id:
                continue
            if int(_field_value(product, "stock") or 0) <= 0:
                continue
            if failed_product is not None and not _same_product_class(product, failed_product):
                continue
            score = _product_match_score(product, query)
            if failed_product is None and score <= 0:
                continue
            candidates.append(
                (
                    -score,
                    -int(_field_value(product, "sold") or 0),
                    int(_field_value(product, "price_cents") or 0),
                    str(product_id),
                )
            )
        if not candidates:
            return None
        return sorted(candidates)[0][3]

    def _uses_deterministic_fallback(self, task_spec: TaskSpec) -> bool:
        return bool(getattr(self.llm, "offline", False)) or task_spec.parse_mode == "deterministic-offline"

    def _verify_goal_from_state(
        self,
        task_spec: TaskSpec,
        trace: Sequence[TaskStep],
    ) -> bool | None:
        if not trace:
            return False

        goal_text = _goal_text(task_spec)
        user_orders = self._user_orders()
        paid_orders = [
            order
            for order in user_orders
            if _field_value(order, "payment_id")
            and _field_value(order, "status") in {"paid", "shipped", "refund_requested"}
        ]
        user_order_ids = {
            str(order_id)
            for order in user_orders
            if (order_id := _field_value(order, "order_id"))
        }
        refunds = [
            refund
            for refund in self.store.refunds.values()
            if _field_value(refund, "order_id") in user_order_ids
        ]
        tickets = [
            ticket
            for ticket in self.store.tickets.values()
            if _field_value(ticket, "user_id") == self.user_id
        ]
        cart_items = self._safe_cart_items()
        successful_tools = {
            step.action_tool for step in trace if not step.observation.blocked
        }

        wants_order_status = _has_any(goal_text, ("订单状态", "物流", "order status"))
        wants_refund = _has_any(goal_text, ("退款", "退货", "refund"))
        wants_support = _has_any(goal_text, ("客服", "工单", "ticket", "support"))
        wants_payment = _has_any(goal_text, ("支付", "付款", "pay"))
        wants_order = _has_any(goal_text, ("下单", "购买", "买", "订购", "order", "purchase"))
        wants_cart = _has_any(goal_text, ("购物车", "加购", "加入购物车", "cart"))
        wants_search = _has_any(goal_text, ("搜索", "查找", "找", "详情", "商品", "search", "find"))

        checks: list[bool] = []
        if wants_order_status:
            checks.append("get_order_status" in successful_tools)
        if wants_refund:
            checks.append(bool(refunds) or "request_refund" in successful_tools)
        if wants_support:
            checks.append(bool(tickets) or "support_create_ticket" in successful_tools)
        if wants_payment:
            checks.append(bool(paid_orders) or "mock_payment" in successful_tools)
        elif wants_order:
            checks.append(bool(user_orders) or "create_order" in successful_tools)
        elif wants_cart:
            checks.append(bool(cart_items) or "cart_add_item" in successful_tools)
        elif wants_search:
            checks.append(self._has_successful_search_or_detail(trace))

        if checks:
            return all(checks)
        if all(step.observation.blocked for step in trace):
            return False
        return None

    def _has_successful_search_or_detail(self, trace: Sequence[TaskStep]) -> bool:
        for step in trace:
            if step.observation.blocked:
                continue
            if step.action_tool not in {"product_search", "get_product_detail"}:
                continue
            value = step.observation.value
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                if len(value) > 0:
                    return True
                continue
            if value is not None:
                return True
        return False

    def _best_product_id(self, goal_text: str) -> str | None:
        products = sorted(
            self.store.products.values(),
            key=lambda product: (
                0 if _field_value(product, "stock") else 1,
                -int(_field_value(product, "sold") or 0),
                int(_field_value(product, "price_cents") or 0),
            ),
        )
        for product in products:
            if int(_field_value(product, "stock") or 0) <= 0:
                continue
            haystack = " ".join(
                _clean_text(_field_value(product, name)).lower()
                for name in ("product_id", "title", "category", "brand", "description")
            )
            if any(token and token in haystack for token in _goal_tokens(goal_text)):
                product_id = _field_value(product, "product_id")
                return str(product_id) if product_id else None
        for product in products:
            if int(_field_value(product, "stock") or 0) > 0:
                product_id = _field_value(product, "product_id")
                return str(product_id) if product_id else None
        return None

    def _latest_user_order_id(self, statuses: set[str] | None = None) -> str | None:
        for order in reversed(self._user_orders()):
            status = _field_value(order, "status")
            if statuses is not None and status not in statuses:
                continue
            order_id = _field_value(order, "order_id")
            if order_id:
                return str(order_id)
        return None

    def _user_state_summary(self) -> str:
        orders = self._user_orders()
        cart_items = self._safe_cart_items()
        pieces = []
        if cart_items:
            pieces.append(f"当前购物车 {len(cart_items)} 件商品")
        if orders:
            latest = orders[-1]
            order_id = _field_value(latest, "order_id")
            status = _field_value(latest, "status")
            pieces.append(f"最近订单 {order_id} 状态 {status}")
        if not pieces:
            return ""
        return "真实状态：" + "；".join(pieces) + "。"

    def _store_evidence(self) -> dict[str, Any]:
        user_orders = self._user_orders()
        user_order_ids = {
            str(order_id)
            for order in user_orders
            if (order_id := _field_value(order, "order_id"))
        }
        return {
            "user_id": self.user_id,
            "role": self.role,
            "cart_items": [_jsonable(item) for item in self._safe_cart_items()],
            "orders": [_jsonable(order) for order in user_orders],
            "payments": [
                _jsonable(payment)
                for payment in self.store.payments.values()
                if _field_value(payment, "order_id") in user_order_ids
            ],
            "refunds": [
                _jsonable(refund)
                for refund in self.store.refunds.values()
                if _field_value(refund, "order_id") in user_order_ids
            ],
            "tickets": [
                _jsonable(ticket)
                for ticket in self.store.tickets.values()
                if _field_value(ticket, "user_id") == self.user_id
            ],
        }

    def _user_orders(self) -> list[Any]:
        return [
            order
            for order in self.store.orders.values()
            if _field_value(order, "user_id") == self.user_id
        ]

    def _safe_cart_items(self) -> list[Any]:
        try:
            return self.store.cart_items(self.user_id)
        except Exception:
            return []


def _goal_text(task_spec: TaskSpec) -> str:
    parts = [
        task_spec.raw_instruction,
        task_spec.goal,
        *task_spec.subgoals,
    ]
    return " ".join(_clean_text(part).lower() for part in parts if _clean_text(part))


def _has_any(text: str, markers: Sequence[str]) -> bool:
    return any(marker.lower() in text for marker in markers)


def _failure_text(failure: Any) -> str:
    return _json_dumps(_jsonable(failure)).lower()


def _goal_tokens(text: str) -> list[str]:
    stop_words = {
        "把",
        "帮",
        "我",
        "请",
        "一个",
        "一件",
        "商品",
        "搜索",
        "查找",
        "购买",
        "下单",
        "支付",
        "加入",
        "购物车",
        "有货",
    }
    normalized = (
        text.replace("，", " ")
        .replace("。", " ")
        .replace(",", " ")
        .replace(".", " ")
        .replace("·", " ")
    )
    tokens = [token.strip().lower() for token in normalized.split() if token.strip()]
    return [token for token in tokens if token not in stop_words]


def _search_query(task_spec: TaskSpec) -> str:
    text = task_spec.raw_instruction or task_spec.goal
    text = re.sub(r"\d+\s*元\s*(?:以内|内)?", " ", text)
    text = re.sub(r"\d+\s*块(?:钱)?", " ", text)
    for marker in (
        "请",
        "帮我",
        "搜索",
        "查找",
        "找",
        "看看",
        "商品",
        "购买",
        "买",
        "下单",
        "支付",
        "付款",
        "加入购物车",
        "加购",
        "购物车",
        "元以内",
        "元内",
        "预算",
        "比价",
        "对比",
        "之后",
        "后",
        "以内",
        "块钱",
        "块",
        "一个",
        "一件",
    ):
        text = text.replace(marker, " ")
    query = " ".join(part for part in text.split() if part)
    return query or task_spec.raw_instruction


def _nested_field_value(value: Any, field_name: str) -> Any:
    if isinstance(value, Mapping):
        if field_name in value:
            return value[field_name]
        for nested in value.values():
            found = _nested_field_value(nested, field_name)
            if found is not None:
                return found
        return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            found = _nested_field_value(item, field_name)
            if found is not None:
                return found
        return None
    return getattr(value, field_name, None)


def _same_product_class(product: Any, reference: Any) -> bool:
    product_category = _clean_text(_field_value(product, "category")).lower()
    reference_category = _clean_text(_field_value(reference, "category")).lower()
    if product_category and product_category == reference_category:
        return True
    if len(reference_category) >= 2 and reference_category[-2:] in _product_text(product):
        return True
    return False


def _product_match_score(product: Any, query: str) -> int:
    query_text = _clean_text(query).lower()
    if not query_text:
        return 0
    haystack = _product_text(product)
    score = 0
    for token in query_text.split():
        if token in haystack:
            score += len(token) * 10
            continue
        score += sum(1 for gram in _text_ngrams(token) if gram in haystack)
    return score


def _text_ngrams(text: str, size: int = 2) -> list[str]:
    if len(text) < size:
        return [text] if text else []
    return [text[index : index + size] for index in range(len(text) - size + 1)]


def _product_text(product: Any) -> str:
    return " ".join(
        _clean_text(_field_value(product, name)).lower()
        for name in ("product_id", "title", "category", "brand", "description")
    )


def _field_value(value: Any, field_name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_jsonable(item) for item in value]
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _non_negative_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


__all__ = ["TaskAgent"]
