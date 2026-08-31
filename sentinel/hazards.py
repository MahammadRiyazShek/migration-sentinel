"""The shared hazard vocabulary.

Baseline, agent pipeline and ground truth all speak these codes, which is what
makes the comparison in eval/ apples-to-apples.  Severity ladder:
blocker > high > medium > low.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SEVERITY_ORDER = ["low", "medium", "high", "blocker"]

HAZARDS: dict[str, dict[str, str]] = {
    "BREAKING_QUERY": {
        "title": "Live query breaks after migration",
        "default_severity": "blocker",
        "detect": "shadow replay",
        "why": "A statement the application issues today fails against the post-migration schema.",
    },
    "SELECT_STAR_DRIFT": {
        "title": "SELECT * consumer receives a different column set",
        "default_severity": "high",
        "detect": "shadow replay (column diff)",
        "why": "The query still runs, so tests pass, but downstream code indexing by position or key breaks.",
    },
    "VIEW_BREAKAGE": {
        "title": "Dependent view no longer resolves",
        "default_severity": "blocker",
        "detect": "shadow replay (view probe)",
        "why": "Views bind lazily; the failure only appears the next time something reads the view.",
    },
    "DESTRUCTIVE_NO_EXPAND_CONTRACT": {
        "title": "Destructive change shipped in a single step",
        "default_severity": "high",
        "detect": "static rule",
        "why": "Dropping or renaming in one deploy means old and new application code cannot both work.",
    },
    "NOT_NULL_NO_DEFAULT": {
        "title": "NOT NULL added without a usable default",
        "default_severity": "blocker",
        "detect": "static rule + backfill replay",
        "why": "Existing rows or in-flight inserts violate the constraint immediately.",
    },
    "UNIQUE_VIOLATION_EXISTING_DATA": {
        "title": "Uniqueness conflicts with data already in the table",
        "default_severity": "blocker",
        "detect": "shadow replay (backfill)",
        "why": "The index build fails partway through, leaving the deploy half-applied.",
    },
    "INDEX_LOCK_NO_CONCURRENT": {
        "title": "Index built without CONCURRENTLY on a large table",
        "default_severity": "high",
        "detect": "static rule + row estimate",
        "why": "Writes queue behind the build; at this row count that is a user-visible stall.",
    },
    "CONSTRAINT_VALIDATION_LOCK": {
        "title": "Constraint added without NOT VALID / VALIDATE split",
        "default_severity": "high",
        "detect": "static rule + row estimate",
        "why": "Validation scans the whole table under a lock that blocks writes.",
    },
    "UNBATCHED_BACKFILL": {
        "title": "Backfill runs as one unbounded statement",
        "default_severity": "high",
        "detect": "static rule",
        "why": "One long transaction holds locks and bloats WAL; it cannot be paused or resumed.",
    },
    "TABLE_REWRITE_LOCK": {
        "title": "Type change forces a full table rewrite",
        "default_severity": "high",
        "detect": "static rule + row estimate",
        "why": "An ACCESS EXCLUSIVE lock for the length of the rewrite is downtime by another name.",
    },
    "TYPE_NARROWING_DATA_LOSS": {
        "title": "Narrowing type change can silently lose data",
        "default_severity": "blocker",
        "detect": "shadow replay (value scan)",
        "why": "Values that do not fit are truncated or rejected, and the old values are gone.",
    },
    "INTEGRITY_CONSTRAINT_REMOVED": {
        "title": "Data-integrity constraint removed",
        "default_severity": "high",
        "detect": "static rule (semantic)",
        "why": "Nothing breaks today; invalid rows start accumulating and are expensive to clean up later.",
    },
    "CROSS_SERVICE_UNCOORDINATED": {
        "title": "Impact lands on a service owned by another team",
        "default_severity": "high",
        "detect": "corpus ownership lookup",
        "why": "The fix needs a deploy the migration author does not control, so ordering must be agreed first.",
    },
    "ACCESS_PATH_REMOVED": {
        "title": "Index dropped while live statements still filter on it",
        "default_severity": "high",
        "detect": "static rule + corpus access-path lookup",
        "why": "Every statement still succeeds, so replay and tests are silent; the plan flips to a "
               "sequential scan and the table's size decides whether that is a slow page or an outage.",
    },
    "CONCURRENT_DDL_IN_TRANSACTION": {
        "title": "CONCURRENTLY used inside a transaction block",
        "default_severity": "blocker",
        "detect": "static rule (statement correlation)",
        "why": "Postgres refuses CREATE/DROP INDEX CONCURRENTLY inside a transaction block, and most "
               "migration frameworks open one by default, so the deploy fails on the statement itself.",
    },
    "MISSING_ROLLBACK": {
        "title": "No rollback path supplied",
        "default_severity": "medium",
        "detect": "static rule",
        "why": "Recovery at 3am should not require improvising DDL.",
    },
}


def severity_at_least(a: str, b: str) -> bool:
    return SEVERITY_ORDER.index(a) >= SEVERITY_ORDER.index(b)


def bump(severity: str, steps: int) -> str:
    idx = min(len(SEVERITY_ORDER) - 1, SEVERITY_ORDER.index(severity) + max(0, steps))
    return SEVERITY_ORDER[idx]


@dataclass
class Hazard:
    code: str
    severity: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    objects: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    source: str = "static"          # static | replay | memory | model
    memory_refs: list[str] = field(default_factory=list)
    remediation: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code, "severity": self.severity, "summary": self.summary,
            "evidence": self.evidence, "objects": self.objects, "services": self.services,
            "source": self.source, "memory_refs": self.memory_refs,
            "remediation": self.remediation,
            "title": HAZARDS.get(self.code, {}).get("title", self.code),
        }
