"""Agent 3 - Risk Officer: the hazards execution cannot see, plus institutional memory.

Shadow replay is blind to three things: locks (SQLite has no MVCC), volume (the
fixtures are tiny) and intent (dropping a CHECK constraint breaks nothing today).
This agent covers exactly those, with explicit, auditable rules - and then lets
memory of past incidents raise, never lower, a severity.

v13 adds a fourth thing replay is blind to, found by an external red-team pass rather
than by an ablation: the query *plan*.  Replay proves a statement still executes; it
says nothing about how the planner will find the rows, so `DROP INDEX` on a hot table
was a clean SAFE.  And it adds one thing both halves saw and neither correlated:
`CONCURRENTLY` inside a transaction block, which Postgres refuses outright.  See
`sentinel/rulebook.py` for why those two were absent rather than wrong.

v14 adds two more that no rule over the op list could ever have raised, because the op
list was not the migration: text in the file that no operation accounts for, and DDL
executing inside a procedural body.  Both read the reconciliation in
`sentinel/tools/parse_audit.py`.  A `--` inside a string literal used to cost this agent
two thirds of a migration silently, and no rule can fire on a statement that was never
parsed.
"""
from __future__ import annotations

import re
from typing import Any

from .. import coverage as coverage_tools
from ..hazards import Hazard, SEVERITY_ORDER, bump
from .base import Agent

LOCK_ROWS_WARN = 100_000
LOCK_ROWS_BLOCK = 5_000_000
DESTRUCTIVE = {"drop_column", "drop_table", "rename_column", "rename_table"}
CONCURRENT_KINDS = {"create_index", "drop_index"}


def is_concurrent(op: Any) -> bool:
    """CONCURRENTLY on an index statement, from the parse where available and the text otherwise.

    `create_index` carries it in `detail`; `drop_index` does not parse it out, and reading
    the text is honest here because the keyword is unambiguous in that position.
    """
    if op.detail.get("concurrently"):
        return True
    return bool(re.search(r"\bconcurrently\b", op.sql or "", flags=re.I))


def replacement_index(ops: list[Any], table: str, columns: list[str]) -> Any | None:
    """A CREATE INDEX in the same migration that still serves `columns` on `table`.

    Prefix match, because a B-tree on (a, b) serves a lookup on (a) and a plain index on
    (a) does not serve one on (b).  Without this the commonest correct index migration in
    the world - drop the narrow index, create the composite - would earn a blocker, and a
    safety tool that blocks the correct version of a change gets switched off.
    """
    want = [c.lower() for c in columns]
    for op in ops:
        if op.kind != "create_index" or (op.table or "").lower() != (table or "").lower():
            continue
        have = [c.lower() for c in op.detail.get("columns", [])]
        if have[:len(want)] == want:
            return op
    return None


def open_transaction_at(ops: list[Any], index: int) -> Any | None:
    """The BEGIN that is still open at statement `index`, if any.

    Postgres refuses CREATE/DROP INDEX CONCURRENTLY inside a transaction block. Migration
    frameworks open one by default, so this is a correlation between two statements rather
    than a property of either, which is exactly why no single-statement rule caught it.
    """
    current = None
    for op in ops:
        if op.index >= index:
            break
        if op.kind != "transaction_control":
            continue
        head = (op.sql or "").strip().lower()
        if head.startswith("begin") or head.startswith("start transaction"):
            current = op
        elif head.startswith(("commit", "rollback", "end")):
            current = None
    return current


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
            use_coverage: bool = True, use_rule_coverage: bool = True,
            use_text_conservation: bool = True) -> dict[str, Any]:
        schema = parsed["schema"]
        rows_of = {t.name: t.row_estimate for t in schema.tables.values()}
        self.start({"case": case["id"], "row_estimates": rows_of,
                    "inherited_hazards": [h.code for h in blast["hazards"]]})
        hazards: list[Hazard] = list(blast["hazards"])
        # v14: the reconciliation between this op list and the file it came from. A rule
        # cannot fire on a statement that never became an op, so two of the findings below
        # are keyed to the scan rather than to an op. See `sentinel/tools/parse_audit.py`.
        audit = parsed.get("text_audit") if use_text_conservation else None
        bodies_at = {}
        for _body in (audit or {}).get("procedural", []):
            bodies_at.setdefault(_body["statement_index"], []).append(_body)

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
            # v13, rule 1: the access path. Replay proves the statement executes; nothing in
            # this pipeline priced how the planner would find the rows.
            if op.kind == "drop_index" and use_rule_coverage:
                name = op.detail.get("name", "")
                idx = schema.indexes.get(name)
                if idx is None:
                    hazards.append(Hazard(
                        "ACCESS_PATH_REMOVED", "medium", source="static",
                        summary=(f"index {name} is dropped but is not in the current DDL, so this "
                                 f"review cannot tell what it served"),
                        evidence=[f"statement {op.index}: `{op.sql[:110]}`",
                                  f"no index named {name} in the supplied schema"],
                        objects=[name],
                        remediation="confirm the index name against the live catalogue before shipping"))
                else:
                    idx_rows = rows_of.get(idx.table, 0)
                    users = self.tool("corpus.access_path_users", queries=case.get("queries", []),
                                      table=idx.table, columns=idx.columns)
                    replacement = replacement_index(parsed["ops"], idx.table, idx.columns)
                    if replacement is not None:
                        users = []
                        if self.tracer:
                            self.tracer.note(
                                self.NAME,
                                f"{name} is dropped but statement {replacement.index} creates "
                                f"{replacement.detail['name']} on {idx.table}"
                                f"({', '.join(replacement.detail['columns'])}), whose leading "
                                f"columns still serve {idx.table}({', '.join(idx.columns)}). The "
                                f"access path survives, so no ACCESS_PATH_REMOVED is raised.")
                    crit = {u["criticality"] for u in users}
                    if users:
                        sev = "medium"
                        if idx_rows >= LOCK_ROWS_WARN:
                            sev = "high"
                        if idx_rows >= LOCK_ROWS_BLOCK and crit & {"critical", "high"}:
                            sev = "blocker"
                        cols = ", ".join(idx.columns)
                        hazards.append(Hazard(
                            "ACCESS_PATH_REMOVED", sev, source="static+replay",
                            summary=(f"dropping {name} removes the only declared index on "
                                     f"{idx.table} ({cols}) while {len(users)} live statement(s) "
                                     f"still filter, join or sort by it on a "
                                     f"{size_class(idx_rows)} table ({idx_rows:,} rows)"),
                            evidence=[f"statement {op.index}: `{op.sql[:110]}`",
                                      f"declared row estimate for {idx.table}: {idx_rows:,}"]
                                     + [f"{u['query_id']} ({u['service']}, {u['criticality']}): "
                                        f"`{u['clause_excerpt']}`" for u in users[:4]],
                            objects=[f"{idx.table}.{c}" for c in idx.columns],
                            services=sorted({u["service"] for u in users}),
                            remediation=(f"prove the index is unused first: check "
                                         f"pg_stat_user_indexes.idx_scan for {name} over a full "
                                         f"business cycle, then drop it CONCURRENTLY in phase 2")))

            # v13, rule 2: a correlation between two statements, not a property of either.
            if op.kind in CONCURRENT_KINDS and use_rule_coverage and is_concurrent(op):
                opener = open_transaction_at(parsed["ops"], op.index)
                if opener is not None:
                    hazards.append(Hazard(
                        "CONCURRENT_DDL_IN_TRANSACTION", "blocker", source="static",
                        summary=(f"statement {op.index} uses CONCURRENTLY inside the transaction "
                                 f"opened at statement {opener.index}; Postgres refuses this and "
                                 f"the deploy fails on the statement itself"),
                        evidence=[f"statement {opener.index}: `{opener.sql[:60]}`",
                                  f"statement {op.index}: `{op.sql[:110]}`",
                                  "ERROR: CREATE INDEX CONCURRENTLY cannot run inside a "
                                  "transaction block (Postgres, all supported versions)"],
                        objects=[op.detail.get("name", op.table or "index")],
                        remediation=("take this statement out of the transaction: most frameworks "
                                     "need an explicit opt-out (Rails disable_ddl_transaction!, "
                                     "Django atomic = False, Alembic autocommit block)")))

            # v14, rule 1: DDL executing inside a procedural body. Keyed to the op, priced
            # from the census in tools/parse_audit.py, which is a keyword scan over
            # literal-masked text rather than a parse - so the DDL is a finding and the
            # block itself stays a declared gap.
            if op.kind == "procedural_block":
                for body in bodies_at.get(op.index, []):
                    if not body["ddl_inside"]:
                        continue
                    shown = (body["destructive_inside"] or body["ddl_inside"])[:3]
                    hazards.append(Hazard(
                        "PROCEDURAL_DDL_UNREVIEWED",
                        "blocker" if body["destructive_inside"] else "high", source="static",
                        summary=(f"{len(body['ddl_inside'])} schema or data statement(s) execute "
                                 f"inside the {body['tag']} body of statement {op.index}; the "
                                 f"expand/contract analysis, the dependency map and the shadow "
                                 f"replay all ran on the outer statement only"),
                        evidence=[f"statement {op.index}: `{body['head']}`"]
                                 + [f"inside the body: `{t[:100]}`" for t in shown],
                        objects=["migration script"],
                        remediation=("lift the DDL out of the procedural block so it can be planned "
                                     "and reviewed as a statement; keep the block for the data "
                                     "logic that actually needs it")))

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

        # v14, rule 2: text in the file that no operation accounts for. Not keyed to an op,
        # because the defect is precisely that there is no op: `strip_comments` cut a string
        # literal at a `--` inside it and the resulting unterminated quote swallowed two
        # destructive statements. Findings rather than gaps because the evidence is positive
        # and carries a span - the scanner can quote the text nobody reviewed. Where the
        # scan cannot say what the text does, the ledger takes it as a gap instead; see
        # `unattributed_statement` in sentinel/coverage.py.
        unparsed: list[Hazard] = []
        if use_static and audit:
            for bad in audit["unterminated"]:
                unparsed.append(Hazard(
                    "MIGRATION_TEXT_UNPARSED", "blocker", source="static",
                    summary=(f"an unterminated {bad['kind'].replace('_', ' ')} starts at character "
                             f"{bad['start']}, so Postgres rejects this script and everything after "
                             f"that point was reviewed as string content rather than as SQL"),
                    evidence=[f"scanner: `{bad['text'].strip()[:100]}`", bad["why"]],
                    objects=["migration script"],
                    remediation=("close the literal. If the intent was a comment inside a string, "
                                 "it is not one: Postgres reads `--` inside quotes as text")))
            for miss in audit["unaccounted"]:
                if not miss["destructive"]:
                    continue
                unparsed.append(Hazard(
                    "MIGRATION_TEXT_UNPARSED", "blocker", source="static",
                    summary=(f"statement {miss['statement_index']} is in the file and no parsed "
                             f"operation accounts for it, and its text is destructive, so a change "
                             f"this review never modelled will execute"),
                    evidence=[f"scanner statement {miss['statement_index']} "
                              f"(characters {miss['start']}-{miss['end']}): `{miss['text'][:110]}`",
                              f"the parse produced {audit['ops']} operation(s) for "
                              f"{audit['lexed_statements']} scanned statement(s)"],
                    objects=["migration script"],
                    remediation="rewrite the statement in a form the parser models, or review it by "
                                "hand and record the decision against this run"))

        # v14, and the experiment this pass removed. The first version reported the
        # unterminated-literal hazard *alongside* the hazards inferred from the mangled
        # remainder, which on rt2_03 meant two findings about statements Postgres will never
        # execute - the identical sin to raising a blocker on a commented-out statement
        # (rt2_04), in the opposite direction. A script the server refuses has no hazards
        # other than that it is refused, so the findings derived from the wreckage are
        # dropped and only the parse failure is reported. The coverage ledger still names the
        # region nobody could read: `unreviewable_text`.
        if unparsed:
            dropped = sorted({h.code for h in hazards})
            hazards = unparsed
            if self.tracer:
                self.tracer.checkpoint(
                    "parse conservation", "SCRIPT DOES NOT PARSE",
                    "Postgres will refuse this script, so no statement in it executes and any "
                    "finding read off the mangled remainder would be a claim about text that "
                    "never runs. "
                    + (f"Suppressed for that reason: {', '.join(dropped)}. " if dropped else "")
                    + "The only honest output is the parse failure and the region nobody could "
                      "read. Fix the script and resubmit for review.")

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
                        unmodelled_notes=parsed["change_set"]["unmodelled"],
                        seed=case.get("seed", {}),
                        rule_coverage=use_rule_coverage,
                        text_audit=(parsed.get("text_audit") if use_text_conservation else None)) \
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
