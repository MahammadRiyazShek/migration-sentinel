"""Pack the repository into the static site under site/.

    python3 tools/build_site.py

Two outputs, both generated (never hand-edited):

  site/data/bundle.json   every case, every recorded review packet, trimmed
                          trajectories, the evaluation and ablation numbers, the
                          hazard catalogue and the changelog parsed out of README.md.
                          This is what the page renders before you boot the engine.

  site/py/                the Python the browser actually runs. Pyodide fetches every
                          path in site/py/manifest.json, writes it into its virtual
                          filesystem and imports `sentinel` from there, so a live run
                          in the browser executes the same code as the CLI.

Run it after any change to sentinel/, eval/, baseline/ or results/, otherwise the page
shows stale recorded runs. `make site` does this for you.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = SITE / "data"
PY = SITE / "py"

sys.path.insert(0, str(ROOT))
from sentinel.hazards import HAZARDS  # noqa: E402
from eval.scoring import FAMILIES, TIME_MODEL  # noqa: E402

RUNTIME_DIRS = ["sentinel", "baseline", "eval"]
RUNTIME_SKIP = re.compile(r"(__pycache__|\.pyc$|eval/cases/)")
RUNTIME_EXTRA = ["memory/incidents.jsonl"]

TRUNC_ARGS = 700
TRUNC_RESULT = 1100


def trim_event(ev: dict) -> dict:
    """Keep a trajectory event readable in a browser without shipping the payloads."""
    kind = ev.get("kind")
    out = {"kind": kind, "seq": ev.get("seq"), "t_ms": ev.get("t_ms"), "agent": ev.get("agent")}
    if kind == "agent_start":
        out["goal"] = ev.get("goal")
        out["inputs"] = json.dumps(ev.get("inputs"), indent=1, sort_keys=True)[:TRUNC_ARGS]
    elif kind == "tool_call":
        out["tool"] = ev.get("tool")
        out["ms"] = ev.get("ms")
        out["args"] = json.dumps(ev.get("args"), indent=1, sort_keys=True)[:TRUNC_ARGS]
        out["result"] = json.dumps(ev.get("result"), indent=1, sort_keys=True)[:TRUNC_RESULT]
    elif kind == "model_call":
        out.update({"tag": ev.get("tag"), "model": ev.get("model"), "text": ev.get("text"),
                    "tokens_in": ev.get("tokens_in"), "tokens_out": ev.get("tokens_out")})
    elif kind == "agent_end":
        out["output"] = json.dumps(ev.get("output"), indent=1, sort_keys=True)[:TRUNC_RESULT]
    elif kind in ("note", "feedback"):
        out["text"] = ev.get("text")
        out["attempt"] = ev.get("attempt")
    elif kind == "retry":
        out.update({"attempt": ev.get("attempt"), "reason": ev.get("reason")})
    elif kind == "human_checkpoint":
        out.update({"name": ev.get("name"), "state": ev.get("state"), "detail": ev.get("detail")})
    return {k: v for k, v in out.items() if v is not None}


def read_trajectory(case_id: str) -> list[dict]:
    path = ROOT / "trajectories" / f"{case_id}.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("kind") == "run_start":
            continue
        events.append(trim_event(ev))
    return events


def parse_changelog(readme: str) -> list[dict]:
    """Lift the Improvement Changelog table out of README.md so it cannot drift."""
    block = readme.split("## Improvement Changelog", 1)
    if len(block) < 2:
        return []
    rows = []
    for line in block[1].splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if rows and stripped.startswith("##"):
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split(" | ")]
        if len(cells) != 4 or set("".join(cells)) <= set("-: "):
            continue
        if cells[0].lower().strip("* ") == "stage":
            continue
        rows.append({"stage": cells[0], "what": cells[1], "evidence": cells[2],
                     "decision": cells[3]})
    return rows


def build_bundle() -> dict:
    cases_dir = ROOT / "eval" / "cases"
    evaluation = json.loads((ROOT / "results" / "evaluation.json").read_text())
    ablation = json.loads((ROOT / "results" / "ablation.json").read_text())
    readme = (ROOT / "README.md").read_text()

    cases = []
    for path in sorted(cases_dir.glob("*.json")):
        case = json.loads(path.read_text())
        report_path = ROOT / "results" / f"{case['id']}.json"
        report = json.loads(report_path.read_text()) if report_path.exists() else None
        if report:
            report = {k: v for k, v in report.items() if k != "tool_calls"}
        baselines = {}
        for variant in ("prompt_only", "prompt_with_schema"):
            bp = ROOT / "results" / "baseline" / f"{case['id']}.{variant}.json"
            if bp.exists():
                baselines[variant] = json.loads(bp.read_text())
        md_path = ROOT / "results" / f"{case['id']}.md"
        cases.append({
            "id": case["id"],
            "title": case["title"],
            "owner_service": case["owner_service"],
            "scenario": case["scenario"],
            "schema_sql": case["schema_sql"],
            "migration_sql": case["migration_sql"],
            "rollback_sql": case.get("rollback_sql", ""),
            "row_estimates": case["row_estimates"],
            "queries": case["queries"],
            "seed": case["seed"],
            "ground_truth": case["ground_truth"],
            "report": report,
            "markdown": md_path.read_text() if md_path.exists() else "",
            "baselines": baselines,
            "trajectory": read_trajectory(case["id"]),
        })

    prompts = {}
    for p in sorted((ROOT / "sentinel" / "agents" / "prompts").glob("*.md")):
        prompts[p.stem] = p.read_text()

    return {
        "generated_from": "results/evaluation.json + results/ablation.json + eval/cases/",
        "cases": cases,
        "evaluation": evaluation,
        "ablation": {k: v["aggregate"] for k, v in ablation.items()},
        "hazards": HAZARDS,
        "families": FAMILIES,
        "time_model": TIME_MODEL,
        "changelog": parse_changelog(readme),
        "prompts": prompts,
        "incidents": [json.loads(l) for l in
                      (ROOT / "memory" / "incidents.jsonl").read_text().splitlines() if l.strip()],
    }


def copy_runtime() -> list[str]:
    if PY.exists():
        shutil.rmtree(PY)
    PY.mkdir(parents=True)
    manifest: list[str] = []
    for d in RUNTIME_DIRS:
        for src in sorted((ROOT / d).rglob("*")):
            rel = src.relative_to(ROOT).as_posix()
            if src.is_dir() or RUNTIME_SKIP.search(rel) or src.suffix not in (".py", ".md"):
                continue
            dst = PY / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            manifest.append(rel)
    for rel in RUNTIME_EXTRA:
        dst = PY / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
        manifest.append(rel)
    for pkg in ("eval", "baseline"):
        init = PY / pkg / "__init__.py"
        if not init.exists():
            init.write_text("")
            manifest.append(f"{pkg}/__init__.py")
    (PY / "manifest.json").write_text(json.dumps(sorted(manifest), indent=1))
    return sorted(manifest)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle()
    out = DATA / "bundle.json"
    out.write_text(json.dumps(bundle, separators=(",", ":"), default=str))
    manifest = copy_runtime()
    kb = out.stat().st_size / 1024
    py_kb = sum(p.stat().st_size for p in PY.rglob("*") if p.is_file()) / 1024
    print(f"site/data/bundle.json   {kb:,.0f} KB  ({len(bundle['cases'])} cases, "
          f"{sum(len(c['trajectory']) for c in bundle['cases'])} trajectory events, "
          f"{len(bundle['changelog'])} changelog rows)")
    print(f"site/py/                {py_kb:,.0f} KB  ({len(manifest)} files for the browser runtime)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
