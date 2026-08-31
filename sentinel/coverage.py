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

`fixture_bounded_value_scan`
    v6, and the ledger's own perimeter caught from outside.  A narrowing type
    change is scanned against the seeded fixture rows: if none of them would be
    refused by the new type, the packet reported the narrowing as a low-severity
    note with no blind spot declared at all.  On `eval/holdout/holdout_07` that
    printed "shippable" over a change that rejects every settlement invoice above
    1,000,000.00, because the five fixture invoices were small.  The fixture is a
    sample of the data in exactly the way the corpus is a sample of the consumers,
    and the ledger already knew how to say that about consumers.  So: a clean value
    scan over a fixture smaller than the declared row estimate is now a declared
    gap, and an irreversible one, because the rollback restores the type and not
    the values.

`unruled_statement`
    v13, and the ledger's own shape caught from outside.  Every gap class above is
    keyed to a statement kind that some rule or some replay already handles, so the
    ledger could only ever declare blind spots about objects something had already
    looked at.  A statement kind **no rule inspects at all** produced no hazard, no
    gap and a clean verdict.  An allow-list of known unknowns is still an allow-list.
    `sentinel/rulebook.py` partitions every kind the parser can emit into RULED,
    REPLAY_COVERED, LEDGERED and RESIDUAL, and every residual op files this gap.  The
    distinction that makes it usable rather than noisy: a rule *considering* a kind
    and clearing it is coverage; no rule *existing* for that kind is a hole.  Without
    that distinction the first version of this flagged `case_06`, the case that exists
    to catch reviewers who cry wolf.

`unused_access_path`
    v13, the other half of the `DROP INDEX` fix.  When an index is dropped and no
    statement in the corpus filters, joins or sorts by its columns, the honest answer
    is not "safe": it is that a sample of the consumers proves nothing about a plan.
    Exactly the `uncovered_object` argument, one level down in the storage engine, and
    it closes with a different action - real scan counts out of
    `pg_stat_user_indexes`, not a grep.

What the ledger deliberately does NOT do
----------------------------------------
It does not invent a hazard.  A gap is an absence of evidence, and the honest
representation of an absence is a named human sign-off, not a finding with a
severity.  Findings still come only from replay and the static rules.  The v6
addition holds that line: `fixture_bounded_value_scan` moves no severity and adds
no code, it only stops the packet from calling the change shippable.

It also does not pretend to know an object's name.  Where the parser produced no
model at all, v5 filed the gap against the literal string `unknown`, which the
held-out trigger case exposed: the statement says `ON shipment_stops` in plain text
and the ledger, whose entire job is to name the affected object, printed `unknown`.
v6 reads the relation out of the statement text and flags it `object_inferred`, so
a reviewer is told which object to go and check *and* told that the name came from
a regular expression rather than from a parse.
"""
from __future__ import annotations

import re
from typing import Any

from . import rulebook
from .tools.query_corpus import access_path_users
from .tools.shadow_db import is_narrowing, offending_values
from .tools.sql_parse import referenced_identifiers

UNMODELLED_KINDS = {"unsupported", "unknown_alter", "unknown_alter_column",
                    "maintenance_rewrite"}

MUTATING_KINDS = {"dml_update", "dml_delete"}

PREEXISTING_TOUCH_KINDS = {"drop_column", "rename_column", "alter_type", "set_not_null",
                           "drop_not_null", "set_default", "drop_default", "drop_table",
                           "rename_table", "drop_view"}

# Statements the parser cannot model at all still name their relation in the text.
RELATION_HINT = re.compile(
    r"\b(?:on|table|from|into|view|only)\s+(?:if\s+exists\s+)?\"?(?P<rel>[A-Za-z_][\w$]*)\"?",
    re.I)
HINT_STOPWORDS = {"select", "update", "delete", "insert", "each", "row", "statement", "concurrently",
                  "materialized", "if", "exists", "only", "table", "view"}

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


def relation_hint(sql: str) -> str | None:
    """The relation an unmodelled statement mentions, read out of its text.

    Deliberately a hint and not a parse: it is reported as `object_inferred` so the
    packet never implies the parser understood the statement.
    """
    for m in RELATION_HINT.finditer(sql or ""):
        rel = m.group("rel").lower()
        if rel not in HINT_STOPWORDS:
            return rel
    return None


def _nulls_erased(sql: str, columns: list[str]) -> list[str]:
    """Columns whose NULLs this statement overwrites (WHERE col IS NULL)."""
    return [c for c in columns
            if re.search(rf"\b{re.escape(c)}\s+is\s+null\b", sql, flags=re.I)]


def ledger(ops: list[Any], schema: Any, queries: list[dict[str, Any]],
           unmodelled_notes: list[str] | None = None,
           seed: dict[str, list[dict[str, Any]]] | None = None,
           rule_coverage: bool = True) -> dict[str, Any]:
    """Deterministic coverage facts for one migration. Pure function, no model involved.

    `seed` is the fixture the shadow replay runs on. It is passed in so the ledger can
    say what the fixture could not have shown, which is the v6 gap class.

    `rule_coverage` is the v13 layer: the two gap classes that come from the rule
    inventory rather than from the data. It is a switch only so `no_rule_coverage` can
    reproduce v12 behaviour exactly and the ablation can price this layer like every
    other one.
    """
    queries = queries or []
    seed = seed or {}
    corpus_idents: dict[str, set[str]] = {q["id"]: referenced_identifiers(q["sql"]) for q in queries}
    later_not_null = {(op.table, op.column) for op in ops if op.kind == "set_not_null"}
    gaps: list[dict[str, Any]] = []

    def add(kind: str, obj: str, op: Any, why: str, closes_with: str,
            irreversible: bool = False, object_inferred: bool = False) -> None:
        gaps.append({
            "kind": kind,
            "object": obj,
            "object_inferred": object_inferred,
            "statement_index": getattr(op, "index", None),
            "statement": (getattr(op, "sql", "") or "")[:140],
            "why": why,
            "closes_with": closes_with,
            "irreversible": irreversible,
        })

    for op in ops:
        table = op.table or "unknown"

        if op.kind in UNMODELLED_KINDS:
            inferred = False
            if op.table is None:
                hint = relation_hint(getattr(op, "sql", ""))
                if hint:
                    table, inferred = hint, True
            add("unmodelled_statement", table, op,
                "the parser produced no structural model for this statement, so no post-migration "
                "schema and no replay covers it"
                + (f"; the relation name was read out of the statement text, not parsed"
                   if inferred else ""),
                f"a reviewer confirms by hand what statement {op.index} does to {table} and to "
                f"anything reading it",
                object_inferred=inferred)

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

        if op.kind == "alter_type" and op.column:
            col_model = (schema.tables.get(op.table).columns.get(op.column)
                         if schema.tables.get(op.table) else None)
            new_type = op.detail.get("new_type", "")
            if col_model is not None and is_narrowing(col_model.type, new_type):
                fixture = seed.get(op.table, []) or []
                values = [r.get(op.column) for r in fixture]
                declared_rows = getattr(schema.tables.get(op.table), "row_estimate", 0) or 0
                if not offending_values(values, new_type) and len(fixture) < declared_rows:
                    add("fixture_bounded_value_scan", f"{op.table}.{op.column}", op,
                        f"the value scan for {op.table}.{op.column} -> {new_type} ran over "
                        f"{len(fixture)} fixture row(s) against a declared {declared_rows:,} in "
                        f"production and found nothing that would be refused; that is a fact about "
                        f"the fixture, not about the column, and the rollback restores the type "
                        f"without the values",
                        f"a reviewer counts the real offenders before phase 2: SELECT count(*) FROM "
                        f"{op.table} WHERE {op.column} would not fit {new_type}",
                        irreversible=True)

        if op.kind in PREEXISTING_TOUCH_KINDS and op.column:
            target = f"{op.table}.{op.column}"
            hits = [qid for qid, idents in corpus_idents.items() if op.column.lower() in idents]
            if not hits:
                add("uncovered_object", target, op,
                    f"no statement in the {len(queries)}-statement corpus references {op.column}, so "
                    f"replay had nothing to run against it; that is silence, not a clean bill of health",
                    f"a reviewer greps the real consumers for {op.column} before phase 2")

        # v13: an index drop whose access path nobody in the corpus uses. Zero users is a
        # fact about a sample of the consumers, and the storage engine is not consulted.
        if op.kind == "drop_index" and rule_coverage:
            idx = getattr(schema, "indexes", {}).get(op.detail.get("name", ""))
            replaced = idx is not None and any(
                o.kind == "create_index"
                and (o.table or "").lower() == (idx.table or "").lower()
                and [c.lower() for c in o.detail.get("columns", [])][:len(idx.columns)]
                == [c.lower() for c in idx.columns]
                for o in ops)
            if idx is not None and not replaced \
                    and not access_path_users(queries, idx.table, idx.columns):
                add("unused_access_path", f"{idx.table}({', '.join(idx.columns)})", op,
                    f"no statement in the {len(queries)}-statement corpus filters, joins or sorts "
                    f"by {idx.table}({', '.join(idx.columns)}), so this review has no evidence the "
                    f"index is unused - only no evidence that it is used, and shadow replay has no "
                    f"query planner to ask",
                    f"a reviewer reads pg_stat_user_indexes.idx_scan for "
                    f"{op.detail.get('name', 'the index')} over a full business cycle before phase 2")

    # v13: statement kinds nothing in this pipeline inspects. The gap class that exists
    # because the ledger could previously only declare blind spots about objects some
    # rule had already looked at. See sentinel/rulebook.py.
    if rule_coverage:
        for op in rulebook.residual_ops(ops):
            obj = op.table or relation_hint(getattr(op, "sql", "")) or "statement"
            add("unruled_statement", f"{obj}:{op.kind}", op,
                f"no static rule inspects `{op.kind}` and shadow replay cannot see its consequence: "
                f"{rulebook.reason(op.kind)}",
                f"a reviewer decides by hand what statement {op.index} changes for future writes "
                f"and who depends on the current behaviour")

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
