"""Agent 4 - Rollout Engineer: rewrite the migration as an expand/contract plan.

Output is executable SQL, not advice.  Phase 1 must be safe to run against the
currently deployed application; every irreversible step is pushed to phase 2,
behind a code change and a human gate.  The Verifier re-runs phase 1 through the
same shadow replay, so "safe" is a measured claim.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .. import coverage as coverage_tools
from .base import Agent
from .risk_officer import LOCK_ROWS_WARN
from ..tools.sql_parse import Schema, sqlite_type

BATCH = 5000


@dataclass
class Policy:
    """Knobs the Verifier is allowed to turn between attempts."""
    include_view_changes: bool = True
    expand_contract_type_change: bool = True
    minimal_phase1: bool = False
    notes: list[str] = field(default_factory=list)


def _pk(schema: Schema, table: str) -> str | None:
    t = schema.tables.get(table)
    if not t:
        return None
    pks = [c.name for c in t.columns.values() if c.primary_key]
    return pks[0] if pks else None


def _batched_backfill(schema: Schema, table: str, target: str, source_expr: str) -> tuple[str, str | None]:
    pk = _pk(schema, table)
    if pk:
        return (f'UPDATE "{table}" SET "{target}" = {source_expr} WHERE "{target}" IS NULL '
                f'AND "{pk}" IN (SELECT "{pk}" FROM "{table}" WHERE "{target}" IS NULL LIMIT {BATCH});',
                None)
    return (f'UPDATE "{table}" SET "{target}" = {source_expr} WHERE "{target}" IS NULL;',
            f"{table} has no single-column primary key, so the backfill cannot be batched by key - "
            f"a human must choose the batching strategy")


class RolloutEngineer(Agent):
    NAME = "rollout_engineer"
    GOAL = ("Rewrite the migration as a phase-1 (expand, safe now) / phase-2 (contract, after the "
            "code deploy) plan with a rollback, and surface every step that needs a human decision.")

    def run(self, case: dict[str, Any], parsed: dict[str, Any], blast: dict[str, Any],
            risk: dict[str, Any], policy: Policy, attempt: int = 1) -> dict[str, Any]:
        schema: Schema = parsed["schema"]
        rows_of = {t.name: t.row_estimate for t in schema.tables.values()}
        codes = {h.code for h in risk["hazards"]}
        replay = blast["replay"]
        dup_targets = {h.objects[0].split(".")[0] for h in risk["hazards"]
                       if h.code == "UNIQUE_VIOLATION_EXISTING_DATA" and h.objects}
        loss_cols = {f"{d['table']}.{d['column']}" for d in replay.data_loss if d["offending_rows"]}

        self.start({"case": case["id"], "attempt": attempt, "policy": policy.__dict__,
                    "hazard_codes": sorted(codes)})

        phase1: list[str] = []
        phase2: list[str] = []
        rollback: list[str] = []
        code_steps: list[str] = []
        gates: list[str] = []

        for op in parsed["ops"]:
            table, col = op.table, op.column
            rows = rows_of.get(table or "", 0)
            if op.kind == "add_column":
                typ = op.detail.get("type", "text")
                default = op.detail.get("default")
                piece = f'ALTER TABLE "{table}" ADD COLUMN "{col}" {typ}'
                if default:
                    piece += f" DEFAULT {default}"
                phase1.append(piece + ";")
                rollback.append(f'ALTER TABLE "{table}" DROP COLUMN "{col}";')
                if op.detail.get("not_null"):
                    if default:
                        phase2.append(f'ALTER TABLE "{table}" ALTER COLUMN "{col}" SET NOT NULL;')
                        code_steps.append(f"deploy code that always writes {table}.{col}")
                    else:
                        gates.append(f"{table}.{col} is NOT NULL with no default: a human must supply a "
                                     f"backfill value before phase 2 can add the constraint")
                        phase2.append(f'-- after backfill: ALTER TABLE "{table}" ALTER COLUMN "{col}" SET NOT NULL;')
                if op.detail.get("unique"):
                    phase2.append(f'CREATE UNIQUE INDEX CONCURRENTLY "{table}_{col}_key" ON "{table}" ("{col}");')
            elif op.kind == "rename_column":
                new = op.detail["new_name"]
                src_type = schema.tables[table].columns[col].type if table in schema.tables and col in schema.tables[table].columns else "text"
                phase1.append(f'ALTER TABLE "{table}" ADD COLUMN "{new}" {src_type};')
                stmt, warn = _batched_backfill(schema, table, new, f'"{col}"')
                phase1.append(stmt)
                if warn:
                    gates.append(warn)
                code_steps.append(f"deploy code that writes both {table}.{col} and {table}.{new}, "
                                  f"and reads {table}.{new}")
                phase2.append(f'ALTER TABLE "{table}" DROP COLUMN "{col}";')
                rollback.append(f'ALTER TABLE "{table}" DROP COLUMN "{new}";')
                gates.append(f"confirm no consumer still reads {table}.{col} before phase 2 drops it")
            elif op.kind == "drop_column":
                phase2.append(f'ALTER TABLE "{table}" DROP COLUMN "{col}";')
                code_steps.append(f"remove every read and write of {table}.{col}, then wait one full "
                                  f"deploy cycle")
                gates.append(f"confirm {table}.{col} has had zero reads for the agreed observation "
                             f"window before phase 2")
            elif op.kind in ("drop_table", "drop_view"):
                name = table or op.detail.get("name")
                phase2.append(op.sql if op.sql.endswith(";") else op.sql + ";")
                gates.append(f"confirm nothing reads {name} before phase 2 removes it")
            elif op.kind == "create_index":
                name, cols = op.detail["name"], op.detail["columns"]
                quoted = ", ".join(f'"{c}"' for c in cols)
                if op.detail["unique"] and table in dup_targets:
                    phase1.append(f'CREATE INDEX CONCURRENTLY "{name}_tmp_nonunique" ON "{table}" ({quoted});')
                    gates.append(f"duplicates already exist for {table} ({quoted}); a human must decide the "
                                 f"dedupe rule - phase 2 promotes the index to UNIQUE only after that")
                    phase2.append(f'CREATE UNIQUE INDEX CONCURRENTLY "{name}" ON "{table}" ({quoted});')
                    rollback.append(f'DROP INDEX CONCURRENTLY "{name}_tmp_nonunique";')
                else:
                    uniq = "UNIQUE " if op.detail["unique"] else ""
                    phase1.append(f'CREATE {uniq}INDEX CONCURRENTLY "{name}" ON "{table}" ({quoted});')
                    rollback.append(f'DROP INDEX CONCURRENTLY "{name}";')
            elif op.kind == "add_constraint":
                kind = op.detail["constraint_kind"]
                name = op.detail["constraint"]
                if kind in ("check", "foreign_key"):
                    kw = "CHECK" if kind == "check" else "FOREIGN KEY"
                    phase1.append(f'ALTER TABLE "{table}" ADD CONSTRAINT "{name}" {kw} '
                                  f'{op.detail["expr"]} NOT VALID;')
                    phase2.append(f'ALTER TABLE "{table}" VALIDATE CONSTRAINT "{name}";')
                    rollback.append(f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}";')
                else:
                    quoted = ", ".join(f'"{c}"' for c in op.detail.get("columns", []))
                    phase1.append(f'CREATE UNIQUE INDEX CONCURRENTLY "{name}_idx" ON "{table}" ({quoted});')
                    phase2.append(f'ALTER TABLE "{table}" ADD CONSTRAINT "{name}" UNIQUE '
                                  f'USING INDEX "{name}_idx";')
                    rollback.append(f'DROP INDEX CONCURRENTLY "{name}_idx";')
            elif op.kind == "drop_constraint":
                phase2.append(op.sql if op.sql.endswith(";") else op.sql + ";")
                gates.append(f"dropping {op.detail['constraint']} removes an invariant: the data owner "
                             f"must sign off and a monitoring check should replace it")
            elif op.kind == "alter_type":
                key = f"{table}.{col}"
                if key in loss_cols:
                    gates.append(f"{key} -> {op.detail['new_type']} loses data for rows that exist today; "
                                 f"a human must approve the truncation rule or widen the target type")
                    phase2.append(f'-- blocked pending human decision: {op.sql};')
                elif rows >= LOCK_ROWS_WARN and policy.expand_contract_type_change:
                    shadow_col = f"{col}_new"
                    phase1.append(f'ALTER TABLE "{table}" ADD COLUMN "{shadow_col}" {op.detail["new_type"]};')
                    stmt, warn = _batched_backfill(schema, table, shadow_col, f'"{col}"')
                    phase1.append(stmt)
                    if warn:
                        gates.append(warn)
                    code_steps.append(f"deploy code that dual-writes {table}.{col} and {table}.{shadow_col}")
                    phase2.append(f'ALTER TABLE "{table}" DROP COLUMN "{col}";')
                    phase2.append(f'ALTER TABLE "{table}" RENAME COLUMN "{shadow_col}" TO "{col}";')
                    rollback.append(f'ALTER TABLE "{table}" DROP COLUMN "{shadow_col}";')
                else:
                    phase1.append(op.sql if op.sql.endswith(";") else op.sql + ";")
            elif op.kind == "dml_update":
                target = op.sql.rstrip(";")
                pk = _pk(schema, table)
                if not op.detail.get("batched") and rows >= 10_000 and pk:
                    # reuse the statement's own predicate inside the keyset subquery, otherwise the
                    # batches pick rows that do not need updating and the loop never terminates
                    wm = re.search(r"\bwhere\b(.*)$", target, flags=re.I | re.S)
                    filt = f" WHERE {wm.group(1).strip()}" if wm else ""
                    keyset = (f'"{pk}" IN (SELECT "{pk}" FROM "{table}"{filt} LIMIT {BATCH})')
                    joiner = " AND " if op.detail.get("where") else " WHERE "
                    phase1.append(f"-- repeat until zero rows are affected (batch size {BATCH}):")
                    phase1.append(target + joiner + keyset + ";")
                elif not op.detail.get("batched") and rows >= 10_000:
                    phase1.append(target + ";")
                    gates.append(f"{table} has no single-column primary key, so this backfill cannot be "
                                 f"batched automatically - a human must choose the batching strategy")
                else:
                    phase1.append(target + ";")
            elif op.kind in ("create_view",):
                if policy.include_view_changes:
                    phase1.append(op.sql if op.sql.endswith(";") else op.sql + ";")
                else:
                    phase2.append(op.sql if op.sql.endswith(";") else op.sql + ";")
                    code_steps.append(f"point readers at the new definition of {op.detail['name']} "
                                      f"before phase 2 replaces it")
            elif op.kind in ("rename_table",):
                phase2.append(op.sql if op.sql.endswith(";") else op.sql + ";")
                code_steps.append(f"switch all readers from {table} to {op.detail['new_name']}")
                gates.append(f"renaming {table} is not backwards compatible; confirm the cutover window")
            elif op.kind in ("create_table", "transaction_control", "validate_constraint",
                             "dml_insert", "dml_delete", "drop_index"):
                phase1.append(op.sql if op.sql.endswith(";") else op.sql + ";")
            else:
                gates.append(f"statement {op.index} ({op.kind}) is outside the tool's model and needs "
                             f"manual review: {op.sql[:90]}")

        if "MISSING_ROLLBACK" in codes and not rollback:
            gates.append("no rollback could be generated automatically; write one before shipping")

        if policy.minimal_phase1:
            keep, moved = [], []
            for stmt in phase1:
                additive = (("add column" in stmt.lower() and "not null" not in stmt.lower())
                            or stmt.lower().startswith("create index")
                            or stmt.lower().startswith("update ")
                            or stmt.strip().startswith("--"))
                (keep if additive else moved).append(stmt)
            phase1, phase2 = keep, moved + phase2
            gates.append("phase 1 was reduced to additive statements only; the rest needs a human to "
                         "choose the deploy order")

        # v2: every open coverage gap becomes a named human decision inside the plan,
        # so the thing the tool could not see is work someone has to sign for.
        gates += coverage_tools.signoff_gates(risk.get("coverage_ledger") or {"gaps": []})

        questions = self.model("reviewer_questions", {"codes": sorted(codes)},
                               user=f"Hazard codes: {sorted(codes)}").payload.get("questions", [])
        plan = {
            "attempt": attempt,
            "phase1_sql": phase1,
            "phase2_sql": phase2,
            "rollback_sql": rollback,
            "code_steps": list(dict.fromkeys(code_steps)),
            "human_gates": list(dict.fromkeys(gates)),
            "questions": questions,
            "policy": dict(policy.__dict__),
        }
        self.end({"attempt": attempt, "phase1_statements": len(phase1),
                  "phase2_statements": len(phase2), "human_gates": len(plan["human_gates"])})
        return plan
