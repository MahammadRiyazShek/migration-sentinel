from __future__ import annotations

from .base import BaseLLM, LLMResponse
from .adversarial import HOSTILE
from .scripted import ScriptedLLM, baseline_hazards


def get_llm(provider: str = "scripted", model: str | None = None,
            cassette: str | None = None, cassette_mode: str = "replay") -> BaseLLM:
    if provider == "scripted":
        llm: BaseLLM = ScriptedLLM()
    elif provider in HOSTILE:
        # Deliberately unhelpful models, used to attack this project's own
        # model-invariance claim. See sentinel/llm/adversarial.py.
        llm = HOSTILE[provider]()
    else:
        from .remote import RemoteLLM
        default_model = "gpt-4.1-mini" if provider == "openai" else "claude-sonnet-4-5"
        llm = RemoteLLM(provider, model or default_model)
    if cassette:
        from .cassette import CassetteLLM
        llm = CassetteLLM(llm, cassette, cassette_mode)
    return llm


__all__ = ["get_llm", "BaseLLM", "LLMResponse", "ScriptedLLM", "baseline_hazards",
           "HOSTILE"]
