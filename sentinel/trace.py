"""Trajectory recorder.

Every agent step, tool call, model call, retry and human checkpoint lands here.
`render_markdown` produces the human-readable trajectory that ships in
trajectories/ - the point being that a reviewer can audit *why* the report says
what it says without reading Python.
"""
from __future__ import annotations

import json
import pathlib
import time
from typing import Any


class Tracer:
    def __init__(self, run_id: str, case_id: str = "", enabled: bool = True):
        self.run_id = run_id
        self.case_id = case_id
        self.enabled = enabled
        self.events: list[dict[str, Any]] = []
        self.t0 = time.perf_counter()

    def _add(self, kind: str, **fields: Any) -> None:
        if not self.enabled:
            return
        self.events.append({"seq": len(self.events) + 1, "t_ms": round((time.perf_counter() - self.t0) * 1000, 1),
                            "kind": kind, **fields})

    def agent_start(self, agent: str, goal: str, inputs: Any = None) -> None:
        self._add("agent_start", agent=agent, goal=goal, inputs=inputs)

    def agent_end(self, agent: str, output: Any = None) -> None:
        self._add("agent_end", agent=agent, output=output)

    def tool_call(self, agent: str, tool: str, args: Any, result_summary: Any, ms: float) -> None:
        self._add("tool_call", agent=agent, tool=tool, args=args, result=result_summary, ms=ms)

    def model_call(self, agent: str, response: Any) -> None:
        self._add("model_call", agent=agent, **(response.to_json() if hasattr(response, "to_json") else {"response": response}))

    def note(self, agent: str, text: str) -> None:
        self._add("note", agent=agent, text=text)

    def feedback(self, agent: str, text: str, attempt: int) -> None:
        self._add("feedback", agent=agent, text=text, attempt=attempt)

    def retry(self, agent: str, attempt: int, reason: str) -> None:
        self._add("retry", agent=agent, attempt=attempt, reason=reason)

    def checkpoint(self, name: str, state: str, detail: str = "") -> None:
        self._add("human_checkpoint", name=name, state=state, detail=detail)

    # -- output ------------------------------------------------------------
    def write_jsonl(self, path: str | pathlib.Path) -> pathlib.Path:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w") as fh:
            fh.write(json.dumps({"run_id": self.run_id, "case_id": self.case_id,
                                 "kind": "run_start"}) + "\n")
            for ev in self.events:
                fh.write(json.dumps(ev, sort_keys=True, default=str) + "\n")
        return p

    def render_markdown(self, title: str) -> str:
        lines = [f"# {title}", "",
                 f"- run id: `{self.run_id}`", f"- case: `{self.case_id}`",
                 f"- events: {len(self.events)}", ""]
        current = None
        for ev in self.events:
            kind = ev["kind"]
            if kind == "agent_start":
                current = ev["agent"]
                lines += [f"## Agent: {ev['agent']}", "",
                          f"**Goal** {ev['goal']}", ""]
                if ev.get("inputs"):
                    lines += ["<details><summary>inputs</summary>", "",
                              "```json", json.dumps(ev["inputs"], indent=1, default=str)[:2000], "```",
                              "", "</details>", ""]
            elif kind == "tool_call":
                lines += [f"**tool** `{ev['tool']}` ({ev['ms']} ms)", "",
                          "```json", json.dumps({"args": ev["args"]}, indent=1, default=str)[:1200], "```",
                          "", "_tool responded_", "",
                          "```json", json.dumps(ev["result"], indent=1, default=str)[:2000], "```", ""]
            elif kind == "model_call":
                lines += [f"**model** `{ev.get('model')}` tag=`{ev.get('tag')}` "
                          f"tokens={ev.get('tokens_in')}/{ev.get('tokens_out')} cost=${ev.get('cost_usd')}", "",
                          "> " + str(ev.get("text", "")).replace("\n", "\n> "), ""]
            elif kind == "feedback":
                lines += [f"**feedback into next step (attempt {ev['attempt']})** {ev['text']}", ""]
            elif kind == "retry":
                lines += [f"**RETRY {ev['attempt']}** because: {ev['reason']}", ""]
            elif kind == "human_checkpoint":
                lines += [f"### Human checkpoint - {ev['name']}: **{ev['state']}**", "",
                          ev.get("detail", ""), ""]
            elif kind == "note":
                lines += [f"_note ({ev.get('agent')})_: {ev['text']}", ""]
            elif kind == "agent_end":
                lines += ["**result**", "", "```json",
                          json.dumps(ev.get("output"), indent=1, default=str)[:2000], "```", ""]
        return "\n".join(lines)
