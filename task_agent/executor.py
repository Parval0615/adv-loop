from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

from auto_defense_system.ecommerce_agent.models import ToolExecution
from auto_defense_system.ecommerce_agent.store import EcommerceStore

import task_agent.tool_registry as tool_registry
from task_agent.models import Observation, PlanStep, TaskStep
from task_agent.prompts import (
    ARGUMENT_GENERATION_SYSTEM_PROMPT,
    EXECUTION_THOUGHT_SYSTEM_PROMPT,
)


ACTION_DECISION_SYSTEM_PROMPT = """You choose the ecommerce tool to execute for one plan step.
Choose exactly one tool from the provided choices. Do not invent tools."""


class Executor:
    def __init__(
        self,
        store: EcommerceStore,
        user_id: str,
        role: str,
        llm: Any,
        recorder: Any | None = None,
    ) -> None:
        self.store = store
        self.user_id = user_id
        self.role = role
        self.llm = llm
        self.recorder = recorder
        self._catalog = tool_registry.catalog_for_role(role)
        self._catalog_by_name = {entry["name"]: entry for entry in self._catalog}

    def run_step(self, step: PlanStep, history: Sequence[TaskStep]) -> TaskStep:
        thought = self._think(step, history)
        action_tool, action_args, decision_reason = self._decide_action(step, history)
        observation = self._observe(action_tool, action_args)
        task_step = TaskStep(
            plan_step_id=step.step_id,
            thought=thought,
            action_tool=action_tool,
            action_args=action_args,
            decision_reason=decision_reason,
            observation=observation,
        )
        self._record(task_step)
        return task_step

    def _think(self, step: PlanStep, history: Sequence[TaskStep]) -> str:
        result = self.llm.complete_json(
            EXECUTION_THOUGHT_SYSTEM_PROMPT,
            self._prompt_payload(
                {
                    "plan_step": step.to_dict(),
                    "history": self._history_payload(history),
                }
            ),
            schema_hint={
                "type": "object",
                "properties": {"thought": {"type": "string"}},
                "required": ["thought"],
            },
            seed=self._seed(step, offset=11),
            max_tokens=256,
        )
        thought = result.get("thought")
        if isinstance(thought, str) and thought.strip():
            return thought.strip()
        return f"Execute plan step {step.step_id} with {step.candidate_tool}."

    def _decide_action(
        self,
        step: PlanStep,
        history: Sequence[TaskStep],
    ) -> tuple[str, dict[str, Any], str]:
        choices = self._candidate_choices(step)
        decision = self.llm.decide(
            ACTION_DECISION_SYSTEM_PROMPT,
            self._prompt_payload(
                {
                    "plan_step": step.to_dict(),
                    "candidate_tools": choices,
                    "tool_catalog": [
                        entry for entry in self._catalog if entry["name"] in choices
                    ],
                    "history": self._history_payload(history),
                }
            ),
            choices=choices,
            seed=self._seed(step, offset=17),
        )
        action_tool = decision.get("choice")
        if not isinstance(action_tool, str) or action_tool not in choices:
            action_tool = choices[0]
        action_args = self._generate_args(action_tool, step, history)
        reason = decision.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = f"Selected {action_tool} for plan step {step.step_id}."
        return action_tool, action_args, reason

    def _observe(self, tool_name: str, args: dict[str, Any]) -> Observation:
        execution = tool_registry.invoke(
            tool_name,
            args,
            store=self.store,
            user_id=self.user_id,
            role=self.role,
        )
        return self._observation_from_execution(execution)

    def _generate_args(
        self,
        tool_name: str,
        step: PlanStep,
        history: Sequence[TaskStep],
    ) -> dict[str, Any]:
        tool_entry = self._catalog_by_name.get(tool_name)
        parameter_schema = {}
        if isinstance(tool_entry, dict):
            parameter_schema = tool_entry.get("parameters") or {}
        args_hint = dict(step.args_hint) if isinstance(step.args_hint, dict) else {}
        result = self.llm.complete_json(
            ARGUMENT_GENERATION_SYSTEM_PROMPT,
            self._prompt_payload(
                {
                    "selected_tool": tool_name,
                    "plan_step": step.to_dict(),
                    "args_hint": args_hint,
                    "parameter_schema": parameter_schema,
                    "history": self._history_payload(history),
                }
            ),
            schema_hint=parameter_schema,
            seed=self._seed(step, offset=23),
        )
        generated = self._extract_argument_object(result)
        args = self._filter_schema_args(generated, parameter_schema)
        args.update(self._filter_schema_args(args_hint, parameter_schema))
        args = self._coerce_schema_types(args, parameter_schema)
        return self._fill_required_defaults(tool_name, args, parameter_schema, history)

    def _candidate_choices(self, step: PlanStep) -> list[str]:
        candidate = step.candidate_tool.strip() if isinstance(step.candidate_tool, str) else ""
        if candidate in self._catalog_by_name:
            return [candidate]
        catalog_names = [entry["name"] for entry in self._catalog]
        if candidate:
            return [candidate]
        return catalog_names

    def _fill_required_defaults(
        self,
        tool_name: str,
        args: dict[str, Any],
        parameter_schema: dict[str, Any],
        history: Sequence[TaskStep],
    ) -> dict[str, Any]:
        filled = dict(args)
        for name in parameter_schema.get("required", []):
            if filled.get(name) is not None:
                continue
            default = self._default_argument(tool_name, name, filled, history)
            if default is not None:
                filled[name] = default
        if tool_name == "cart_add_item" and "quantity" not in filled:
            filled["quantity"] = 1
        return filled

    def _default_argument(
        self,
        tool_name: str,
        name: str,
        args: dict[str, Any],
        history: Sequence[TaskStep],
    ) -> Any:
        if name == "quantity":
            return 1
        if name == "query":
            return ""
        if name == "address_id":
            return self._first_address_id()
        if name == "message":
            return "请协助处理该订单问题。"
        if name == "reason":
            return "用户申请退款。"
        if name == "product_id":
            return self._first_product_id()
        if name == "coupon_id":
            return self._first_coupon_id()
        if name == "order_id":
            return self._recent_order_id(history)
        if name == "amount_cents" and tool_name == "mock_payment":
            order_id = args.get("order_id") or self._recent_order_id(history)
            if isinstance(order_id, str):
                try:
                    order = self.store.get_order(self.user_id, order_id)
                    return order.amount_cents
                except Exception:
                    return None
        if name == "new_price_cents":
            product_id = args.get("product_id") or self._first_product_id()
            if isinstance(product_id, str):
                try:
                    return self.store.get_product(product_id).price_cents
                except Exception:
                    return None
        if name == "new_stock":
            product_id = args.get("product_id") or self._first_product_id()
            if isinstance(product_id, str):
                try:
                    return self.store.get_product(product_id).stock
                except Exception:
                    return None
        return None

    def _first_address_id(self) -> str | None:
        try:
            user = self.store.get_user(self.user_id)
        except Exception:
            return None
        if not user.addresses:
            return None
        return user.addresses[0].address_id

    def _first_product_id(self) -> str | None:
        try:
            return next(iter(self.store.products))
        except StopIteration:
            return None

    def _first_coupon_id(self) -> str | None:
        for coupon in self.store.coupons.values():
            if coupon.owner_user_id in (None, self.user_id):
                return coupon.coupon_id
        return None

    def _recent_order_id(self, history: Sequence[TaskStep]) -> str | None:
        for item in reversed(history):
            value = item.observation.value
            order_id = self._field_from_value(value, "order_id")
            if isinstance(order_id, str):
                return order_id
        for order_id, order in reversed(list(self.store.orders.items())):
            if order.user_id == self.user_id:
                return order_id
        return None

    @staticmethod
    def _field_from_value(value: Any, name: str) -> Any:
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    @staticmethod
    def _extract_argument_object(result: Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            return {}
        for key in ("arguments", "args"):
            nested = result.get(key)
            if isinstance(nested, dict):
                return dict(nested)
        return dict(result)

    @staticmethod
    def _filter_schema_args(
        args: dict[str, Any],
        parameter_schema: dict[str, Any],
    ) -> dict[str, Any]:
        properties = parameter_schema.get("properties")
        if not isinstance(properties, dict) or not properties:
            return dict(args)
        return {key: value for key, value in args.items() if key in properties}

    @staticmethod
    def _coerce_schema_types(
        args: dict[str, Any],
        parameter_schema: dict[str, Any],
    ) -> dict[str, Any]:
        properties = parameter_schema.get("properties")
        if not isinstance(properties, dict):
            return args
        coerced = dict(args)
        for key, schema in properties.items():
            if key not in coerced or not isinstance(schema, dict):
                continue
            value = coerced[key]
            if schema.get("type") == "integer" and not isinstance(value, bool):
                try:
                    coerced[key] = int(value)
                except (TypeError, ValueError):
                    pass
            elif schema.get("type") == "string" and value is not None:
                coerced[key] = str(value)
        return coerced

    @staticmethod
    def _observation_from_execution(execution: ToolExecution) -> Observation:
        tool_calls = [call.to_dict() for call in execution.tool_calls]
        business_events = [event.to_dict() for event in execution.business_events]
        audit_events = [event.to_dict() for event in execution.audit_events]
        return Observation(
            answer=execution.answer,
            blocked=execution.blocked,
            risk_level=execution.risk_level,
            value=execution.value,
            summary={
                "tool": tool_calls[0]["tool_name"] if tool_calls else "",
                "tool_calls": tool_calls,
                "business_events": business_events,
                "audit_events": audit_events,
            },
        )

    @staticmethod
    def _history_payload(history: Sequence[TaskStep]) -> list[dict[str, Any]]:
        return [item.to_dict() for item in history]

    @staticmethod
    def _prompt_payload(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=_json_default)

    @staticmethod
    def _seed(step: PlanStep, *, offset: int) -> int:
        return sum(ord(char) for char in step.step_id) + offset

    def _record(self, task_step: TaskStep) -> None:
        if self.recorder is None:
            return
        if hasattr(self.recorder, "record_step"):
            self.recorder.record_step(task_step)
            return
        if hasattr(self.recorder, "record"):
            self.recorder.record(task_step)
            return
        if hasattr(self.recorder, "append"):
            self.recorder.append(task_step)
            return
        if callable(self.recorder):
            self.recorder(task_step)


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return str(value)


__all__ = ["Executor"]
