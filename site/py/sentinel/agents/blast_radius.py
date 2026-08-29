"""Agent 2 - Blast Radius: find who depends on the touched objects, then prove it.

Static dependency lookup answers "who might care".  Shadow replay answers "who
actually breaks".  Only the second one is allowed to create a blocker.
"""
from __future__ import annotations

import re
from typing import Any

from ..hazards import Hazard
from ..tools.shadow_db import ReplayReport
from .base import Agent

UNIQUE_RE = re.compile(r"UNIQUE constraint failed: ([\w.]+)", re.I)
NOTNULL_RE = re.compile(r"NOT NULL constraint failed: ([\w.]+)", re.I)
CHECK_RE = re.compile(r"CHECK constraint failed: ([\w.]+)", re.I)


class BlastRadius(Agent):
    NAME = "blast_radius"
    GOAL = ("Enumerate every application statement that depends on the touched objects and "
            "reproduce the failures in a shadow database before anyone deploys anything.")

    def run(self, case: dict[str, Any], parsed: dict[str, Any],
            use_replay: bool = True) -> dict[str, Any]:
        queries = case["queries"]
        self.start({"case": case["id"], "corpus_size": len(queries),
                    "services": sorted({q.get("service", "unknown") for q in queries})})
        hits = self.tool("corpus.dependents", queries=queries, ops=parsed["ops"],
                         schema=parsed["schema"])
        score = self.tool("corpus.blast_score", hits=hits)
        if use_replay:
            replay = self.tool("shadow.replay", pre_schema=parsed["schema"],
                               post_schema=parsed["post_schema"], ops=parsed["ops"],
                               seed=case.get("seed", {}), queries=queries)
        else:
            # ablation arm: static dependency lookup only, nothing is executed
            replay = ReplayReport(materialised=True)
            self.tracer and self.tracer.note(self.NAME, "shadow replay disabled for this run")
        hazards: list[Hazard] = []
        corpus_names = " ".join(q["sql"] for q in queries).lower()
        for b in replay.broken:
            code = "VIEW_BREAKAGE" if b["query_id"].startswith("__view__") else "BREAKING_QUERY"
            label = b["query_id"][8:] if b["query_id"].startswith("__view__") else b["query_id"]
            if code == "VIEW_BREAKAGE" and label.lower() in corpus_names:
                # a corpus statement reads this view, so the same failure is already reported
                # against a real owner - reporting it twice is noise, not thoroughness
                self.tracer and self.tracer.note(
                    self.NAME, f"view {label} breakage folded into the corpus statement that reads it")
                continue
            hazards.append(Hazard(
                code=code, severity="blocker", source="replay",
                summary=f"{label} fails after the migration: {b['error']}",
                evidence=[f"shadow replay: `{b['sql'][:120]}` -> {b['error']}"],
                objects=[label], services=[b["service"]]))
        for d in replay.column_drift:
            if d["query_id"].startswith("__view__"):
                # the view probe is a self-check; the corpus statements that read the view
                # already carry the hazard with a real owner attached
                continue
            if not d["removed"]:
                # a purely additive column set is a note, not a hazard: flagging every
                # ADD COLUMN as a breakage is how a reviewer learns to ignore the tool
                self.tracer and self.tracer.note(
                    self.NAME, f"{d['query_id']} gains column(s) {d['added']}; recorded as a note, "
                               f"not a hazard, because nothing is removed from the result set")
                continue
            hazards.append(Hazard(
                code="SELECT_STAR_DRIFT", severity="high", source="replay",
                summary=(f"{d['query_id']} still runs but its column set changes "
                         f"(removed {d['removed'] or 'none'}, added {d['added'] or 'none'})"),
                evidence=[f"shadow replay columns before={d['before']} after={d['after']}"],
                objects=[d["query_id"]], services=[d["service"]]))
        for err in replay.data_errors:
            if UNIQUE_RE.search(err):
                target = UNIQUE_RE.search(err).group(1)
                hazards.append(Hazard(
                    code="UNIQUE_VIOLATION_EXISTING_DATA", severity="blocker", source="replay",
                    summary=f"Uniqueness on {target} is violated by rows already in the table",
                    evidence=[f"shadow backfill: {err[:200]}"], objects=[target]))
            elif NOTNULL_RE.search(err):
                target = NOTNULL_RE.search(err).group(1)
                hazards.append(Hazard(
                    code="NOT_NULL_NO_DEFAULT", severity="blocker", source="replay",
                    summary=f"Existing rows cannot satisfy NOT NULL on {target}",
                    evidence=[f"shadow backfill: {err[:200]}"], objects=[target]))
            elif CHECK_RE.search(err):
                target = CHECK_RE.search(err).group(1)
                hazards.append(Hazard(
                    code="BREAKING_QUERY", severity="blocker", source="replay",
                    summary=f"Migration data step violates a CHECK constraint on {target}",
                    evidence=[f"shadow backfill: {err[:200]}"], objects=[target]))
            else:
                hazards.append(Hazard(
                    code="BREAKING_QUERY", severity="blocker", source="replay",
                    summary=f"Migration step failed in shadow replay: {err[:160]}",
                    evidence=[err[:240]]))
        for loss in replay.data_loss:
            sev = "blocker" if loss["offending_rows"] else "medium"
            hazards.append(Hazard(
                code="TYPE_NARROWING_DATA_LOSS", severity=sev, source="replay",
                summary=(f"{loss['table']}.{loss['column']} {loss['from']} -> {loss['to']} would not "
                         f"survive {loss['offending_rows']}/{loss['rows_checked']} fixture rows"),
                evidence=[f"value scan offenders={loss['offending_samples']}"],
                objects=[f"{loss['table']}.{loss['column']}"]))
        out = {"dependents": hits, "blast_score": score, "replay": replay, "hazards": hazards}
        self.end({"dependent_queries": len(hits), "blast_score": score,
                  "replay": replay.to_json(), "hazards_found": [h.code for h in hazards]})
        return out
