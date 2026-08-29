"""Long-term memory: the incidents this team already paid for.

Two stores:
  * memory/incidents.jsonl  - curated postmortems (read-only input, human owned)
  * memory/learned.jsonl    - patterns the pipeline recorded from earlier runs

Memory only ever *raises* severity or adds a citation.  It can never clear a
hazard that execution found, because a team having survived something once is
not evidence that it is safe.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any


def load_jsonl(path: str | pathlib.Path) -> list[dict[str, Any]]:
    p = pathlib.Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            out.append(json.loads(line))
    return out


class IncidentMemory:
    def __init__(self, incidents_path: str | pathlib.Path, learned_path: str | pathlib.Path | None = None):
        self.incidents = load_jsonl(incidents_path)
        self.learned_path = pathlib.Path(learned_path) if learned_path else None
        self.learned = load_jsonl(self.learned_path) if self.learned_path else []

    def recall(self, hazard_code: str, table: str | None = None,
               service: str | None = None) -> list[dict[str, Any]]:
        """Exact-key recall.  No embeddings, no similarity threshold to tune."""
        out = []
        for inc in self.incidents + self.learned:
            if inc.get("hazard_code") != hazard_code:
                continue
            same_table = table is not None and table in inc.get("tables", [])
            same_service = service is not None and service in inc.get("services", [])
            out.append({**inc, "match": "table" if same_table else ("service" if same_service else "pattern")})
        order = {"table": 0, "service": 1, "pattern": 2}
        return sorted(out, key=lambda i: (order[i["match"]], -i.get("severity_bump", 0)))

    def escalation(self, hazard_code: str, table: str | None = None) -> tuple[int, list[str]]:
        bump, cites = 0, []
        for inc in self.recall(hazard_code, table):
            if inc["match"] in ("table", "service"):
                bump = max(bump, int(inc.get("severity_bump", 1)))
                cites.append(inc["id"])
            elif not cites:
                cites.append(inc["id"])
        return bump, cites

    def record(self, entry: dict[str, Any]) -> None:
        if not self.learned_path:
            return
        keys = {(e.get("hazard_code"), tuple(sorted(e.get("tables", [])))) for e in self.learned}
        key = (entry.get("hazard_code"), tuple(sorted(entry.get("tables", []))))
        if key in keys:
            return
        self.learned.append(entry)
        self.learned_path.parent.mkdir(parents=True, exist_ok=True)
        with self.learned_path.open("a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
