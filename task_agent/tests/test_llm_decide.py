from types import SimpleNamespace
from typing import Any

from auto_attack_system.llm_client import LLMConfig, SharedLLMClient


class FixedDecisionClient(SharedLLMClient):
    def __init__(self, payload: dict) -> None:
        super().__init__(force_offline=True)
        self.payload = payload

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint: Any,
        seed: int = 0,
        max_tokens: int = 1024,
    ) -> dict:
        return dict(self.payload)


class StubCompletions:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.calls: list[dict] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        content = self.outputs.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class StubOpenAIClient:
    def __init__(self, outputs: list[str]) -> None:
        self.completions = StubCompletions(outputs)
        self.chat = SimpleNamespace(completions=self.completions)


def test_decide_accepts_valid_choice() -> None:
    client = FixedDecisionClient({"choice": "refund_order", "reason": "matches"})

    result = client.decide(
        "choose a tool",
        "refund the order",
        choices=["search_products", "refund_order"],
    )

    assert result["choice"] == "refund_order"
    assert result["fallback_choice"] is False


def test_decide_falls_back_on_invalid_choice() -> None:
    client = FixedDecisionClient({"choice": "delete_database", "reason": "bad"})

    result = client.decide(
        "choose a tool",
        "refund the order",
        choices=["search_products", "refund_order"],
    )

    assert result["choice"] == "search_products"
    assert result["invalid_choice"] == "delete_database"
    assert result["fallback_choice"] is True


def test_complete_json_offline_is_deterministic_and_parseable() -> None:
    client = SharedLLMClient(force_offline=True)
    schema_hint = {"type": "object", "choices": ["search_products", "refund_order"]}

    first = client.complete_json("system", "user", schema_hint=schema_hint, seed=7)
    second = client.complete_json("system", "user", schema_hint=schema_hint, seed=7)
    third = client.complete_json("system", "user", schema_hint=schema_hint, seed=8)

    assert first == second
    assert first != third
    assert first["choice"] in schema_hint["choices"]
    assert first["mode"] == "deterministic-offline"


def test_complete_json_retries_bad_json_with_json_response_format() -> None:
    client = SharedLLMClient(
        config=LLMConfig(api_base="https://example.test/v1", api_key="key", model="m")
    )
    stub = StubOpenAIClient(["not json", '{"choice": "refund_order"}'])
    client._client = stub

    result = client.complete_json(
        "choose a tool",
        "refund the order",
        schema_hint={"type": "object", "choices": ["search_products", "refund_order"]},
        seed=11,
    )

    assert result == {"choice": "refund_order"}
    assert len(stub.completions.calls) == 2
    assert all(
        call["response_format"] == {"type": "json_object"}
        for call in stub.completions.calls
    )
