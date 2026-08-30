"""The coverage ledger: what this review structurally could not see.

Why this module exists
----------------------
v1 already refused to launder a gap into a green check: an unparsed statement
travelled through as an explicit unknown and landed in the packet's "what this
review did not check" section.  That was the right half of the fix.  The missing
half, named as a known limitation in the v1 submission, is that **a stated gap
did not constrain the verdict**.  `case_09` came back `SAFE_WITH_PLAN`
immediately above a declared blind spot, which is the exact shape of the failure
the tool exists to prevent: a reviewer reads the badge, not the appendix.

So the ledger is not a prose section any more.  It is a machine-computed set of
gap records over the objects this migration actually touches, and it can cap the
verdict.  Three gap classes, each defensible without reference to any label in
the evaluation set:

`unmodelled_statement`
    The parser produced no structural model for the statement, so there is no
    post-migration schema for it and shadow replay never exercised it.  This
    includes statements the static rules *do* now recognise by name (`CLUSTER`,
    `VACUUM FULL`, `REINDEX`): naming a hazard is not the same as modelling the
    statement, and pretending otherwise is how a tool starts lying about its
    own reach.

`in_place_data_mutation`
    Replay proves that a statement still *executes*.  It cannot prove that the
    statement still *returns the same answer*.  Any migration that rewrites
    existing rows changes answers, and the query corpus is a declared sample of
    consumers rather than a census, so a clean replay is structurally
    uninformative about who noticed.

`value_class_erased`
    The sharp case of the above: a backfill that eliminates a distinguishable
    value class (`NULL`), followed by a constraint that makes that class
    unreachable.  The supplied rollback restores the *schema* and not the
    *data*, so the change is irreversible in a way the rollback script implies
    it is not.

`uncovered_object`
    A pre-existing column is altered or dropped and no statement in the corpus
    references it.  Zero failures is then a statement about the corpus, not
    about the column.

What the ledger deliberately does NOT do
----------------------------------------
It does not invent a hazard.  A gap is an absence of evidence, and the honest
representation of an absence is a named human sign-off, not a finding with a
severity.  Findings still come only from replay and the static rules.
"""
from __future__ import annotations

import re
from typing import Any

from .tools.sql_parse import referenced_identifiers

UNMODELLED_KINDS = {"unsupported", "unknown_alter", "unknown_alter_column",
                    "maintenance_rewrite"}

MUTATING_KINDS = {"dml_update", "dml_delete"}

PREEXISTING_TOUCH_KINDS = {"drop_column", "rename_column", "alter_type", "set_not_null",
                           "drop_not_null", "set_default", "drop_default", "drop_table",
                           "rename_table", "drop_view"}

CAPPABLE_VERDICTS = ("SAFE", "SAFE_WITH_PLAN")
CAPPED_VERDICT = "NEEDS_COVERAGE_SIGNOFF"


def _assigned_columns(sql: str) -> list[str]:
    """Columns on the left of an UPDATE ... SET assignment. Over-approximate and cheap."""
    m = re.search(r"\bset\b(?P<body>.*?)(\bwhere\b|$)", sql, flags=re.I | re.S)
    if not m:
        return []
    cols = []
    for chunk in m.group("body").split(","):
        cm = re.match(r"\s*\"?(?P<col>[A-Za-z_][\w$]*)\"?\s*=", chunk)
        if cm:
            cols.append(cm.group("col").lower())
    return cols


def _nulls_erased(sql: str, columns: list[str]) -> list[str]:
    """Columns whose NULLs this statement overwrites (WHERE col IS NULL)."""
    return [c for c in columns
            if re.search(rf"\b{re.escape(c)}\s+is\s+null\b", sql, flags=re.I)]


def ledger(ops: list[Any], schema: Any, queries: list[dict[str, Any]],
           unmodelled_notes: list[str] | None = None) -> dict[str, Any]:
    """Deterministic coverage facts for one migration. Pure function, no model involved."""
    queries = queries or []
    corpus_idents: dict[str, set[str]] = {q["id"]: referenced_identifiers(q["sql"]) for q in queries}
    later_not_null = {(op.table, op.column) for op in ops if op.kind == "set_not_null"}
    gaps: list[dict[str, Any]] = []

    def add(kind: str, obj: str, op: Any, why: str, closes_with: str,
            irreversible: bool = False) -> None:
        gaps.append({
            "kind": kind,
            "object": obj,
            "statement_index": getattr(op, "index", None),
            "statement": (getattr(op, "sql", "") or "")[:140],
            "why": why,
            "closes_with": closes_with,
            "irreversible": irreversible,
        })

    for op in ops:
        table = op.table or "unknown"

        if op.kind in UNMODELLED_KINDS:
            add("unmodelled_statement", table, op,
                "the parser produced no structural model for this statement, so no post-migration "
                "schema and no replay covers it",
                f"a reviewer confirms by hand what statement {op.index} does to {table} and to "
                f"anything reading it")

        if op.kind in MUTATING_KINDS:
            cols = _assigned_columns(op.sql) if op.kind == "dml_update" else []
            erased = _nulls_erased(op.sql, cols)
            targets = [f"{op.table}.{c}" for c in cols] or [table]
            for target in targets:
                col = target.split(".")[-1]
                if col in erased and (op.table, col) in later_not_null:
                    add("value_class_erased", target, op,
                        f"the backfill removes every NULL from {target} and the following SET NOT NULL "
                        f"makes NULL unreachable; any consumer that reads NULL as a distinct state "
                        f"changes behaviour silently, and the supplied rollback restores the column's "
                        f"nullability but not the values",
                        f"a reviewer confirms no consumer treats {target} IS NULL as meaningful, and "
                        f"that the pre-backfill values are captured somewhere restorable",
                        irreversible=True)
                else:
                    add("in_place_data_mutation", target, op,
                        f"rows that already exist in {table} are rewritten; replay proves the corpus "
                        f"still executes, never that it still returns the same answer",
                        f"a reviewer confirms which consumers of {target} depend on the current values")

        if op.kind in PREEXISTING_TOUCH_KINDS and op.column:
            target = f"{op.table}.{op.column}"
            hits = [qid for qid, idents in corpus_idents.items() if op.column.lower() in idents]
            if not hits:
                add("uncovered_object", target, op,
                    f"no statement in the {len(queries)}-statement corpus references {op.column}, so "
                    f"replay had nothing to run against it; that is silence, not a clean bill of health",
                    f"a reviewer greps the real consumers for {op.column} before phase 2")

    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for g in gaps:
        key = (g["kind"], g["object"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(g)

    return {
        "gaps": unique,
        "gap_kinds": sorted({g["kind"] for g in unique}),
        "irreversible": [g["object"] for g in unique if g["irreversible"]],
        "corpus_statements": len(queries),
        "parser_notes": list(unmodelled_notes or []),
    }


def cap(verdict: str, cov: dict[str, Any]) -> tuple[str, bool]:
    """Coverage cannot make a verdict safer; it can only stop one from being clean.

    BLOCK is left alone: it is already the most restrictive answer available.
    """
    if cov["gaps"] and verdict in CAPPABLE_VERDICTS:
        return CAPPED_VERDICT, True
    return verdict, False


def signoff_gates(cov: dict[str, Any]) -> list[str]:
    """One named human decision per open gap, phrased as the thing to go and check."""
    out = []
    for g in cov["gaps"]:
        prefix = "IRREVERSIBLE - " if g["irreversible"] else ""
        out.append(f"{prefix}coverage gap on `{g['object']}` ({g['kind']}): {g['closes_with']}")
    return out
