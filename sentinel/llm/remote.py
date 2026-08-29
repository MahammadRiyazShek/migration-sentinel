"""Optional hosted-model providers, stdlib only (urllib), no SDK dependency.

Used when you pass --provider openai|anthropic and set the matching environment
variable.  Never required to reproduce the numbers in results/.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from ..hazards import HAZARDS, SEVERITY_ORDER
from .base import BaseLLM, LLMResponse, approx_tokens, price


def parse_review_text(text: str) -> dict[str, Any]:
    """Turn a free-text review into the shared hazard vocabulary."""
    hazards = []
    for code in HAZARDS:
        for m in re.finditer(rf"(?:\[(?P<sev>\w+)\]\s*)?{code}\b[:\-\s]*(?P<note>[^\n]*)", text):
            sev = (m.group("sev") or "").lower()
            if sev not in SEVERITY_ORDER:
                sev = HAZARDS[code]["default_severity"]
            hazards.append({"code": code, "severity": sev, "note": m.group("note").strip()})
            break
    verdict = "REQUEST_CHANGES" if re.search(r"request[_ ]changes|do not ship|block", text, re.I) else (
        "APPROVE" if re.search(r"\bapprove\b|safe to ship", text, re.I) else
        ("REQUEST_CHANGES" if hazards else "APPROVE"))
    return {"verdict": verdict, "hazards": hazards}


class RemoteLLM(BaseLLM):
    def __init__(self, provider: str, model: str, timeout: int = 60):
        super().__init__()
        self.provider = provider
        self.model = model
        self.timeout = timeout
        env = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        self.api_key = os.environ.get(env)
        if not self.api_key:
            raise RuntimeError(f"{env} is not set; use --provider scripted for the offline run")

    def _request(self, system: str, user: str) -> tuple[str, int, int]:
        if self.provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            body = {"model": self.model, "temperature": 0,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": user}]}
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        else:
            url = "https://api.anthropic.com/v1/messages"
            body = {"model": self.model, "max_tokens": 2048, "temperature": 0, "system": system,
                    "messages": [{"role": "user", "content": user}]}
            headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                       "Content-Type": "application/json"}
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        if self.provider == "openai":
            usage = data.get("usage", {})
            return (data["choices"][0]["message"]["content"],
                    usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        usage = data.get("usage", {})
        return ("".join(b.get("text", "") for b in data["content"]),
                usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    def complete(self, system: str, user: str, *, tag: str = "",
                 payload: dict[str, Any] | None = None) -> LLMResponse:
        text, tin, tout = self._request(system, user)
        tin = tin or approx_tokens(system + user)
        tout = tout or approx_tokens(text)
        out_payload = parse_review_text(text) if tag == "baseline_review" else {"text": text}
        resp = LLMResponse(text=text, payload=out_payload, tokens_in=tin, tokens_out=tout,
                           cost_usd=price(self.model, tin, tout), provider=self.provider,
                           model=self.model, tag=tag)
        self.calls.append(resp)
        return resp
