"""The rule inventory: which parsed statement kinds anything in this pipeline looks at.

SUPERVISOR LOG (v13), carried at the top of the file that acts on it
-------------------------------------------------------------------
Everything below exists because of one external red-team pass whose only job was to
find a migration this pipeline calls SAFE and a database would call an outage.  It
found two in six probes, and the reason it found them is more interesting than either
bug.

  R1  "the coverage ledger names what the review could not see."  It named what the
      review could not see *about objects a rule already looked at*.  The ledger
      enumerated gap classes per op kind: `unmodelled_statement`,
      `in_place_data_mutation`, `value_class_erased`, `uncovered_object`,
      `fixture_bounded_value_scan`.  Every one of those is keyed to a kind that some
      rule or some replay already handles.  A statement kind **no rule inspects at
      all** produced no hazard, no gap and a clean verdict - the exact failure the
      ledger was built to prevent, one level up.  v2 made a declared gap constrain the
      verdict.  It never asked what happens when nothing declares anything.  An
      allow-list of known unknowns is still an allow-list.

  R2  `DROP INDEX idx_invoices_customer` on a 48M-row table three critical statements
      filter by `customer_id`.  Parsed cleanly, into an op whose `table` field is
      `None`.  Shadow replay executes every query fine, because SQLite has no plan
      cost and the fixtures are five rows.  No static rule mentions `drop_index`.
      Verdict: **SAFE**, zero hazards, zero coverage gaps.  This is the most common
      migration in the world - "clean up unused indexes" - and the one op kind whose
      entire risk is invisible to both halves of the design.

  R3  `BEGIN; CREATE INDEX CONCURRENTLY ...; COMMIT;`  Postgres refuses outright: CIC
      cannot run inside a transaction block, and every major migration framework wraps
      a migration in one by default.  Both halves saw it and neither cared: the parser
      emits `transaction_control` and `create_index(concurrently=True)` as separate
      ops and no rule correlates them.  Verdict: **SAFE**.  The *text-only baseline*
      catches this one, because it is a famous string.  So on this hazard class the
      advanced solution scored below the thing it exists to beat, and no in-sample
      number could ever have shown it: the twelve cases contain no `BEGIN`.

WHAT THIS MODULE IS
-------------------
The inventory of statement kinds, partitioned by *what in this pipeline actually looks
at them*.  Four buckets, and the invariant that makes it worth having:

    RULED             a static rule in agents/risk_officer.py inspects this kind
    REPLAY_COVERED    the consequence is exercised by running the corpus against the
                      post-migration schema, so replay is the coverage
    LEDGERED          coverage.py already opens a gap for this kind by construction
    RESIDUAL          nothing above.  Reviewed, named, and declared as a gap rather
                      than passed over in silence.

`tests/test_all.py::TestRulebook` asserts the union equals every kind
`sql_parse.parse_migration` can emit.  Teach the parser a new statement kind and the
test fails until someone decides, in this file, which bucket it belongs to.  That is
the point: the failure was not a wrong rule, it was an absent one nothing was counting.

WHY RESIDUAL IS A GAP AND NOT A HAZARD
--------------------------------------
The line the ledger has held since v2: an absence of evidence is not a finding.  A
residual kind gets `unruled_statement`, which caps the verdict at
NEEDS_COVERAGE_SIGNOFF and names a human gate.  It invents no hazard and moves no
severity.

WHY THIS IS NOT JUST "DEFAULT DENY"
-----------------------------------
The first version of this module was default-deny: any op no rule fired on opened a
gap.  It flagged `case_06` - `CREATE UNIQUE INDEX CONCURRENTLY`, the case that exists
to catch reviewers who cry wolf - because the index rule looked at it and correctly
cleared it, and "no hazard was produced" is indistinguishable from "nothing looked" if
you only count hazards.  So the distinction this file draws is between *a rule
considered this kind and cleared it* and *no rule exists for this kind*.  The first is
coverage.  The second is a hole.  Conflating them is how a safety tool becomes a tool
that flags everything, which is the same as flagging nothing.
"""
from __future__ import annotations

import inspect
import re
from typing import Any

# --- kinds a static rule in agents/risk_officer.py inspects -----------------
# Each entry names the rule that looks, so this list cannot drift into decoration.
RULED: dict[str, str] = {
    "drop_column": "DESTRUCTIVE_NO_EXPAND_CONTRACT",
    "drop_table": "DESTRUCTIVE_NO_EXPAND_CONTRACT",
    "rename_column": "DESTRUCTIVE_NO_EXPAND_CONTRACT",
    "rename_table": "DESTRUCTIVE_NO_EXPAND_CONTRACT",
    "create_index": "INDEX_LOCK_NO_CONCURRENT / CONCURRENT_DDL_IN_TRANSACTION",
    "add_constraint": "CONSTRAINT_VALIDATION_LOCK",
    "maintenance_rewrite": "TABLE_REWRITE_LOCK",
    "alter_type": "TABLE_REWRITE_LOCK",
    "dml_update": "UNBATCHED_BACKFILL",
    "set_not_null": "NOT_NULL_NO_DEFAULT",
    "add_column": "NOT_NULL_NO_DEFAULT",
    "drop_constraint": "INTEGRITY_CONSTRAINT_REMOVED",
    # v13, the two holes the red-team pass found:
    "drop_index": "ACCESS_PATH_REMOVED",
    "transaction_control": "CONCURRENT_DDL_IN_TRANSACTION",
}

# --- kinds whose consequence shadow replay exercises directly ---------------
# Justification per kind, because "replay covers it" is exactly the sentence R2 was
# hiding behind.
REPLAY_COVERED: dict[str, str] = {
    "create_view": "apply_ops models the new definition and the corpus is re-executed against it, "
                   "so a view that stops resolving or changes its column set surfaces as "
                   "VIEW_BREAKAGE / SELECT_STAR_DRIFT",
    "drop_view": "any corpus statement reading the view fails against the post schema, which is "
                 "BREAKING_QUERY / VIEW_BREAKAGE",
    "create_table": "purely additive: nothing that executes today can start failing because a new "
                    "relation exists, and the corpus is replayed against the post schema anyway",
}

# --- kinds coverage.py already opens a gap for, by construction -------------
LEDGERED: dict[str, str] = {
    "unsupported": "unmodelled_statement",
    "unknown_alter": "unmodelled_statement",
    "unknown_alter_column": "unmodelled_statement",
    "dml_delete": "in_place_data_mutation",
}

# --- everything else: reviewed, named, declared rather than passed over ------
# The honest bucket. Each parses cleanly, executes cleanly in replay, and carries a
# risk neither a rule nor the corpus can see. These open `unruled_statement`.
RESIDUAL: dict[str, str] = {
    "set_default": "the default only affects writes that have not happened yet, so no existing "
                   "statement in the corpus can fail and no rule prices the behaviour change",
    "drop_default": "same shape: future INSERTs that omitted the column start writing NULL, and "
                    "nothing in the corpus or the fixtures executes in that future",
    "drop_not_null": "relaxing nullability breaks readers that assume non-null, and every one of "
                     "those readers is in application code rather than in the SQL corpus",
    "dml_insert": "rows appear that no fixture contains; replay proves the statement runs, never "
                  "that what it inserts is correct or idempotent on a retry",
    "validate_constraint": "the second half of a NOT VALID split takes its own lock over the whole "
                           "relation and no rule prices it against the row estimate",
}

BUCKETS = ("RULED", "REPLAY_COVERED", "LEDGERED", "RESIDUAL")


def known_kinds() -> set[str]:
    return set(RULED) | set(REPLAY_COVERED) | set(LEDGERED) | set(RESIDUAL)


def bucket(kind: str) -> str:
    if kind in RULED:
        return "RULED"
    if kind in REPLAY_COVERED:
        return "REPLAY_COVERED"
    if kind in LEDGERED:
        return "LEDGERED"
    if kind in RESIDUAL:
        return "RESIDUAL"
    return "UNCLASSIFIED"


def reason(kind: str) -> str:
    for table in (RULED, REPLAY_COVERED, LEDGERED, RESIDUAL):
        if kind in table:
            return table[kind]
    return ("this statement kind is not in the rule inventory at all, so nobody has decided how "
            "it is covered")


def residual_ops(ops: list[Any]) -> list[Any]:
    """Ops whose kind nothing in this pipeline inspects. RESIDUAL plus UNCLASSIFIED.

    An unclassified kind is treated as residual on purpose: a parser that learns a new
    statement kind should make reviews *more* cautious until someone classifies it, not
    silently quieter.
    """
    return [op for op in ops if bucket(op.kind) in ("RESIDUAL", "UNCLASSIFIED")]


def parser_kinds() -> set[str]:
    """Every kind `sql_parse.parse_migration` can emit, read out of its own source.

    Read from source rather than maintained by hand, because a hand-maintained list of
    what the parser emits is the same class of artefact as a hand-maintained list of
    what the rules cover, and this module exists because that class of artefact drifts.
    """
    from .tools import sql_parse

    src = inspect.getsource(sql_parse.parse_migration)
    return set(re.findall(r'Op\(\s*"([a-z_]+)"', src))


def render() -> str:
    """The inventory as a table, for the packet and for the docs."""
    lines = ["| statement kind | coverage | how |", "|---|---|---|"]
    for kind in sorted(known_kinds()):
        lines.append(f"| `{kind}` | {bucket(kind)} | {reason(kind)} |")
    return "\n".join(lines)
