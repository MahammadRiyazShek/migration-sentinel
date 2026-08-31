"""Deterministic parser for the PostgreSQL subset used by Migration Sentinel.

Design note: we deliberately do NOT ask a language model to "read" the schema or
the migration.  Structural facts (which column is dropped, which view depends on
it) are cheap to compute exactly and expensive to guess.  The model is reserved
for judgement and prose, never for facts.

Everything here is pure and side-effect free so it can be unit tested.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from . import sql_lex

# --------------------------------------------------------------------------
# statement splitting
# --------------------------------------------------------------------------


def legacy_strip_comments(sql: str) -> str:
    """The v13 comment stripper. RETIRED, kept because it is the artefact under test.

    It deletes from `--` to end of line unconditionally, including inside a string
    literal, which is how `'legacy -- do not touch'` became an unterminated quote that
    swallowed the two destructive statements after it.  See `sentinel/tools/sql_lex.py`.
    Reachable only through `legacy_split_statements`, which only the `no_text_conservation`
    ablation arm and `tools/parse_audit.legacy_loss` call.
    """
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    out = []
    for line in sql.splitlines():
        idx = line.find("--")
        out.append(line if idx < 0 else line[:idx])
    return "\n".join(out)


def strip_comments(sql: str) -> str:
    """Comments removed, literal-aware, via the scanner. Nested block comments included."""
    res = sql_lex.lex(sql or "")
    chars = list(sql or "")
    for span in res.comment_spans:
        for i in range(max(0, span.start), min(span.end, len(chars))):
            chars[i] = " "
    return "".join(chars)


def split_statements(sql: str) -> list[str]:
    """Top-level statements, comments removed. Delegates to the scanner.

    v14. Byte-identical to `legacy_split_statements` on all 84 schema, migration and
    rollback scripts in `eval/` (`tests/test_all.py::TestLexerParity`), which is why the
    swap moved no published number, and different from it on exactly the inputs the
    scanner exists for: dollar-quoted bodies, nested block comments, and a `--` inside a
    string literal.
    """
    return sql_lex.split_statements(sql)


def legacy_split_statements(sql: str) -> list[str]:
    """The v13 splitter. RETIRED. See `legacy_strip_comments` for what it does wrong."""
    sql = legacy_strip_comments(sql)
    stmts, buf, depth, quote = [], [], 0, None
    for ch in sql:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == ";" and depth == 0:
            stmt = "".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def ident(s: str) -> str:
    return s.strip().strip('"').strip().lower()


# --------------------------------------------------------------------------
# schema model
# --------------------------------------------------------------------------

PG_TO_SQLITE = {
    "serial": "INTEGER",
    "bigserial": "INTEGER",
    "int": "INTEGER",
    "int4": "INTEGER",
    "int8": "INTEGER",
    "integer": "INTEGER",
    "bigint": "INTEGER",
    "smallint": "INTEGER",
    "boolean": "INTEGER",
    "bool": "INTEGER",
    "text": "TEXT",
    "uuid": "TEXT",
    "jsonb": "TEXT",
    "json": "TEXT",
    "date": "TEXT",
    "timestamp": "TEXT",
    "timestamptz": "TEXT",
    "numeric": "REAL",
    "decimal": "REAL",
    "real": "REAL",
    "double": "REAL",
    "money": "REAL",
}


def sqlite_type(pg_type: str) -> str:
    base = pg_type.strip().lower()
    m = re.match(r"([a-z_ ]+?)\s*(\(([^)]*)\))?$", base)
    root = (m.group(1).strip() if m else base).replace("  ", " ")
    args = m.group(3) if m and m.group(3) else ""
    if root.startswith("varchar") or root.startswith("character varying") or root.startswith("char"):
        return f"VARCHAR({args})" if args else "TEXT"
    for key, val in PG_TO_SQLITE.items():
        if root == key or root.startswith(key + " "):
            return val
    return "TEXT"


@dataclass
class Column:
    name: str
    type: str
    nullable: bool = True
    default: str | None = None
    primary_key: bool = False
    unique: bool = False

    def clone(self) -> "Column":
        return Column(**self.__dict__)


@dataclass
class Constraint:
    name: str
    kind: str  # check | unique | foreign_key | primary_key
    expr: str
    columns: list[str] = field(default_factory=list)


@dataclass
class Table:
    name: str
    columns: dict[str, Column] = field(default_factory=dict)
    constraints: list[Constraint] = field(default_factory=list)
    row_estimate: int = 0

    def clone(self) -> "Table":
        t = Table(self.name, row_estimate=self.row_estimate)
        t.columns = {k: v.clone() for k, v in self.columns.items()}
        t.constraints = [Constraint(c.name, c.kind, c.expr, list(c.columns)) for c in self.constraints]
        return t


@dataclass
class View:
    name: str
    select_sql: str


@dataclass
class Index:
    name: str
    table: str
    columns: list[str]
    unique: bool = False


@dataclass
class Schema:
    tables: dict[str, Table] = field(default_factory=dict)
    views: dict[str, View] = field(default_factory=dict)
    indexes: dict[str, Index] = field(default_factory=dict)

    def clone(self) -> "Schema":
        s = Schema()
        s.tables = {k: v.clone() for k, v in self.tables.items()}
        s.views = {k: View(v.name, v.select_sql) for k, v in self.views.items()}
        s.indexes = {k: Index(i.name, i.table, list(i.columns), i.unique) for k, i in self.indexes.items()}
        return s


# A type name is one of a few multi-word Postgres spellings or a single word,
# optionally followed by a precision list and/or an array marker.  Matching this
# explicitly (instead of a greedy [\w ]+) keeps "NOT NULL UNIQUE" out of the type.
TYPE_PATTERN = (
    r"(?:double\s+precision|timestamp\s+with(?:out)?\s+time\s+zone"
    r"|character\s+varying|bit\s+varying|[a-zA-Z_]\w*)"
    r"(?:\s*\([^)]*\))?(?:\s*\[\])?"
)
COL_LEVEL_RE = re.compile(
    r"^(?P<name>\"?[a-zA-Z_][\w$]*\"?)\s+(?P<type>" + TYPE_PATTERN + r")(?P<rest>.*)$", re.S | re.I
)


def _split_top_level_commas(body: str) -> list[str]:
    parts, buf, depth, quote = [], [], 0, None
    for ch in body:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def parse_create_table(stmt: str) -> Table:
    m = re.match(r"create\s+table\s+(if\s+not\s+exists\s+)?(?P<name>\"?[\w$.]+\"?)\s*\((?P<body>.*)\)\s*$",
                 norm(stmt), flags=re.I | re.S)
    if not m:
        raise ValueError(f"cannot parse CREATE TABLE: {stmt[:80]}")
    table = Table(ident(m.group("name")))
    for part in _split_top_level_commas(m.group("body")):
        low = part.lower()
        if re.match(r"^(constraint\s+\S+\s+)?(check|unique|primary\s+key|foreign\s+key)\b", low):
            cm = re.match(r"^(constraint\s+(?P<cname>\S+)\s+)?(?P<kw>check|unique|primary\s+key|foreign\s+key)\s*(?P<expr>.*)$",
                          part, flags=re.I | re.S)
            kw = re.sub(r"\s+", "_", cm.group("kw").lower())
            cols = []
            inner = re.match(r"^\((?P<cols>[^)]*)\)", cm.group("expr").strip())
            if kw in ("unique", "primary_key") and inner:
                cols = [ident(c) for c in inner.group("cols").split(",")]
            cname = ident(cm.group("cname")) if cm.group("cname") else f"{table.name}_{kw}_{len(table.constraints)}"
            table.constraints.append(Constraint(cname, kw, norm(cm.group("expr")), cols))
            if kw == "primary_key":
                for c in cols:
                    if c in table.columns:
                        table.columns[c].primary_key = True
            continue
        cm = COL_LEVEL_RE.match(part.strip())
        if not cm:
            continue
        rest = cm.group("rest") or ""
        low_rest = rest.lower()
        default = None
        dm = re.search(r"default\s+(?P<val>'[^']*'|[\w.()':\-]+)", rest, flags=re.I)
        if dm:
            default = dm.group("val")
        col = Column(
            name=ident(cm.group("name")),
            type=norm(cm.group("type")),
            nullable="not null" not in low_rest and "primary key" not in low_rest,
            default=default,
            primary_key="primary key" in low_rest,
            unique="unique" in low_rest,
        )
        if col.type.lower().endswith("serial"):
            col.nullable = False
        table.columns[col.name] = col
        if "check" in low_rest:
            chk = re.search(r"check\s*(\([^;]*\))", rest, flags=re.I)
            if chk:
                table.constraints.append(
                    Constraint(f"{table.name}_{col.name}_check", "check", norm(chk.group(1)), [col.name])
                )
        if "unique" in low_rest:
            table.constraints.append(
                Constraint(f"{table.name}_{col.name}_key", "unique", f"({col.name})", [col.name])
            )
    return table


def parse_schema(sql: str, row_estimates: dict[str, int] | None = None) -> Schema:
    schema = Schema()
    for stmt in split_statements(sql):
        low = norm(stmt).lower()
        if low.startswith("create table"):
            t = parse_create_table(stmt)
            schema.tables[t.name] = t
        elif low.startswith("create view") or low.startswith("create or replace view"):
            m = re.match(r"create\s+(or\s+replace\s+)?view\s+(?P<name>\"?[\w$.]+\"?)\s+as\s+(?P<sel>.*)$",
                         norm(stmt), flags=re.I | re.S)
            if m:
                schema.views[ident(m.group("name"))] = View(ident(m.group("name")), norm(m.group("sel")))
        elif re.match(r"create\s+(unique\s+)?index", low):
            m = re.match(
                r"create\s+(?P<uniq>unique\s+)?index\s+(concurrently\s+)?(if\s+not\s+exists\s+)?"
                r"(?P<name>\"?[\w$.]+\"?)\s+on\s+(?P<table>\"?[\w$.]+\"?)\s*\((?P<cols>[^)]*)\)",
                norm(stmt), flags=re.I)
            if m:
                name = ident(m.group("name"))
                schema.indexes[name] = Index(
                    name, ident(m.group("table")), [ident(c) for c in m.group("cols").split(",")],
                    bool(m.group("uniq")))
    for name, rows in (row_estimates or {}).items():
        if ident(name) in schema.tables:
            schema.tables[ident(name)].row_estimate = rows
    return schema


# --------------------------------------------------------------------------
# migration operations
# --------------------------------------------------------------------------


@dataclass
class Op:
    kind: str
    sql: str
    index: int
    table: str | None = None
    column: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "table": self.table, "column": self.column,
            "detail": self.detail, "sql": self.sql, "index": self.index,
        }


# PostgreSQL maintenance commands that rewrite or exclusively lock a whole
# relation.  Documented family, not a per-case special case: every one of these
# takes ACCESS EXCLUSIVE for the duration and none of them is expressible as a
# structural schema change, which is why they get an op kind of their own.
# v14: statements that run a program rather than a single command. Matched on the
# statement head, so a `$$`-quoted default or a quoted piece of documentation stays a
# string rather than becoming a program.
PROCEDURAL_HEAD = re.compile(r"^\s*(do\b|create\s+(or\s+replace\s+)?(function|procedure)\b)", re.I)

MAINTENANCE_REWRITE = (
    r"(?P<cmd>cluster|vacuum\s+full|reindex(\s+(table|index|schema|database))?|"
    r"refresh\s+materialized\s+view)"
    r"(\s+(concurrently|verbose|analyze))*"
    r"(\s+(?P<table>\"?[\w$.]+\"?))?"
)


def _alter_actions(body: str) -> list[str]:
    return _split_top_level_commas(body)


def parse_migration(sql: str, legacy_split: bool = False) -> list[Op]:
    """Typed operations for one migration script.

    `legacy_split` restores the v13 splitter so the `no_text_conservation` ablation arm
    can reproduce v13 exactly and this layer can be priced like every other one here.
    Nothing in the shipped path passes it.
    """
    splitter = legacy_split_statements if legacy_split else split_statements
    ops: list[Op] = []
    for i, raw in enumerate(splitter(sql)):
        stmt = norm(raw)
        low = stmt.lower()
        if low.startswith(("begin", "commit", "rollback", "set ", "lock ")):
            ops.append(Op("transaction_control", stmt, i))
            continue
        m = re.match(r"alter\s+table\s+(if\s+exists\s+)?(?P<table>\"?[\w$.]+\"?)\s+(?P<body>.*)$", stmt, flags=re.I | re.S)
        if m:
            table = ident(m.group("table"))
            for action in _alter_actions(m.group("body")):
                al = action.lower()
                if am := re.match(r"add\s+column\s+(if\s+not\s+exists\s+)?(?P<col>\"?[\w$]+\"?)\s+(?P<type>" + TYPE_PATTERN + r")(?P<rest>.*)$", action, flags=re.I | re.S):
                    rest = am.group("rest") or ""
                    dm = re.search(r"default\s+(?P<val>'[^']*'|[\w.()':\-]+)", rest, flags=re.I)
                    ops.append(Op("add_column", stmt, i, table, ident(am.group("col")), {
                        "type": norm(am.group("type")),
                        "not_null": "not null" in rest.lower(),
                        "default": dm.group("val") if dm else None,
                        "unique": "unique" in rest.lower(),
                    }))
                elif am := re.match(r"drop\s+column\s+(if\s+exists\s+)?(?P<col>\"?[\w$]+\"?)", action, flags=re.I):
                    ops.append(Op("drop_column", stmt, i, table, ident(am.group("col")), {}))
                elif am := re.match(r"rename\s+column\s+(?P<old>\"?[\w$]+\"?)\s+to\s+(?P<new>\"?[\w$]+\"?)", action, flags=re.I):
                    ops.append(Op("rename_column", stmt, i, table, ident(am.group("old")),
                                  {"new_name": ident(am.group("new"))}))
                elif am := re.match(r"rename\s+to\s+(?P<new>\"?[\w$.]+\"?)", action, flags=re.I):
                    ops.append(Op("rename_table", stmt, i, table, None, {"new_name": ident(am.group("new"))}))
                elif am := re.match(r"alter\s+column\s+(?P<col>\"?[\w$]+\"?)\s+(?P<tail>.*)$", action, flags=re.I | re.S):
                    col, tail = ident(am.group("col")), am.group("tail").strip()
                    tl = tail.lower()
                    if tl.startswith("type") or tl.startswith("set data type"):
                        newtype = re.sub(r"^(set\s+data\s+)?type\s+", "", tail, flags=re.I)
                        newtype = re.sub(r"\s+using\s+.*$", "", newtype, flags=re.I)
                        ops.append(Op("alter_type", stmt, i, table, col, {"new_type": norm(newtype)}))
                    elif tl.startswith("set not null"):
                        ops.append(Op("set_not_null", stmt, i, table, col, {}))
                    elif tl.startswith("drop not null"):
                        ops.append(Op("drop_not_null", stmt, i, table, col, {}))
                    elif tl.startswith("set default"):
                        ops.append(Op("set_default", stmt, i, table, col,
                                      {"default": norm(re.sub(r"^set\s+default\s+", "", tail, flags=re.I))}))
                    elif tl.startswith("drop default"):
                        ops.append(Op("drop_default", stmt, i, table, col, {}))
                    else:
                        ops.append(Op("unknown_alter_column", stmt, i, table, col, {"tail": tail}))
                elif am := re.match(r"add\s+(constraint\s+(?P<cname>\"?[\w$]+\"?)\s+)?(?P<kw>check|unique|foreign\s+key|primary\s+key)\s*(?P<expr>.*)$", action, flags=re.I | re.S):
                    kw = re.sub(r"\s+", "_", am.group("kw").lower())
                    expr = norm(am.group("expr"))
                    cols = []
                    inner = re.match(r"^\((?P<cols>[^)]*)\)", expr)
                    if kw in ("unique", "primary_key") and inner:
                        cols = [ident(c) for c in inner.group("cols").split(",")]
                    ops.append(Op("add_constraint", stmt, i, table, cols[0] if cols else None, {
                        "constraint": ident(am.group("cname")) if am.group("cname") else f"{table}_{kw}_new",
                        "constraint_kind": kw, "expr": re.sub(r"\s+not\s+valid$", "", expr, flags=re.I),
                        "columns": cols, "not_valid": bool(re.search(r"not\s+valid", expr, flags=re.I)),
                    }))
                elif am := re.match(r"drop\s+constraint\s+(if\s+exists\s+)?(?P<cname>\"?[\w$]+\"?)", action, flags=re.I):
                    ops.append(Op("drop_constraint", stmt, i, table, None,
                                  {"constraint": ident(am.group("cname"))}))
                elif am := re.match(r"validate\s+constraint\s+(?P<cname>\"?[\w$]+\"?)", action, flags=re.I):
                    ops.append(Op("validate_constraint", stmt, i, table, None,
                                  {"constraint": ident(am.group("cname"))}))
                else:
                    ops.append(Op("unknown_alter", stmt, i, table, None, {"action": action}))
            continue
        if m := re.match(r"create\s+(?P<uniq>unique\s+)?index\s+(?P<conc>concurrently\s+)?(if\s+not\s+exists\s+)?(?P<name>\"?[\w$.]+\"?)\s+on\s+(?P<table>\"?[\w$.]+\"?)\s*\((?P<cols>[^)]*)\)", stmt, flags=re.I):
            ops.append(Op("create_index", stmt, i, ident(m.group("table")), None, {
                "name": ident(m.group("name")), "unique": bool(m.group("uniq")),
                "concurrently": bool(m.group("conc")),
                "columns": [ident(c) for c in m.group("cols").split(",")],
            }))
            continue
        if m := re.match(r"drop\s+index\s+(concurrently\s+)?(if\s+exists\s+)?(?P<name>\"?[\w$.]+\"?)", stmt, flags=re.I):
            ops.append(Op("drop_index", stmt, i, None, None, {"name": ident(m.group("name"))}))
            continue
        if m := re.match(r"create\s+(or\s+replace\s+)?view\s+(?P<name>\"?[\w$.]+\"?)\s+as\s+(?P<sel>.*)$", stmt, flags=re.I | re.S):
            ops.append(Op("create_view", stmt, i, None, None,
                          {"name": ident(m.group("name")), "select": norm(m.group("sel")),
                           "replace": bool(m.group(1))}))
            continue
        if m := re.match(r"drop\s+view\s+(if\s+exists\s+)?(?P<name>\"?[\w$.]+\"?)", stmt, flags=re.I):
            ops.append(Op("drop_view", stmt, i, None, None, {"name": ident(m.group("name"))}))
            continue
        if m := re.match(r"drop\s+table\s+(if\s+exists\s+)?(?P<name>\"?[\w$.]+\"?)", stmt, flags=re.I):
            ops.append(Op("drop_table", stmt, i, ident(m.group("name")), None, {}))
            continue
        if norm(stmt).lower().startswith("create table"):
            t = parse_create_table(stmt)
            ops.append(Op("create_table", stmt, i, t.name, None, {"table": t}))
            continue
        if m := re.match(r"update\s+(?P<table>\"?[\w$.]+\"?)\s+set\s+(?P<rest>.*)$", stmt, flags=re.I | re.S):
            ops.append(Op("dml_update", stmt, i, ident(m.group("table")), None, {
                "where": bool(re.search(r"\bwhere\b", stmt, flags=re.I)),
                "batched": bool(re.search(r"\b(limit|ctid|id\s*(>|between)|in\s*\(\s*select)", stmt, flags=re.I)),
            }))
            continue
        if m := re.match(r"delete\s+from\s+(?P<table>\"?[\w$.]+\"?)", stmt, flags=re.I):
            ops.append(Op("dml_delete", stmt, i, ident(m.group("table")), None,
                          {"where": bool(re.search(r"\bwhere\b", stmt, flags=re.I))}))
            continue
        if m := re.match(r"insert\s+into\s+(?P<table>\"?[\w$.]+\"?)", stmt, flags=re.I):
            ops.append(Op("dml_insert", stmt, i, ident(m.group("table")), None, {}))
            continue
        # v14: a procedural body. `DO $$ ... $$` and function bodies carry statements
        # that execute and that nothing here models; the retired splitter shredded them at
        # their inner semicolons. Given its own kind so `sentinel/rulebook.py` has to
        # classify it and `tools/parse_audit.py` can census what is inside.
        if PROCEDURAL_HEAD.match(stmt) and sql_lex.DOLLAR_TAG.search(raw):
            ops.append(Op("procedural_block", stmt, i, None, None,
                          {"head": norm(stmt)[:80],
                           "bodies": [b.tag for b in
                                      (sql_lex.lex(raw).statements or [None])[0].dollar_bodies]
                                     if sql_lex.lex(raw).statements else []}))
            continue
        if m := re.match(MAINTENANCE_REWRITE, stmt, flags=re.I):
            # Recognised by name, still not modelled structurally.  The op carries a
            # table so the lock rules can price it; apply_ops still records it as
            # unmodelled, so the coverage ledger keeps reporting it as a blind spot.
            ops.append(Op("maintenance_rewrite", stmt, i,
                          ident(m.group("table")) if m.group("table") else None, None,
                          {"command": re.sub(r"\s+", " ", m.group("cmd")).upper()}))
            continue
        ops.append(Op("unsupported", stmt, i, None, None, {}))
    return ops


def apply_ops(schema: Schema, ops: list[Op]) -> tuple[Schema, list[str]]:
    """Return the post-migration schema plus notes about ops we could not model."""
    s = schema.clone()
    notes: list[str] = []
    for op in ops:
        t = s.tables.get(op.table) if op.table else None
        if op.kind == "add_column" and t is not None:
            t.columns[op.column] = Column(
                op.column, op.detail.get("type", "text"),
                nullable=not op.detail.get("not_null"), default=op.detail.get("default"),
                unique=bool(op.detail.get("unique")))
        elif op.kind == "drop_column" and t is not None:
            t.columns.pop(op.column, None)
            t.constraints = [c for c in t.constraints if op.column not in c.columns
                             and not re.search(rf"\b{re.escape(op.column)}\b", c.expr)]
            for iname in [k for k, v in s.indexes.items() if v.table == t.name and op.column in v.columns]:
                s.indexes.pop(iname)
        elif op.kind == "rename_column" and t is not None and op.column in t.columns:
            col = t.columns.pop(op.column)
            col.name = op.detail["new_name"]
            t.columns[col.name] = col
            for c in t.constraints:
                c.columns = [op.detail["new_name"] if x == op.column else x for x in c.columns]
            for idx in s.indexes.values():
                if idx.table == t.name:
                    idx.columns = [op.detail["new_name"] if x == op.column else x for x in idx.columns]
        elif op.kind == "alter_type" and t is not None and op.column in t.columns:
            t.columns[op.column].type = op.detail["new_type"]
        elif op.kind == "set_not_null" and t is not None and op.column in t.columns:
            t.columns[op.column].nullable = False
        elif op.kind == "drop_not_null" and t is not None and op.column in t.columns:
            t.columns[op.column].nullable = True
        elif op.kind == "set_default" and t is not None and op.column in t.columns:
            t.columns[op.column].default = op.detail["default"]
        elif op.kind == "drop_default" and t is not None and op.column in t.columns:
            t.columns[op.column].default = None
        elif op.kind == "rename_table" and t is not None:
            s.tables.pop(t.name)
            t.name = op.detail["new_name"]
            s.tables[t.name] = t
        elif op.kind == "drop_table" and t is not None:
            s.tables.pop(t.name, None)
        elif op.kind == "create_table":
            newt: Table = op.detail["table"]
            s.tables[newt.name] = newt
        elif op.kind == "create_index":
            s.indexes[op.detail["name"]] = Index(op.detail["name"], op.table,
                                                op.detail["columns"], op.detail["unique"])
        elif op.kind == "drop_index":
            s.indexes.pop(op.detail["name"], None)
        elif op.kind == "create_view":
            s.views[op.detail["name"]] = View(op.detail["name"], op.detail["select"])
        elif op.kind == "drop_view":
            s.views.pop(op.detail["name"], None)
        elif op.kind == "add_constraint" and t is not None:
            t.constraints.append(Constraint(op.detail["constraint"], op.detail["constraint_kind"],
                                            op.detail["expr"], op.detail.get("columns", [])))
            if op.detail["constraint_kind"] == "unique" and op.detail.get("columns"):
                nm = op.detail["constraint"]
                s.indexes[nm] = Index(nm, t.name, op.detail["columns"], True)
        elif op.kind == "drop_constraint" and t is not None:
            t.constraints = [c for c in t.constraints if c.name != op.detail["constraint"]]
            s.indexes.pop(op.detail["constraint"], None)
        elif op.kind in ("dml_update", "dml_insert", "dml_delete", "transaction_control",
                         "validate_constraint"):
            pass
        else:
            notes.append(f"op {op.index} ({op.kind}) not modelled structurally: {op.sql[:60]}")
    return s, notes


def referenced_identifiers(sql: str) -> set[str]:
    """Lower-cased bare identifiers appearing in a query (over-approximate)."""
    return {w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z_0-9]*", sql)}
