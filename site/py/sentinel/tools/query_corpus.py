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
