"""A lexical scanner for the migration text itself, independent of what parses it.

SUPERVISOR LOG (v14), carried at the top of the file that acts on it
-------------------------------------------------------------------
Thirteen passes audited what this pipeline says, and one audited what it inspects.
This one audited what it *reads*, and that is where the worst defect in the
repository was sitting the whole time.

  R1  THE STATEMENT LOSS.  `strip_comments` deleted from `--` to end of line
      unconditionally, including inside a string literal.  So

          UPDATE invoices SET note = 'legacy -- do not touch' WHERE note IS NULL;
          ALTER TABLE invoices DROP COLUMN legacy_total;
          DROP TABLE invoice_archive;

      became one statement.  The comment stripper cut the literal in half, leaving
      an unterminated quote; `split_statements` then treated every remaining
      character in the file - both destructive statements, both semicolons - as
      the inside of that string.  `parse_migration` returned a single `dml_update`
      op.  Not a wrong severity, not a missed rule: **the DROP COLUMN and the DROP
      TABLE were never presented to any rule, to replay, or to the coverage
      ledger.**  A reviewer reads a packet about a third of a migration and the
      other two thirds are the outage.

  R2  WHERE v13 STOPPED, EXACTLY.  `sentinel/rulebook.py` partitions every kind
      `parse_migration` can emit and fails a test if the parser learns another one.
      It is an exhaustive audit of the *op list*.  R1 never reaches the op list.
      The arithmetic v13 published - enumerate what your tool can parse, subtract
      what any part of it inspects, publish the remainder - takes the parse as the
      universe, and the parse is a lossy function of the file.  Three releases
      found "X is a sample of Y" one level up each time (corpus/consumers v1,
      fixture/data v6, rules/hazards v13).  This is the fourth, and it sits
      upstream of all three: **the parse is a sample of the text.**

  R3  THE FALSE-POSITIVE DIRECTION, WHICH IS THE SAME BUG.  Postgres nests block
      comments.  A non-greedy /* ... */ regex does not.  So a superseded statement
      commented out with an inner comment inside it left a live
      `ALTER TABLE ... DROP COLUMN` behind after the first `*/`, and the pipeline
      blocked a migration whose destructive statement is commented out.  Same
      defect, opposite sign.  A tool that invents a blocker out of a comment gets
      switched off, and a switched-off tool has recall zero.

WHAT THIS MODULE IS
-------------------
The scanner Postgres would recognise, over the raw bytes, with spans:

    '...'         single-quoted literal, '' escape
    E'...'        escape-string literal, backslash escapes
    "..."         quoted identifier, "" escape
    $tag$...$tag$ dollar-quoted body, any tag, no escapes inside - which is why
                  migration frameworks use it for procedural bodies, and why a
                  naive splitter shreds it at the semicolons inside
    -- ...        line comment, to end of line
    /* ... */     block comment, NESTED, as Postgres specifies

It answers three questions nothing here could answer before:

    statements      the top-level statements, each with its source span, so the op
                    list can be reconciled against the file rather than trusted as
                    the file
    unterminated    a literal, identifier or comment that never closes.  Postgres
                    rejects the script; the old splitter silently ate the rest of
                    it.  Now a fact with a span attached
    dollar_bodies   procedural bodies, whose contents execute and which no
                    structural parser in this repository models

WHY IT IS A SEPARATE MODULE FROM sql_parse
------------------------------------------
Because the point is reconciliation, and a reconciliation between a thing and
itself proves nothing.  `sql_parse.parse_migration` consumes this scanner for
splitting - that is the fix for R1 and R3 - and `sentinel/tools/parse_audit.py`
re-derives the statement inventory from the same scanner and checks that the op
list accounts for every statement in it.  Two consumers of one scanner is not
independence; what makes the audit worth having is the division of labour.  The
scanner counts statements and the parser classifies them, and a statement the
parser silently declines to classify is exactly what R1 was.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It evaluates nothing and it decides nothing is a hazard.  It reports spans.  Every
judgement built on it lives in `parse_audit.py`, in the risk rules or in the
coverage ledger, where an ablation arm can switch it off and price it like every
other layer here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# A dollar-quote tag: $$ or $ident$. `$1` (a positional parameter) must not match,
# which is why the tag body requires a leading letter or underscore.
DOLLAR_TAG = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")

# Leading keyword of a statement, for the reconciliation census. Read off the scanned
# code text, never off the raw source, so a keyword inside a comment or inside a string
# literal cannot become a statement. R3 is that mistake in one line.
LEADING_KEYWORD = re.compile(r"^\s*([A-Za-z][A-Za-z_]*(?:\s+[A-Za-z][A-Za-z_]*)?)", re.I)

# Statement shapes that change schema or data. Used to describe what a statement *is*,
# never to decide that it is dangerous - that is the rules' job, on a parsed op.
DDL_OR_DML = re.compile(
    r"^\s*(alter|drop|create|truncate|rename|update|delete|insert|grant|revoke|"
    r"cluster|vacuum|reindex|refresh|comment|do|call|lock|copy|merge|analyze)\b", re.I)

DESTRUCTIVE = re.compile(
    r"\b(drop\s+(table|column|view|index|constraint|schema|sequence|type|not\s+null|default)|"
    r"truncate\b|rename\s+(to|column)|set\s+data\s+type|alter\s+column)", re.I)


@dataclass(frozen=True)
class Span:
    start: int
    end: int

    def __len__(self) -> int:
        return max(0, self.end - self.start)


@dataclass
class DollarBody:
    """A dollar-quoted body: the thing a naive splitter shreds at its inner semicolons."""
    tag: str
    body: str
    span: Span
    body_span: Span


@dataclass
class LexedStatement:
    index: int
    span: Span
    raw: str                 # exactly as written, comments and all
    code: str                # comments blanked to spaces, literals left intact
    dollar_bodies: list[DollarBody] = field(default_factory=list)

    @property
    def leading_keyword(self) -> str:
        m = LEADING_KEYWORD.match(self.code)
        return re.sub(r"\s+", " ", m.group(1)).lower() if m else ""

    @property
    def is_ddl_or_dml(self) -> bool:
        return bool(DDL_OR_DML.match(self.code))

    @property
    def is_destructive(self) -> bool:
        return bool(DESTRUCTIVE.search(self.code))


@dataclass
class LexResult:
    source: str
    statements: list[LexedStatement] = field(default_factory=list)
    comment_spans: list[Span] = field(default_factory=list)
    literal_spans: list[Span] = field(default_factory=list)
    unterminated: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.unterminated

    def dollar_bodies(self) -> list[DollarBody]:
        return [b for s in self.statements for b in s.dollar_bodies]

    def attributed(self) -> int:
        """Non-whitespace characters that sit inside a statement or inside a comment.

        The conservation quantity. Short of `significant()` means some text in the file
        was read by nobody - the R1 condition stated as arithmetic rather than as a
        story about one probe.
        """
        covered = bytearray(len(self.source))
        for sp in [s.span for s in self.statements] + self.comment_spans:
            for i in range(max(0, sp.start), min(sp.end, len(self.source))):
                covered[i] = 1
        return sum(1 for i, ch in enumerate(self.source)
                   if not ch.isspace() and ch != ";" and covered[i])

    def significant(self) -> int:
        return sum(1 for ch in self.source if not ch.isspace() and ch != ";")


def lex(sql: str) -> LexResult:
    """Scan `sql` into top-level statements, comments, literals and dollar bodies.

    Pure, side-effect free, single pass, standard library only. Never raises on
    malformed input: an unterminated construct is reported as a fact with a span,
    because the failure this module exists to fix was a malformed literal handled
    silently.
    """
    sql = sql or ""
    res = LexResult(source=sql)
    n = len(sql)
    i = 0
    stmt_start = 0
    depth = 0
    bodies: list[DollarBody] = []
    blanked: list[Span] = []   # comment spans inside the statement being scanned

    def flush(end: int, consumed_semicolon: bool) -> None:
        nonlocal stmt_start, bodies, blanked
        raw = sql[stmt_start:end]
        if raw.strip():
            chars = list(raw)
            for sp in blanked:
                for k in range(sp.start - stmt_start, min(sp.end, end) - stmt_start):
                    if 0 <= k < len(chars):
                        chars[k] = " "
            res.statements.append(LexedStatement(
                index=len(res.statements),
                span=Span(stmt_start, end),
                raw=raw,
                code="".join(chars),
                dollar_bodies=list(bodies),
            ))
        bodies = []
        blanked = []
        stmt_start = end + (1 if consumed_semicolon else 0)

    while i < n:
        ch = sql[i]

        # ---- line comment -------------------------------------------------
        if ch == "-" and sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j < 0 else j
            res.comment_spans.append(Span(i, j))
            blanked.append(Span(i, j))
            i = j
            continue

        # ---- block comment, nested, as Postgres specifies -----------------
        if ch == "/" and sql.startswith("/*", i):
            j, cdepth = i + 2, 1
            while j < n and cdepth:
                if sql.startswith("/*", j):
                    cdepth += 1
                    j += 2
                elif sql.startswith("*/", j):
                    cdepth -= 1
                    j += 2
                else:
                    j += 1
            if cdepth:
                res.unterminated.append({
                    "kind": "block_comment", "start": i, "end": n, "text": sql[i:i + 80],
                    "why": "a /* block comment never closes, so Postgres rejects the script and "
                           "every statement after this point was read by nothing",
                })
            res.comment_spans.append(Span(i, j))
            blanked.append(Span(i, j))
            i = j
            continue

        # ---- dollar-quoted body -------------------------------------------
        if ch == "$":
            m = DOLLAR_TAG.match(sql, i)
            if m:
                tag = m.group(0)
                close = sql.find(tag, m.end())
                if close < 0:
                    res.unterminated.append({
                        "kind": "dollar_string", "start": i, "end": n, "text": sql[i:i + 80],
                        "why": f"a {tag}-quoted body never closes, so every statement after this "
                               f"point is inside a string as far as Postgres is concerned",
                    })
                    res.literal_spans.append(Span(i, n))
                    i = n
                    continue
                whole = Span(i, close + len(tag))
                bodies.append(DollarBody(tag=tag, body=sql[m.end():close],
                                         span=whole, body_span=Span(m.end(), close)))
                res.literal_spans.append(whole)
                i = whole.end
                continue

        # ---- single-quoted literal, '' escape, E'' backslash escapes ------
        if ch == "'":
            escape_string = i > 0 and sql[i - 1] in "Ee" and (
                i == 1 or not (sql[i - 2].isalnum() or sql[i - 2] == "_"))
            j, closed = i + 1, False
            while j < n:
                if escape_string and sql[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    closed = True
                    j += 1
                    break
                j += 1
            if not closed:
                res.unterminated.append({
                    "kind": "string", "start": i, "end": n, "text": sql[i:i + 80],
                    "why": "a single-quoted literal never closes, so Postgres rejects the script "
                           "and everything after the quote was read as string content",
                })
                res.literal_spans.append(Span(i, n))
                i = n
                continue
            res.literal_spans.append(Span(i, j))
            i = j
            continue

        # ---- quoted identifier, "" escape ---------------------------------
        if ch == '"':
            j, closed = i + 1, False
            while j < n:
                if sql[j] == '"':
                    if j + 1 < n and sql[j + 1] == '"':
                        j += 2
                        continue
                    closed = True
                    j += 1
                    break
                j += 1
            if not closed:
                res.unterminated.append({
                    "kind": "quoted_identifier", "start": i, "end": n, "text": sql[i:i + 80],
                    "why": "a double-quoted identifier never closes, so Postgres rejects the "
                           "script and everything after it was read as part of a name",
                })
                res.literal_spans.append(Span(i, n))
                i = n
                continue
            res.literal_spans.append(Span(i, j))
            i = j
            continue

        # ---- structure ----------------------------------------------------
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            flush(i, consumed_semicolon=True)
            i += 1
            continue
        i += 1

    flush(n, consumed_semicolon=False)
    return res


def split_statements(sql: str) -> list[str]:
    """Statement texts with comments removed. Drop-in for the retired regex splitter.

    Verified byte-identical to the v13 splitter on every schema, migration and rollback
    script in `eval/` - `tests/test_all.py::TestLexerParity` - which is the only reason
    this could be swapped in underneath 28 labelled cases without moving a published
    number.
    """
    return [s.code.strip() for s in lex(sql).statements if s.code.strip()]
