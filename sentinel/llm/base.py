from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

PRICES_PER_MTOK = {  # USD, update as vendors change them
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "scripted-v1": (0.0, 0.0),
}


@dataclass
class LLMResponse:
    text: str
    payload: dict[str, Any] | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    provider: str = "scripted"
    model: str = "scripted-v1"
    tag: str = ""
    cached: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "tag": self.tag, "provider": self.provider, "model": self.model,
            "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
            "cost_usd": round(self.cost_usd, 6), "cached": self.cached,
            "text": self.text[:600] + ("..." if len(self.text) > 600 else ""),
        }


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def price(model: str, tokens_in: int, tokens_out: int) -> float:
    pin, pout = PRICES_PER_MTOK.get(model, (0.0, 0.0))
    return tokens_in / 1e6 * pin + tokens_out / 1e6 * pout


def prompt_key(system: str, user: str, tag: str, model: str) -> str:
    blob = json.dumps([system, user, tag, model], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


class BaseLLM:
    provider = "base"
    model = "base"

    def __init__(self) -> None:
        self.calls: list[LLMResponse] = []

    def complete(self, system: str, user: str, *, tag: str = "",
                 payload: dict[str, Any] | None = None) -> LLMResponse:
        raise NotImplementedError

    @property
    def total_cost(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def total_tokens(self) -> tuple[int, int]:
        return sum(c.tokens_in for c in self.calls), sum(c.tokens_out for c in self.calls)
