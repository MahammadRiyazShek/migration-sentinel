"""Tool registry with call logging, so every trajectory shows the real I/O."""
from __future__ import annotations

import time
from typing import Any, Callable


class ToolRegistry:
    def __init__(self, tracer=None):
        self._tools: dict[str, Callable[..., Any]] = {}
        self.docs: dict[str, str] = {}
        self.tracer = tracer
        self.calls: list[dict[str, Any]] = []

    def register(self, name: str, fn: Callable[..., Any], description: str = "") -> None:
        self._tools[name] = fn
        self.docs[name] = description or (fn.__doc__ or "").strip().splitlines()[0] if (description or fn.__doc__) else ""

    def names(self) -> list[str]:
        return sorted(self._tools)

    def call(self, name: str, agent: str, **kwargs: Any) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        started = time.perf_counter()
        result = self._tools[name](**kwargs)
        entry = {
            "agent": agent, "tool": name, "args": {k: _short(v) for k, v in kwargs.items()},
            "ms": round((time.perf_counter() - started) * 1000, 2),
            "result_summary": _short(result),
        }
        self.calls.append(entry)
        if self.tracer:
            self.tracer.tool_call(**entry)
        return result


def _short(value: Any, limit: int = 400) -> Any:
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "..."
    if isinstance(value, dict):
        return {k: _short(v, 120) for k, v in list(value.items())[:12]}
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        return [_short(v, 120) for v in items[:8]] + ([f"...+{len(items)-8} more"] if len(items) > 8 else [])
    summarise = getattr(value, "to_json", None)
    if callable(summarise):
        return _short(summarise(), limit)
    return type(value).__name__
