"""Agent 1 - Cartographer: turn text into an exact structural change set.

v14: and then check the arithmetic. The change set is only as complete as the parse, and
the parse is a lossy function of the file - a `--` inside a string literal used to cost
this agent two thirds of a migration without a word of complaint. So the parse is now
reconciled against an independent lexical scan of the same text, and the remainder
travels on as a fact rather than as an absence. See `sentinel/tools/parse_audit.py`.
"""
from __future__ import annotations

from typing import Any

from .base import Agent


class Cartographer(Agent):
    NAME = "cartographer"
    GOAL = ("Convert the current schema DDL and the proposed migration into an exact, "
            "machine-checkable change set. Facts only, no risk opinions.")

    def run(self, case: dict[str, Any], text_conservation: bool = True) -> dict[str, Any]:
        self.start({"case": case["id"], "migration_statements": case["migration_sql"].count(";"),
                    "tables_declared": list(case.get("row_estimates", {}))})
        schema = self.tool("schema.parse", sql=case["schema_sql"],
                           row_estimates=case.get("row_estimates", {}))
        ops = self.tool("migration.parse", sql=case["migration_sql"])
        audit = self.tool("migration.audit", migration_sql=case["migration_sql"], ops=ops) \
            if text_conservation else None
        post, notes = self.tool("schema.apply_ops", schema=schema, ops=ops)
        change_set = {
            "ops": [o.to_json() for o in ops],
            "op_kinds": sorted({o.kind for o in ops}),
            "tables_touched": sorted({o.table for o in ops if o.table}),
            "columns_touched": sorted({f"{o.table}.{o.column}" for o in ops if o.column}),
            "unmodelled": notes,
        }
        if audit is not None and not audit["clean"]:
            self.tracer and self.tracer.note(
                self.NAME,
                f"parse conservation: the scanner finds {audit['lexed_statements']} statement(s) in "
                f"this file and the parse produced {audit['ops']} operation(s); "
                f"{len(audit['unterminated'])} unterminated construct(s), "
                f"{len(audit['unaccounted'])} statement(s) no operation accounts for, "
                f"{len(audit['procedural'])} procedural body/bodies. Reported as findings or "
                f"declared gaps rather than reviewed as a smaller migration.")
        if notes:
            self.tracer and self.tracer.note(self.NAME,
                "Some statements could not be modelled structurally; they are passed to the risk "
                "officer as unknowns rather than silently assumed safe.")
        self.end({"op_kinds": change_set["op_kinds"], "tables_touched": change_set["tables_touched"],
                  "unmodelled": notes})
        return {"schema": schema, "post_schema": post, "ops": ops, "change_set": change_set,
                "text_audit": audit}
