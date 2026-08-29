from __future__ import annotations

import pathlib
from typing import Any

PROMPT_DIR = pathlib.Path(__file__).parent / "prompts"


class Agent:
    NAME = "agent"
    GOAL = ""

    def __init__(self, tools, llm, tracer):
        self.tools = tools
        self.llm = llm
        self.tracer = tracer

    @property
    def instructions(self) -> str:
        path = PROMPT_DIR / f"{self.NAME}.md"
        return path.read_text() if path.exists() else ""

    def tool(self, name: str, **kwargs: Any) -> Any:
        return self.tools.call(name, self.NAME, **kwargs)

    def model(self, tag: str, payload: dict[str, Any], user: str) -> Any:
        resp = self.llm.complete(self.instructions, user, tag=tag, payload=payload)
        if self.tracer:
            self.tracer.model_call(self.NAME, resp)
        return resp

    def start(self, inputs: Any = None) -> None:
        if self.tracer:
            self.tracer.agent_start(self.NAME, self.GOAL, inputs)

    def end(self, output: Any = None) -> None:
        if self.tracer:
            self.tracer.agent_end(self.NAME, output)
