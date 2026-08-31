"""Shadow-database replay: the tool that turns opinions into evidence.

We materialise the pre- and post-migration schema in two throwaway in-memory
SQLite databases, seed them with the case fixture rows, then execute every query
in the application query corpus against both.  A query that runs before and
fails after is not a guess about risk: it is a reproduced failure with the
engine's own error message attached.

Deliberate limitations (documented, not hidden):
  * SQLite stands in for PostgreSQL, so lock behaviour, MVCC and planner effects
    are NOT observable here.  Those hazards are covered by the static rules in
    sentinel/agents/risk_officer.py, which is exactly why the final pipeline
    keeps both layers.
  * Fixture data is small and synthetic; volume-dependent hazards are estimated
    from the declared row estimates, never measured.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from .sql_parse import Op, Schema, sqlite_type

NARROWING = {
    ("numeric", "integer"), ("numeric", "int"), ("numeric", "bigint"),
    ("real", "integer"), ("double precision", "integer"),
    ("bigint", "integer"), ("bigint", "smallint"), ("integer", "smallint"),
    ("text", "varchar"), ("text", "character varying"),
}


def _root(t: str) -> str:
    return t.split("(")[0].strip().lower()


def _len_arg(t: str) -> int | None:
    if "(" in t and ")" in t:
        inner = t[t.index("(") + 1:t.rindex(")")].split(",")[0].strip()
        return int(inner) if inner.isdigit() else None
    return None


def is_narrowing(old_type: str, new_type: str) -> bool:
    """Whether `old_type -> new_type` can refuse or truncate a value that fits today.

    Public because the coverage ledger needs the same answer this module uses: v6
    found, on the held-out set, that a narrowing whose offenders happen to be absent
    from the fixture was reported as a low-severity note with no blind spot declared.
    Two callers, one definition.
    """
    if (_root(old_type), _root(new_type)) in NARROWING:
        return True
    new_len, old_len = _len_arg(new_type), _len_arg(old_type)
    return new_len is not None and (old_len is None or new_len < old_len)


def _numeric_limit(new_type: str) -> float | None:
    """For numeric(p,s), the first magnitude the target type cannot hold.

    v6, from the held-out set: `numeric(12,2) -> numeric(8,2)` was scanned as if the
    only thing precision could do was truncate a string. It cannot hold 1,000,000.00,
    and the migration errors on the row rather than rounding it.
    """
    if _root(new_type) not in ("numeric", "decimal"):
        return None
    args = new_type[new_type.index("(") + 1:new_type.rindex(")")].split(",") \
        if "(" in new_type and ")" in new_type else []
    digits = [a.strip() for a in args if a.strip().isdigit()]
    if not digits:
        return None
    precision = int(digits[0])
    scale = int(digits[1]) if len(digits) > 1 else 0
    return float(10 ** max(0, precision - scale))


def offending_values(values: list[Any], new_type: str) -> list[Any]:
    """Values that would not survive a change to `new_type`, from the rows supplied."""
    new_len = _len_arg(new_type)
    limit = _numeric_limit(new_type)
    out = []
    for val in values:
        if val is None:
            continue
        if limit is not None and isinstance(val, (int, float)) and abs(float(val)) >= limit:
            out.append(val)
        elif limit is None and new_len is not None and isinstance(val, str) and len(val) > new_len:
            out.append(val)
        elif _root(new_type) in ("integer", "int", "bigint", "smallint") \
                and isinstance(val, (int, float)) and float(val) != int(float(val)):
            out.append(val)
    return out


def ddl_for(schema: Schema) -> list[str]:
    stmts: list[str] = []
    for table in schema.tables.values():
        cols = []
        pk = [c.name for c in table.columns.values() if c.primary_key]
        for col in table.columns.values():
            piece = f'"{col.name}" {sqlite_type(col.type)}'
            if not col.nullable and len(pk) <= 1:
                piece += " NOT NULL"
            if col.default is not None:
                piece += f" DEFAULT {col.default}"
            cols.append(piece)
        for con in table.constraints:
            if con.kind == "check":
                cols.append(f"CONSTRAINT \"{con.name}\" CHECK {con.expr}")
            elif con.kind == "unique" and con.columns:
                quoted = ", ".join(f'"{c}"' for c in con.columns)
                cols.append(f"CONSTRAINT \"{con.name}\" UNIQUE ({quoted})")
        if pk:
            cols.append("PRIMARY KEY (" + ", ".join(f'"{c}"' for c in pk) + ")")
        stmts.append(f'CREATE TABLE "{table.name}" (\n  ' + ",\n  ".join(cols) + "\n)")
    for idx in schema.indexes.values():
        if idx.table not in schema.tables:
            continue
        uniq = "UNIQUE " if idx.unique else ""
        quoted = ", ".join(f'"{c}"' for c in idx.columns)
        stmts.append(f'CREATE {uniq}INDEX "{idx.name}" ON "{idx.table}" ({quoted})')
    for view in schema.views.values():
        stmts.append(f'CREATE VIEW "{view.name}" AS {view.select_sql}')
    return stmts


@dataclass
class QueryOutcome:
    id: str
    ok: bool
    error: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: int = 0


@dataclass
class ReplayReport:
    materialised: bool
    schema_errors: list[str] = field(default_factory=list)
    data_errors: list[str] = field(default_factory=list)
    pre: dict[str, QueryOutcome] = field(default_factory=dict)
    post: dict[str, QueryOutcome] = field(default_factory=dict)
    broken: list[dict[str, Any]] = field(default_factory=list)
    column_drift: list[dict[str, Any]] = field(default_factory=list)
    rowcount_drift: list[dict[str, Any]] = field(default_factory=list)
    data_loss: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "materialised": self.materialised,
            "schema_errors": self.schema_errors,
            "data_errors": self.data_errors,
            "broken": self.broken,
            "column_drift": self.column_drift,
            "rowcount_drift": self.rowcount_drift,
            "data_loss": self.data_loss,
            "queries_run": len(self.post),
            "queries_ok_before": sum(1 for o in self.pre.values() if o.ok),
            "queries_ok_after": sum(1 for o in self.post.values() if o.ok),
        }


def _connect(schema: Schema) -> tuple[sqlite3.Connection, list[str]]:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    errors: list[str] = []
    for stmt in ddl_for(schema):
        try:
            conn.execute(stmt)
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            errors.append(f"{type(exc).__name__}: {exc} while running: {stmt.splitlines()[0]}")
    return conn, errors


def _seed(conn: sqlite3.Connection, schema: Schema, seed: dict[str, list[dict[str, Any]]]) -> list[str]:
    errors: list[str] = []
    for table_name, rows in seed.items():
        table = schema.tables.get(table_name)
        if table is None:
            continue
        for row in rows:
            cols = [c for c in row if c in table.columns]
            placeholders = ", ".join("?" for _ in cols)
            quoted = ", ".join(f'"{c}"' for c in cols)
            try:
                conn.execute(f'INSERT INTO "{table_name}" ({quoted}) VALUES ({placeholders})',
                             [row[c] for c in cols])
            except sqlite3.Error as exc:
                errors.append(f'seed {table_name}: {exc}')
    conn.commit()
    return errors


def _run_queries(conn: sqlite3.Connection, queries: list[dict[str, Any]]) -> dict[str, QueryOutcome]:
    out: dict[str, QueryOutcome] = {}
    for q in queries:
        qid = q["id"]
        try:
            conn.execute("SAVEPOINT probe")
            cur = conn.execute(q["sql"])
            cols = [d[0] for d in cur.description] if cur.description else []
            fetched = cur.fetchall() if cur.description else []
            out[qid] = QueryOutcome(qid, True, None, cols, len(fetched))
            conn.execute("ROLLBACK TO probe")
            conn.execute("RELEASE probe")
        except sqlite3.Error as exc:
            out[qid] = QueryOutcome(qid, False, f"{type(exc).__name__}: {exc}")
            try:
                conn.execute("ROLLBACK TO probe")
                conn.execute("RELEASE probe")
            except sqlite3.Error:
                pass
    return out


def _rename_map(ops: list[Op]) -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    tables: dict[str, str] = {}
    columns: dict[tuple[str, str], str] = {}
    for op in ops:
        if op.kind == "rename_table":
            tables[op.table] = op.detail["new_name"]
        elif op.kind == "rename_column":
            columns[(op.table, op.column)] = op.detail["new_name"]
    return tables, columns


def _copy_data(pre: sqlite3.Connection, post: sqlite3.Connection, pre_schema: Schema,
               post_schema: Schema, ops: list[Op]) -> list[str]:
    """Move fixture rows into the post-migration shape, reporting real failures."""
    errors: list[str] = []
    table_renames, column_renames = _rename_map(ops)
    for name, table in pre_schema.tables.items():
        target_name = table_renames.get(name, name)
        target = post_schema.tables.get(target_name)
        if target is None:
            continue
        mapping = {}
        for col in table.columns:
            new_col = column_renames.get((name, col), col)
            if new_col in target.columns:
                mapping[col] = new_col
        if not mapping:
            continue
        src_cols = list(mapping)
        rows = pre.execute(f'SELECT {", ".join(chr(34)+c+chr(34) for c in src_cols)} FROM "{name}"').fetchall()
        dst_cols = [mapping[c] for c in src_cols]
        quoted = ", ".join(f'"{c}"' for c in dst_cols)
        placeholders = ", ".join("?" for _ in dst_cols)
        for row in rows:
            try:
                post.execute(f'INSERT INTO "{target_name}" ({quoted}) VALUES ({placeholders})', row)
            except sqlite3.Error as exc:
                errors.append(f'backfill {target_name}: {exc} (row={dict(zip(dst_cols, row))})')
    post.commit()
    return errors


def _dml(conn: sqlite3.Connection, ops: list[Op]) -> list[str]:
    errors: list[str] = []
    for op in ops:
        if op.kind in ("dml_update", "dml_insert", "dml_delete"):
            try:
                conn.execute(op.sql)
            except sqlite3.Error as exc:
                errors.append(f"migration DML failed (stmt {op.index}): {exc} :: {op.sql[:90]}")
    conn.commit()
    return errors


def _data_loss(pre: sqlite3.Connection, pre_schema: Schema, ops: list[Op]) -> list[dict[str, Any]]:
    """Check narrowing type changes against the fixture rows we actually have."""
    findings: list[dict[str, Any]] = []
    for op in ops:
        if op.kind != "alter_type":
            continue
        table = pre_schema.tables.get(op.table)
        if not table or op.column not in table.columns:
            continue
        old, new = table.columns[op.column].type, op.detail["new_type"]
        if not is_narrowing(old, new):
            continue
        rows = pre.execute(f'SELECT "{op.column}" FROM "{op.table}"').fetchall()
        offenders = offending_values([r[0] for r in rows], new)
        findings.append({
            "table": op.table, "column": op.column, "from": old, "to": new,
            "rows_checked": len(rows), "offending_samples": offenders[:5],
            "offending_rows": len(offenders),
        })
    return findings


def replay(pre_schema: Schema, post_schema: Schema, ops: list[Op],
           seed: dict[str, list[dict[str, Any]]], queries: list[dict[str, Any]]) -> ReplayReport:
    pre_conn, pre_errs = _connect(pre_schema)
    seed_errs = _seed(pre_conn, pre_schema, seed)
    post_conn, post_errs = _connect(post_schema)
    report = ReplayReport(materialised=not post_errs, schema_errors=pre_errs + post_errs)
    report.data_errors = seed_errs
    report.data_errors += _copy_data(pre_conn, post_conn, pre_schema, post_schema, ops)
    report.data_errors += _dml(post_conn, ops)
    report.data_loss = _data_loss(pre_conn, pre_schema, ops)

    # views are lazily validated by SQLite, so probe them explicitly
    view_probes = [{"id": f"__view__{v}", "sql": f'SELECT * FROM "{v}" LIMIT 1',
                    "service": "database", "criticality": "high", "label": f"view {v}"}
                   for v in sorted(set(pre_schema.views) | set(post_schema.views))]
    all_queries = list(queries) + view_probes

    report.pre = _run_queries(pre_conn, [q for q in all_queries
                                         if not q["id"].startswith("__view__")
                                         or q["id"][8:] in pre_schema.views])
    report.post = _run_queries(post_conn, [q for q in all_queries
                                           if not q["id"].startswith("__view__")
                                           or q["id"][8:] in post_schema.views])
    by_id = {q["id"]: q for q in all_queries}
    for qid, after in report.post.items():
        before = report.pre.get(qid)
        meta = by_id[qid]
        if before and before.ok and not after.ok:
            report.broken.append({
                "query_id": qid, "service": meta.get("service", "unknown"),
                "criticality": meta.get("criticality", "medium"),
                "label": meta.get("label", ""), "error": after.error,
                "sql": meta["sql"],
            })
        elif before and before.ok and after.ok:
            if before.columns and after.columns and before.columns != after.columns:
                report.column_drift.append({
                    "query_id": qid, "service": meta.get("service", "unknown"),
                    "criticality": meta.get("criticality", "medium"),
                    "before": before.columns, "after": after.columns,
                    "removed": [c for c in before.columns if c not in after.columns],
                    "added": [c for c in after.columns if c not in before.columns],
                    "sql": meta["sql"],
                })
            if before.rows != after.rows:
                report.rowcount_drift.append({
                    "query_id": qid, "service": meta.get("service", "unknown"),
                    "before_rows": before.rows, "after_rows": after.rows,
                    "sql": meta["sql"],
                })
    for qid, before in report.pre.items():
        if qid not in report.post and before.ok:
            report.broken.append({
                "query_id": qid, "service": by_id[qid].get("service", "unknown"),
                "criticality": "high", "label": by_id[qid].get("label", ""),
                "error": "object removed by migration (view or table no longer exists)",
                "sql": by_id[qid]["sql"],
            })
    pre_conn.close()
    post_conn.close()
    return report
