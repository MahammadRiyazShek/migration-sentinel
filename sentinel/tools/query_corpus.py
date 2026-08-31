"""Static dependency lookup over the application query corpus.

The corpus is the set of SQL statements a real codebase issues against the
database (in practice: extracted from ORM logs, dbt models, BI definitions).
Here it is part of the case fixture so the whole thing stays reproducible.
"""
from __future__ import annotations

import re
from typing import Any

from .sql_parse import Op, Schema, referenced_identifiers

CRIT_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def touched_objects(ops: list[Op], schema: Schema) -> dict[str, set[str]]:
    """Tables and columns the migration touches, plus views that depend on them."""
    tables: set[str] = set()
    columns: set[str] = set()
    for op in ops:
        if op.table:
            tables.add(op.table)
        if op.column:
            columns.add(op.column)
        if op.kind == "rename_column":
            columns.add(op.detail["new_name"])
        if op.kind in ("create_view", "drop_view"):
            tables.add(op.detail["name"])
        for col in op.detail.get("columns", []) or []:
            columns.add(col)
    dependent_views = set()
    for view in schema.views.values():
        idents = referenced_identifiers(view.select_sql)
        if idents & tables or idents & columns or re.search(r"select\s+\*", view.select_sql, re.I) and idents & tables:
            dependent_views.add(view.name)
    return {"tables": tables, "columns": columns, "views": dependent_views}


def dependents(queries: list[dict[str, Any]], ops: list[Op], schema: Schema) -> list[dict[str, Any]]:
    """Queries that mention a touched table/column/view - the static blast radius."""
    touched = touched_objects(ops, schema)
    hits = []
    for q in queries:
        idents = referenced_identifiers(q["sql"])
        why = sorted((idents & touched["tables"]) | (idents & touched["columns"])
                     | (idents & touched["views"]))
        if why:
            hits.append({
                "query_id": q["id"], "service": q.get("service", "unknown"),
                "criticality": q.get("criticality", "medium"),
                "matched": why, "uses_select_star": bool(re.search(r"select\s+\*", q["sql"], re.I)),
                "label": q.get("label", ""),
            })
    return hits


def blast_score(hits: list[dict[str, Any]]) -> int:
    return sum(CRIT_WEIGHT.get(h["criticality"], 2) for h in hits)


# --------------------------------------------------------------------------
# v13: access paths.  Added because `DROP INDEX` was the one op kind whose whole
# risk lives in the query *plan* rather than in the query *result*, and every other
# tool here answers questions about results.
# --------------------------------------------------------------------------

# Clauses where a column's presence means the planner wants an index on it. A column
# in the SELECT list is a projection and costs nothing to fetch; a column in a WHERE,
# JOIN, ORDER BY or GROUP BY is a lookup, a sort or a grouping, and those are what an
# index serves.
FILTER_CLAUSES = re.compile(
    r"\b(where|join|on|order\s+by|group\s+by|having)\b(?P<body>.*?)"
    r"(?=\b(where|join|on|order\s+by|group\s+by|having|limit|returning|union)\b|$)",
    re.I | re.S)


def filter_columns(sql: str) -> set[str]:
    """Columns this statement uses as a lookup, sort or grouping key.

    Deliberately over-approximate on the clause split and exact on the column match:
    a false positive here means a reviewer is told an index might matter when it does
    not, and a false negative means an index is dropped under a live query.
    """
    out: set[str] = set()
    for m in FILTER_CLAUSES.finditer(sql or ""):
        body = m.group("body")
        for tok in re.findall(r"[A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)?", body):
            out.add(tok.split(".")[-1].lower())
    return out - SQL_WORDS


SQL_WORDS = {
    "and", "or", "not", "in", "is", "null", "like", "ilike", "between", "exists", "case", "when",
    "then", "else", "end", "asc", "desc", "true", "false", "select", "from", "as", "distinct",
    "count", "sum", "avg", "min", "max", "coalesce", "date", "interval", "now", "current_date",
    "current_timestamp", "cast", "left", "right", "inner", "outer", "full", "cross", "lateral",
    "nulls", "first", "last", "any", "all", "some",
}


def access_path_users(queries: list[dict[str, Any]], table: str,
                      columns: list[str]) -> list[dict[str, Any]]:
    """Corpus statements that use `columns` of `table` as a lookup, sort or grouping key.

    This is the evidence behind ACCESS_PATH_REMOVED: not "something mentions this
    column" but "something asks the planner to find rows by it".
    """
    cols = {c.lower() for c in columns}
    hits: list[dict[str, Any]] = []
    for q in queries:
        sql = q.get("sql", "")
        idents = referenced_identifiers(sql)
        if table and table.lower() not in idents:
            continue
        used = sorted(cols & filter_columns(sql))
        if not used:
            continue
        hits.append({
            "query_id": q["id"], "service": q.get("service", "unknown"),
            "criticality": q.get("criticality", "medium"),
            "label": q.get("label", ""), "columns": used,
            "clause_excerpt": _clause_excerpt(sql, used),
        })
    return sorted(hits, key=lambda h: (-CRIT_WEIGHT.get(h["criticality"], 2), h["query_id"]))


def _clause_excerpt(sql: str, columns: list[str]) -> str:
    """The fragment of the statement that names the column, so the packet quotes evidence."""
    for col in columns:
        m = re.search(rf"\b(where|join|on|order\s+by|group\s+by|having)\b[^;]{{0,80}}?\b{re.escape(col)}\b",
                      sql, flags=re.I | re.S)
        if m:
            return re.sub(r"\s+", " ", m.group(0)).strip()[:120]
    return re.sub(r"\s+", " ", sql).strip()[:120]
