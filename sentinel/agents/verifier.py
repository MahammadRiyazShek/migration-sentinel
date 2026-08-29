"""Agent 5 - Verifier: the plan does not count as safe until it is replayed.

The Rollout Engineer writes SQL.  The Verifier parses that SQL with the same
parser, applies it to the same schema model and replays the same query corpus.
If anything still breaks, the failure text is handed back to the engineer as
feedback and the plan is regenerated with a tightened policy.  After
`max_attempts` the run stops and escalates to a human instead of shipping a plan
it cannot prove.
"""
from __future__ import annotations

from typing import Any

from .base import Agent
from ..tools.sql_parse import Schema


class Verifier(Agent):
    NAME = "verifier"
    GOAL = ("Prove that phase 1 of the plan breaks nothing the application does today, or hand back "
            "the exact failure that stops it.")

    def run(self, case: dict[str, Any], parsed: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        schema: Schema = parsed["schema"]
        script = "\n".join(s for s in plan["phase1_sql"] if not s.strip().startswith("--"))
        self.start({"case": case["id"], "attempt": plan["attempt"],
                    "phase1_statements": len(plan["phase1_sql"])})
        ops = self.tool("migration.parse", sql=script)
        post, notes = self.tool("schema.apply_ops", schema=schema, ops=ops)
        replay = self.tool("shadow.replay", pre_schema=schema, post_schema=post, ops=ops,
                           seed=case.get("seed", {}), queries=case["queries"])
        problems = [f"{b['query_id']} ({b['service']}): {b['error']}" for b in replay.broken]
        problems += [f"{d['query_id']} ({d['service']}): column set changed, removed {d['removed']}"
                     for d in replay.column_drift if d["removed"]]
        problems += [f"phase-1 data step failed: {e}" for e in replay.data_errors]
        verified = not problems
        result = {"verified": verified, "problems": problems, "replay": replay.to_json(),
                  "unmodelled": notes}
        self.end(result)
        return result
