"""Offline, deterministic model stand-in.

WHY THIS EXISTS - read before quoting any number from this repo
---------------------------------------------------------------
The evaluation must be runnable by a judge on a clean machine with no API key,
no network and no spend, and it must return byte-identical numbers every time.
So the default "model" is this scripted stand-in, not a hosted LLM.

It is not a strawman and it is not pretending to be a frontier model:

  * In `baseline_review` mode it implements a *generous* single-pass reviewer.
    It flags every hazard that is visible in the text of the migration itself -
    all destructive DDL, missing CONCURRENTLY, NOT NULL without a default,
    unbatched backfills, type changes, missing rollback - which is more than
    most humans catch on a first read.  What it cannot do is know things that
    are not in front of it: which application queries exist, what the data
    looks like, or how big the table is.  Those misses are the honest,
    structural difference between "read the diff" and "run the diff", and they
    are the entire thesis of this project.
  * In agent modes it only ever writes prose.  Every hazard, severity and
    remediation in the final report is produced by tools in sentinel/tools/,
    so swapping this stand-in for a real model cannot change the primary
    metric - only the wording of the report.

Run the identical prompts against a hosted model with
`--provider openai --model gpt-4.1-mini` (see sentinel/llm/remote.py).
"""
from __future__ import annotations

import re
from typing import Any

from ..hazards import HAZARDS
from .base import BaseLLM, LLMResponse, approx_tokens, price


def _find(sql: str, pattern: str) -> bool:
    return bool(re.search(pattern, sql, flags=re.I))


def baseline_hazards(migration_sql: str, schema_sql: str | None,
                     rollback_sql: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def add(code: str, severity: str, note: str) -> None:
        if not any(h["code"] == code for h in out):
            out.append({"code": code, "severity": severity, "note": note})

    if _find(migration_sql, r"drop\s+column") or _find(migration_sql, r"drop\s+table"):
        add("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high",
            "The diff drops a column or table in a single step; old application code will break.")
    if _find(migration_sql, r"rename\s+(column|to)"):
        add("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high",
            "A rename is not backwards compatible with the currently deployed code.")
    if _find(migration_sql, r"create\s+(unique\s+)?index") and not _find(migration_sql, r"concurrently"):
        add("INDEX_LOCK_NO_CONCURRENT", "high",
            "CREATE INDEX without CONCURRENTLY takes a lock that blocks writes.")
    if _find(migration_sql, r"create\s+unique\s+index") or _find(migration_sql, r"add\s+(constraint\s+\S+\s+)?unique"):
        add("UNIQUE_VIOLATION_EXISTING_DATA", "high",
            "Adding uniqueness may fail if duplicates already exist - please check first.")
    if (_find(migration_sql, r"set\s+not\s+null")
            or (_find(migration_sql, r"add\s+column[^;]*not\s+null")
                and not _find(migration_sql, r"add\s+column[^;]*not\s+null[^;]*default"))):
        add("NOT_NULL_NO_DEFAULT", "blocker",
            "NOT NULL without a default will reject existing rows and in-flight inserts.")
    if _find(migration_sql, r"alter\s+column\s+\S+\s+(set\s+data\s+)?type"):
        add("TABLE_REWRITE_LOCK", "high",
            "A column type change rewrites the table under an exclusive lock.")
    if _find(migration_sql, r"add\s+(constraint|check)") and not _find(migration_sql, r"not\s+valid"):
        add("CONSTRAINT_VALIDATION_LOCK", "high",
            "ADD CONSTRAINT without NOT VALID validates the whole table under a lock.")
    if _find(migration_sql, r"^\s*update\s", ) or _find(migration_sql, r";\s*update\s"):
        if not _find(migration_sql, r"limit|ctid|batch|in\s*\(\s*select"):
            add("UNBATCHED_BACKFILL", "high",
                "The backfill is one unbounded UPDATE; it will hold locks for its whole duration.")
    if not rollback_sql and not _find(migration_sql, r"--\s*rollback|down\s+migration"):
        add("MISSING_ROLLBACK", "medium", "No rollback statements are included in the file.")
    if schema_sql:
        # with the schema in the prompt a text-only reviewer can string-match views
        touched = set(re.findall(r"(?:alter\s+table|drop\s+table)\s+\"?(\w+)", migration_sql, flags=re.I))
        for vm in re.finditer(r"create\s+(?:or\s+replace\s+)?view\s+\"?(\w+)\"?\s+as\s+([^;]+)", schema_sql, flags=re.I):
            if any(re.search(rf"\b{t}\b", vm.group(2), flags=re.I) for t in touched):
                add("VIEW_BREAKAGE", "high",
                    f"View {vm.group(1)} reads a table this migration alters and may stop resolving.")
        if _find(migration_sql, r"drop\s+constraint"):
            add("INTEGRITY_CONSTRAINT_REMOVED", "medium",
                "A constraint is dropped; nothing breaks immediately but invalid rows become possible.")
    return out


class ScriptedLLM(BaseLLM):
    provider = "scripted"
    model = "scripted-v1"

    def complete(self, system: str, user: str, *, tag: str = "",
                 payload: dict[str, Any] | None = None) -> LLMResponse:
        payload = payload or {}
        text, out_payload = self._respond(tag, payload)
        tin, tout = approx_tokens(system + user), approx_tokens(text)
        resp = LLMResponse(text=text, payload=out_payload, tokens_in=tin, tokens_out=tout,
                           cost_usd=price(self.model, tin, tout), provider=self.provider,
                           model=self.model, tag=tag)
        self.calls.append(resp)
        return resp

    # -- response modes ----------------------------------------------------
    def _respond(self, tag: str, p: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if tag == "baseline_review":
            hz = baseline_hazards(p.get("migration_sql", ""), p.get("schema_sql"),
                                  p.get("rollback_sql"))
            blocking = [h for h in hz if h["severity"] in ("blocker", "high")]
            verdict = "REQUEST_CHANGES" if blocking else "APPROVE"
            lines = [f"Verdict: {verdict}", ""]
            for h in hz:
                lines.append(f"- [{h['severity'].upper()}] {h['code']}: {h['note']}")
            if not hz:
                lines.append("- No problems found in the migration as written. Looks safe to ship.")
            return "\n".join(lines), {"verdict": verdict, "hazards": hz}

        if tag == "hazard_narrative":
            h = p["hazard"]
            meta = HAZARDS.get(h["code"], {})
            ev = h.get("evidence", [])
            why = meta.get("why", "")
            body = f"{meta.get('title', h['code'])}. {why}"
            if ev:
                body += f" Evidence: {ev[0]}"
            if h.get("services"):
                body += f" Owning service(s): {', '.join(h['services'])}."
            if h.get("memory_refs"):
                body += f" Previously bit us in {', '.join(h['memory_refs'])}."
            return body, {"narrative": body}

        if tag == "executive_summary":
            v, counts = p["verdict"], p["counts"]
            broken = p.get("broken_queries", 0)
            plan_ok = p.get("plan_verified")
            head = {
                "BLOCK": "Do not ship this as written.",
                "SAFE_WITH_PLAN": "Shippable, but only as the staged plan below.",
                "SAFE": "No blocking hazards found.",
                "NEEDS_COVERAGE_SIGNOFF": "Not cleared: the hazards found are not blocking, but this "
                                          "review has a declared blind spot on an object the "
                                          "migration touches.",
            }[v]
            bits = [head]
            if p.get("coverage_gaps"):
                bits.append(f"{p['coverage_gaps']} coverage gap(s) need a named sign-off before this "
                            f"can be called safe.")
            if broken:
                bits.append(f"{broken} statement(s) the application issues today fail against the "
                            f"post-migration schema in shadow replay.")
            bits.append(f"{counts.get('blocker', 0)} blocker, {counts.get('high', 0)} high, "
                        f"{counts.get('medium', 0)} medium, {counts.get('low', 0)} low.")
            if plan_ok is True:
                bits.append("The rewritten phase-1 plan passes shadow replay with zero broken statements.")
            elif plan_ok is False:
                bits.append("The rewritten plan still breaks at least one statement, so a human has to "
                            "decide the sequencing.")
            return " ".join(bits), {}

        if tag == "reviewer_questions":
            qs = []
            for code in p.get("codes", []):
                qs.append({
                    "BREAKING_QUERY": "Which deploy lands first: the query change or the schema change?",
                    "SELECT_STAR_DRIFT": "Do any consumers read this result set positionally or serialise it whole?",
                    "UNIQUE_VIOLATION_EXISTING_DATA": "Who owns cleaning the duplicate rows, and by when?",
                    "INTEGRITY_CONSTRAINT_REMOVED": "What enforces this invariant once the constraint is gone?",
                    "CROSS_SERVICE_UNCOORDINATED": "Has the owning team agreed to the deploy order?",
                    "TYPE_NARROWING_DATA_LOSS": "Is the truncated value recoverable from anywhere else?",
                    "INDEX_LOCK_NO_CONCURRENT": "What is the acceptable write-stall window for this table?",
                    "UNBATCHED_BACKFILL": "What batch size and pause has this table tolerated before?",
                }.get(code, f"What is the accepted risk for {code}?"))
            seen, uniq = set(), []
            for q in qs:
                if q not in seen:
                    seen.add(q)
                    uniq.append(q)
            return "\n".join(f"- {q}" for q in uniq[:6]), {"questions": uniq[:6]}

        return "", {}
