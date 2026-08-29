"""Agent 1 - Cartographer: turn text into an exact structural change set."""
from __future__ import annotations

from typing import Any

from .base import Agent


class Cartographer(Agent):
    NAME = "cartographer"
    GOAL = ("Convert the current schema DDL and the proposed migration into an exact, "
            "machine-checkable change set. Facts only, no risk opinions.")

    def run(self, case: dict[str, Any]) -> dict[str, Any]:
        self.start({"case": case["id"], "migration_statements": case["migration_sql"].count(";"),
                    "tables_declared": list(case.get("row_estimates", {}))})
        schema = self.tool("schema.parse", sql=case["schema_sql"],
                           row_estimates=case.get("row_estimates", {}))
        ops = self.tool("migration.parse", sql=case["migration_sql"])
        post, notes = self.tool("schema.apply_ops", schema=schema, ops=ops)
        change_set = {
            "ops": [o.to_json() for o in ops],
            "op_kinds": sorted({o.kind for o in ops}),
            "tables_touched": sorted({o.table for o in ops if o.table}),
            "columns_touched": sorted({f"{o.table}.{o.column}" for o in ops if o.column}),
            "unmodelled": notes,
        }
        if notes:
            self.tracer and self.tracer.note(self.NAME,
                "Some statements could not be modelled structurally; they are passed to the risk "
                "officer as unknowns rather than silently assumed safe.")
        self.end({"op_kinds": change_set["op_kinds"], "tables_touched": change_set["tables_touched"],
                  "unmodelled": notes})
        return {"schema": schema, "post_schema": post, "ops": ops, "change_set": change_set}
