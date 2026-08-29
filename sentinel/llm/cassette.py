"""Record/replay wrapper so a hosted-model run can be re-run offline, byte for byte."""
from __future__ import annotations

import json
import pathlib
from typing import Any

from .base import BaseLLM, LLMResponse, prompt_key


class CassetteLLM(BaseLLM):
    def __init__(self, inner: BaseLLM | None, path: str | pathlib.Path, mode: str = "replay"):
        super().__init__()
        self.inner = inner
        self.path = pathlib.Path(path)
        self.mode = mode
        self.provider = f"cassette:{inner.provider if inner else 'none'}"
        self.model = inner.model if inner else "cassette"
        self.store: dict[str, Any] = {}
        if self.path.exists():
            self.store = json.loads(self.path.read_text())

    def complete(self, system: str, user: str, *, tag: str = "",
                 payload: dict[str, Any] | None = None) -> LLMResponse:
        key = prompt_key(system, user, tag, self.model)
        if key in self.store and self.mode != "record":
            raw = self.store[key]
            resp = LLMResponse(text=raw["text"], payload=raw.get("payload"),
                               tokens_in=raw["tokens_in"], tokens_out=raw["tokens_out"],
                               cost_usd=0.0, provider=self.provider, model=self.model,
                               tag=tag, cached=True)
            self.calls.append(resp)
            return resp
        if self.inner is None:
            raise RuntimeError(f"cassette miss for tag={tag} and no live provider configured")
        resp = self.inner.complete(system, user, tag=tag, payload=payload)
        self.store[key] = {"text": resp.text, "payload": resp.payload,
                           "tokens_in": resp.tokens_in, "tokens_out": resp.tokens_out,
                           "tag": tag}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.store, indent=1, sort_keys=True))
        self.calls.append(resp)
        return resp
