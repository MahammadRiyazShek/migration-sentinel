"""Reconcile the op list against the file it came from. The v14 layer.

SUPERVISOR LOG (v14), carried at the top of the file that acts on it
-------------------------------------------------------------------
v13 published an arithmetic: enumerate what your tool can parse, subtract what any
part of it actually inspects, publish the remainder as a named blind spot.
`sentinel/rulebook.py` is that arithmetic, and it is exhaustive over the op list.

The op list is not the file.

    UPDATE invoices SET note = 'legacy -- do not touch' WHERE note IS NULL;
    ALTER TABLE invoices DROP COLUMN legacy_total;
    DROP TABLE invoice_archive;

Three statements went in.  One op came out.  The comment stripper cut the literal at
the `--`, the resulting unterminated quote swallowed the rest of the file, and the
two destructive statements were never presented to a rule, to replay or to the
coverage ledger.  Every honesty layer in this repository - the ledger since v2, the
provenance narrator since v5, the fixture gap since v6, the rule inventory since v13
- operates downstream of a parse that had silently discarded two thirds of its
input.  A rule inventory cannot see a statement that never became an op.

So this module does the same subtraction one level up, over the source text:

    every statement the scanner finds
      - every statement an op accounts for
      = the statements this review never looked at

and it reports the remainder with spans, keywords and the source excerpt, so the
packet can say *which* text nobody read rather than reporting a smaller migration
than the one on disk.

THREE FINDINGS, AND THE ONE RULE THAT SEPARATES THEM
----------------------------------------------------
  unterminated construct   A literal, identifier or block comment that never
                           closes.  Postgres rejects the whole script, so the
                           reviewed artefact and the deployed artefact are not the
                           same object.  Positive evidence, with a span: a FINDING.

  unaccounted statement    The scanner found a top-level statement and no op claims
                           its index.  If its text is destructive we know something
                           destructive executes unreviewed - positive evidence, a
                           FINDING.  If it is not, we know only that we do not know:
                           a declared GAP with a human gate.

  procedural body          `DO $$ ... $$` and function bodies execute statements no
                           structural parser here models, and the naive splitter used
                           to shred them at their inner semicolons.  DDL inside one
                           is positive evidence that schema changes bypass the whole
                           expand/contract analysis: a FINDING, plus a GAP for the
                           rest of the body, because reading the body is not
                           modelling it.

The line is the same one the ledger has held since v2 and the rulebook restated in
v13: text we can read is evidence, text we cannot is a gap, and the two must never
be printed as the same thing.

THE CANARY, AND WHY IT IS IN THE SET
------------------------------------
Postgres nests block comments; the retired regex did not.  A superseded statement
commented out with a nested comment inside it left a live `ALTER TABLE ... DROP
COLUMN` behind after the first `*/`, and the v13 pipeline blocked a migration whose
destructive statement is commented out.  Same defect as the statement loss, opposite
sign.  `rt2_06` is that case and every arm has to stay quiet on it, because a tool
that invents a blocker out of a comment gets switched off, and a switched-off tool
has recall zero.  Nothing in this module ever reads the raw source: every census
runs over `LexedStatement.code`, where comments are already blanked.
"""
from __future__ import annotations

import re
from typing import Any

from . import sql_lex

# Kinds of dollar-quoted body that carry executable statements. A `$$`-quoted default
# or a quoted piece of documentation is a string, not a program, so the census only
# runs where the statement itself says it is running code.
PROCEDURAL_HEAD = re.compile(
    r"^\s*(do\b|create\s+(or\s+replace\s+)?(function|procedure)\b)", re.I)

# plpgsql keywords that open or close a block rather than act on the schema. Stripped
# from the front of an inner statement before the census, because `BEGIN` carries no
# semicolon of its own, so the scanner hands back `BEGIN ALTER TABLE ...` as one unit and
# a leading-keyword test would read the whole thing as control flow.
CONTROL_FLOW = ("begin", "declare", "end", "loop", "else", "then", "elsif", "exception",
                "commit", "rollback")
CONTROL_PREFIX = re.compile(r"^\s*(?:(?:" + "|".join(CONTROL_FLOW) + r")\b\s*)+", re.I)

# The census pattern. Deliberately a search over literal-masked text rather than a parse:
# the whole point of this module is that a procedural body is NOT parsed here, and
# claiming otherwise would be the same class of overreach it was written to catch.
DDL_IN_BODY = re.compile(
    r"\b(alter\s+table|drop\s+(?:table|column|view|index|constraint|schema|sequence)|"
    r"create\s+(?:unique\s+)?(?:table|index|view|schema|sequence)|truncate\b|"
    r"update\s+[\w.\"]+\s+set|delete\s+from|insert\s+into|grant\b|revoke\b)", re.I)


def _mask_literals(text: str) -> str:
    """Text with every string literal and quoted identifier blanked.

    So a DDL keyword sitting inside a quoted message inside a `DO` block cannot become a
    finding. The false-positive direction of this defect class is a case in the set
    (`rt2_06`), and it is the reason nothing in this module ever reads raw source.
    """
    res = sql_lex.lex(text)
    chars = list(text)
    for span in list(res.literal_spans) + list(res.comment_spans):
        for i in range(max(0, span.start), min(span.end, len(chars))):
            chars[i] = " "
    return "".join(chars)


def _inner_statements(body: str) -> list[dict[str, Any]]:
    """Statements inside a procedural body, scanned rather than parsed.

    A census with text attached, never turned into ops: pretending a `DO` block's
    contents are modelled is exactly the class of claim this file exists to stop.
    """
    out: list[dict[str, Any]] = []
    for st in sql_lex.lex(body).statements:
        code = re.sub(r"\s+", " ", st.code).strip()
        if not code:
            continue
        masked = re.sub(r"\s+", " ", _mask_literals(st.code)).strip()
        stripped = CONTROL_PREFIX.sub("", masked).strip()
        hit = DDL_IN_BODY.search(stripped)
        # Quote from the DDL keyword rather than from the start of the inner statement: an
        # idempotency guard puts 90 characters of `IF EXISTS (SELECT ...)` in front of the
        # statement that matters, and evidence a reviewer has to scroll is evidence nobody
        # reads.
        excerpt = stripped[hit.start():].strip() if hit else code
        out.append({
            "excerpt": excerpt[:160],
            "keyword": (hit.group(1).lower() if hit else
                        (CONTROL_PREFIX.match(masked).group(0).strip().lower()
                         if CONTROL_PREFIX.match(masked) else st.leading_keyword)),
            "text": code[:160],
            "control_flow": hit is None,
            "ddl_or_dml": hit is not None,
            "destructive": hit is not None and bool(sql_lex.DESTRUCTIVE.search(stripped)),
        })
    return out


def audit(migration_sql: str, ops: list[Any]) -> dict[str, Any]:
    """What the file contains that the op list does not account for. Pure function.

    Deterministic, standard library, no model involved. The report carries it whole so
    a reviewer can check the subtraction rather than trust it.
    """
    lexed = sql_lex.lex(migration_sql or "")
    statements = [s for s in lexed.statements if s.code.strip()]
    claimed = {getattr(op, "index", None) for op in ops}

    unaccounted = []
    for pos, st in enumerate(statements):
        if pos in claimed:
            continue
        unaccounted.append({
            "statement_index": pos,
            "keyword": st.leading_keyword,
            "start": st.span.start,
            "end": st.span.end,
            "text": re.sub(r"\s+", " ", st.code).strip()[:160],
            "destructive": st.is_destructive,
            "ddl_or_dml": st.is_ddl_or_dml,
        })

    procedural = []
    for pos, st in enumerate(statements):
        if not st.dollar_bodies or not PROCEDURAL_HEAD.match(st.code):
            continue
        for body in st.dollar_bodies:
            inner = _inner_statements(body.body)
            ddl = [s for s in inner if s["ddl_or_dml"] and not s["control_flow"]]
            procedural.append({
                "statement_index": pos,
                "tag": body.tag,
                "head": re.sub(r"\s+", " ", st.code[:80]).strip(),
                "start": body.span.start,
                "end": body.span.end,
                "body_statements": len(inner),
                "inner": inner,
                "ddl_inside": [s["excerpt"] for s in ddl],
                "destructive_inside": [s["excerpt"] for s in ddl if s["destructive"]],
            })

    significant, attributed = lexed.significant(), lexed.attributed()
    return {
        "lexed_statements": len(statements),
        "ops": len(ops),
        "unterminated": list(lexed.unterminated),
        "unaccounted": unaccounted,
        "procedural": procedural,
        "conservation": {
            "significant_chars": significant,
            "attributed_chars": attributed,
            "unattributed_chars": max(0, significant - attributed),
        },
        "clean": not lexed.unterminated and not unaccounted and not procedural
                 and significant == attributed,
    }


def legacy_loss(migration_sql: str) -> dict[str, Any]:
    """What the retired v13 splitter did to this file, for the red-team report.

    Kept because the size of the defect is the argument for the fix, and a number
    recomputed from the artefact under test beats a sentence about it. Imported by
    `eval/run_redteam2.py`, never by the pipeline.
    """
    from . import sql_parse

    fixed = [s for s in sql_lex.lex(migration_sql or "").statements if s.code.strip()]
    legacy = sql_parse.legacy_split_statements(migration_sql or "")
    return {
        "statements_in_file": len(fixed),
        "statements_v13_saw": len(legacy),
        "statements_lost": max(0, len(fixed) - len(legacy)),
        "phantom_statements": max(0, len(legacy) - len(fixed)),
    }
