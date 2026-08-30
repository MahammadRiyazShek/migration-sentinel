"""Agent 3 - Risk Officer: the hazards execution cannot see, plus institutional memory.

Shadow replay is blind to three things: locks (SQLite has no MVCC), volume (the
fixtures are tiny) and intent (dropping a CHECK constraint breaks nothing today).
This agent covers exactly those, with explicit, auditable rules - and then lets
memory of past incidents raise, never lower, a severity.
"""
from __future__ import annotations

from typing import Any

from .. import coverage as coverage_tools
from ..hazards import Hazard, SEVERITY_ORDER, bump
from .base import Agent

LOCK_ROWS_WARN = 100_000
LOCK_ROWS_BLOCK = 5_000_000
DESTRUCTIVE = {"drop_column", "drop_table", "rename_column", "rename_table"}


def size_class(rows: int) -> str:
    if rows >= LOCK_ROWS_BLOCK:
        return "very large"
    if rows >= LOCK_ROWS_WARN:
        return "large"
    if rows >= 10_000:
        return "medium"
    return "small"


class RiskOfficer(Agent):
    NAME = "risk_officer"
    GOAL = ("Add lock, volume and intent hazards that execution cannot observe, weight every "
            "hazard by table size and past incidents, then issue a verdict.")

    def run(self, case: dict[str, Any], parsed: dict[str, Any], blast: dict[str, Any],
            use_static: bool = True, use_memory: bool = True,
            use_coverage: bool = True) -> dict[str, Any]:
        schema = parsed["schema"]
        rows_of = {t.name: t.row_estimate for t in schema.tables.values()}
        self.start({"case": case["id"], "row_estimates": rows_of,
                    "inherited_hazards": [h.code for h in blast["hazards"]]})
        hazards: list[Hazard] = list(blast["hazards"])

        for op in (parsed["ops"] if use_static else []):
            rows = rows_of.get(op.table or "", 0)
            klass = size_class(rows)
            if op.kind in DESTRUCTIVE:
                target = f"{op.table}.{op.column}" if op.column else op.table
                hazards.append(Hazard(
                    "DESTRUCTIVE_NO_EXPAND_CONTRACT", "high", source="static",
                    summary=f"{op.kind.replace('_', ' ')} on {target} lands in a single deploy",
                    evidence=[f"statement {op.index}: `{op.sql[:110]}`"], objects=[target]))
            if op.kind == "create_index" and not op.detail.get("concurrently"):
                sev = "high" if rows >= LOCK_ROWS_WARN else "medium"
                if rows >= LOCK_ROWS_BLOCK:
                    sev = "blocker"
                hazards.append(Hazard(
                    "INDEX_LOCK_NO_CONCURRENT", sev, source="static",
                    summary=(f"index {op.detail['name']} is built without CONCURRENTLY on "
                             f"{op.table} ({rows:,} rows, {klass})"),
                    evidence=[f"statement {op.index}: `{op.sql[:110]}`",
                              f"declared row estimate for {op.table}: {rows:,}"],
                    objects=[op.table]))
            if op.kind == "add_constraint" and not op.detail.get("not_valid") \
                    and op.detail.get("constraint_kind") in ("check", "foreign_key"):
                hazards.append(Hazard(
                    "CONSTRAINT_VALIDATION_LOCK", "high" if rows >= LOCK_ROWS_WARN else "medium",
                    source="static",
                    summary=(f"{op.detail['constraint']} is added without NOT VALID, so validation "
                             f"scans all {rows:,} rows under a lock"),
                    evidence=[f"statement {op.index}: `{op.sql[:110]}`"], objects=[op.table]))
            if op.kind == "maintenance_rewrite":
                cmd = op.detail.get("command", "maintenance")
                sev = "high" if rows >= LOCK_ROWS_WARN else "medium"
                hazards.append(Hazard(
                    "TABLE_REWRITE_LOCK", sev, source="static",
                    summary=(f"{cmd} rewrites {op.table or 'the relation'} under an ACCESS EXCLUSIVE "
                             f"lock ({rows:,} rows, {klass})"),
                    evidence=[f"statement {op.index}: `{op.sql[:110]}`",
                              f"declared row estimate for {op.table}: {rows:,}",
                              "recognised as a whole-relation maintenance command; the statement "
                              "itself is still not modelled structurally and stays in the coverage "
                              "ledger"],
                    objects=[op.table] if op.table else []))
            if op.kind == "alter_type":
                sev = "high" if rows >= LOCK_ROWS_WARN else "medium"
                hazards.append(Hazard(
                    "TABLE_REWRITE_LOCK", sev, source="static",
                    summary=(f"{op.table}.{op.column} -> {op.detail['new_type']} forces a rewrite of a "
                             f"{klass} table ({rows:,} rows)"),
                    evidence=[f"statement {op.index}: `{op.sql[:110]}`"],
                    objects=[f"{op.table}.{op.column}"]))
            if op.kind == "dml_update" and not op.detail.get("batched") and rows >= 10_000:
                hazards.append(Hazard(
                    "UNBATCHED_BACKFILL", "high" if rows >= LOCK_ROWS_WARN else "medium",
                    source="static",
                    summary=f"backfill on {op.table} runs as one statement over {rows:,} rows",
                    evidence=[f"statement {op.index}: `{op.sql[:110]}`"], objects=[op.table]))
            if op.kind == "set_not_null":
                hazards.append(Hazard(
                    "NOT_NULL_NO_DEFAULT", "high", source="static",
                    summary=f"SET NOT NULL on {op.table}.{op.column} validates every row under a lock",
                    evidence=[f"statement {op.index}: `{op.sql[:110]}`"],
                    objects=[f"{op.table}.{op.column}"]))
            if op.kind == "add_column" and op.detail.get("not_null") and not op.detail.get("default"):
                hazards.append(Hazard(
                    "NOT_NULL_NO_DEFAULT", "blocker", source="static",
                    summary=f"new column {op.table}.{op.column} is NOT NULL with no default",
                    evidence=[f"statement {op.index}: `{op.sql[:110]}`"],
                    objects=[f"{op.table}.{op.column}"]))
            if op.kind == "drop_constraint":
                table = schema.tables.get(op.table)
                con = next((c for c in (table.constraints if table else [])
                            if c.name == op.detail["constraint"]), None)
                kind = con.kind if con else "unknown"
                hazards.append(Hazard(
                    "INTEGRITY_CONSTRAINT_REMOVED", "high", source="static",
                    summary=(f"{op.detail['constraint']} ({kind}) is dropped from {op.table}; no query "
                             f"breaks today, invalid rows become possible tomorrow"),
                    evidence=[f"statement {op.index}: `{op.sql[:110]}`"]
                             + ([f"constraint text: {con.expr}"] if con else
                                ["constraint not found in current schema - verify the name"]),
                    objects=[op.table]))

        if use_static and not case.get("rollback_sql"):
            hazards.append(Hazard(
                "MISSING_ROLLBACK", "medium", source="static",
                summary="the change ships without a rollback script",
                evidence=["case field `rollback_sql` is empty"]))

        # cross-team coordination: only counts when something actually breaks there
        owner = case.get("owner_service")
        impacted = {s for h in blast["hazards"] for s in h.services
                    if s and s != owner and s != "database"
                    and h.code in ("BREAKING_QUERY", "SELECT_STAR_DRIFT", "VIEW_BREAKAGE")}
        if use_static and owner and impacted:
            hazards.append(Hazard(
                "CROSS_SERVICE_UNCOORDINATED", "high", source="static",
                summary=(f"the migration is owned by `{owner}` but breakage lands in "
                         f"{', '.join(sorted(impacted))}"),
                evidence=[f"corpus ownership of failing statements: {sorted(impacted)}"],
                services=sorted(impacted)))

        hazards = self._merge(hazards)
        if use_memory:
            hazards = self._apply_memory(hazards)
        counts = {s: sum(1 for h in hazards if h.severity == s) for s in SEVERITY_ORDER}
        verdict = "BLOCK" if counts["blocker"] else ("SAFE_WITH_PLAN" if counts["high"] else "SAFE")

        # v2: a declared blind spot now constrains the verdict instead of sitting
        # in an appendix underneath a clean badge.  Facts from a tool, as always.
        cov = self.tool("coverage.ledger", ops=parsed["ops"], schema=schema,
                        queries=case.get("queries", []),
                        unmodelled_notes=parsed["change_set"]["unmodelled"]) \
            if use_coverage else {"gaps": [], "gap_kinds": [], "irreversible": [],
                                  "corpus_statements": len(case.get("queries", [])),
                                  "parser_notes": parsed["change_set"]["unmodelled"]}
        verdict, capped = coverage_tools.cap(verdict, cov)
        if capped and self.tracer:
            self.tracer.note(self.NAME,
                             f"verdict capped to {verdict}: {len(cov['gaps'])} coverage gap(s) on "
                             f"objects this migration touches "
                             f"({', '.join(g['object'] for g in cov['gaps'])}). No hazard was "
                             f"invented; the packet cannot certify what it did not see.")
        for h in hazards:
            self.model("hazard_narrative", {"hazard": h.to_json()},
                       user=f"Explain this hazard for a reviewer:\n{h.to_json()}")
        out = {"hazards": hazards, "counts": counts, "verdict": verdict,
               "coverage_gaps": parsed["change_set"]["unmodelled"],
               "coverage_ledger": cov, "verdict_capped_by_coverage": capped}
        self.end({"verdict": verdict, "counts": counts,
                  "coverage_gaps": [g["kind"] + ":" + g["object"] for g in cov["gaps"]],
                  "verdict_capped_by_coverage": capped,
                  "hazards": [{"code": h.code, "severity": h.severity, "source": h.source,
                               "memory": h.memory_refs} for h in hazards]})
        return out

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _merge(hazards: list[Hazard]) -> list[Hazard]:
        merged: dict[tuple[str, str], Hazard] = {}
        for h in hazards:
            key = (h.code, ",".join(sorted(h.objects)))
            cur = merged.get(key)
            if cur is None:
                merged[key] = h
                continue
            keep, drop = (h, cur) if SEVERITY_ORDER.index(h.severity) > SEVERITY_ORDER.index(cur.severity) else (cur, h)
            if drop.source == "replay" and keep.source != "replay":
                keep.source = "replay+static"
            keep.evidence = list(dict.fromkeys(keep.evidence + drop.evidence))
            keep.services = sorted(set(keep.services) | set(drop.services))
            merged[key] = keep
        order = {s: i for i, s in enumerate(reversed(SEVERITY_ORDER))}
        return sorted(merged.values(), key=lambda h: (order[h.severity], h.code))

    def _apply_memory(self, hazards: list[Hazard]) -> list[Hazard]:
        for h in hazards:
            table = h.objects[0].split(".")[0] if h.objects else None
            steps, refs = self.tool("memory.escalation", hazard_code=h.code, table=table)
            if refs:
                h.memory_refs = refs
            if steps:
                before = h.severity
                h.severity = bump(h.severity, steps)
                if h.severity != before:
                    h.evidence.append(f"severity raised {before} -> {h.severity} by prior incident(s) "
                                      f"{', '.join(refs)}")
                    h.source = h.source + "+memory"
        return hazards
