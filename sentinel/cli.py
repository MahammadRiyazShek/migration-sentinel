from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys
from typing import Any

from .llm import get_llm
from .orchestrator import record_learning, review
from .report import render
from .tools import shadow_db, sql_parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_INCIDENTS = ROOT / "memory" / "incidents.jsonl"


def load_case(path: str | pathlib.Path) -> dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text())


def cmd_review(args: argparse.Namespace) -> int:
    case = load_case(args.case)
    llm = get_llm(args.provider, args.model, args.cassette, args.cassette_mode)
    out = review(case, llm, incidents_path=args.incidents,
                 learned_path=args.learned if args.learn else None,
                 max_attempts=args.max_attempts, trace=not args.no_trace,
                 run_id=args.run_id)
    report = out["report"]
    if args.learn:
        report["memory_written"] = record_learning(out["memory"], report)
    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{case['id']}.json").write_text(json.dumps(report, indent=1, default=str))
    md = render(report)
    (outdir / f"{case['id']}.md").write_text(md)
    if not args.no_trace:
        tdir = pathlib.Path(args.trace_dir)
        tdir.mkdir(parents=True, exist_ok=True)
        out["tracer"].write_jsonl(tdir / f"{case['id']}.jsonl")
        (tdir / f"{case['id']}.md").write_text(
            out["tracer"].render_markdown(f"Trajectory - {case['id']}"))
    if args.print_report:
        print(md)
    else:
        print(f"{case['id']}: {report['verdict']} "
              f"({report['counts']['blocker']} blocker / {report['counts']['high']} high) "
              f"-> {outdir / (case['id'] + '.md')}")
    return 0


def cmd_execute(args: argparse.Namespace) -> int:
    """Dry-run phase 1 against a throwaway sandbox copy. Never touches a real database."""
    report = json.loads(pathlib.Path(args.report).read_text())
    if not args.i_approve or not args.reviewer:
        print("REFUSED: phase 1 execution requires --i-approve and --reviewer \"name\".\n"
              "This is the human approval gate; the agent will not run DDL on its own authority.")
        return 2
    if report["verdict"] == "BLOCK" and not args.override_block:
        print("REFUSED: the review verdict is BLOCK. Re-run with --override-block if a qualified "
              "reviewer has accepted the hazards, and say so in the deploy record.")
        return 3
    case = load_case(args.case)
    schema = sql_parse.parse_schema(case["schema_sql"], case.get("row_estimates", {}))
    script = "\n".join(s for s in report["plan"]["phase1_sql"] if not s.strip().startswith("--"))
    ops = sql_parse.parse_migration(script)
    post, _ = sql_parse.apply_ops(schema, ops)
    rep = shadow_db.replay(schema, post, ops, case.get("seed", {}), case["queries"])
    print(f"sandbox: SQLite in-memory copy (never a live database)")
    print(f"approved by: {args.reviewer}")
    print(f"phase-1 statements executed: {len(ops)}")
    print(f"corpus after phase 1: {sum(1 for o in rep.post.values() if o.ok)}/{len(rep.post)} passing")
    for b in rep.broken:
        print(f"  BROKEN {b['query_id']}: {b['error']}")
    return 0 if not rep.broken else 1


def cmd_cases(args: argparse.Namespace) -> int:
    for path in sorted(pathlib.Path(args.dir).glob("*.json")):
        case = load_case(path)
        gt = case["ground_truth"]
        print(f"{case['id']:<34} {'BLOCKING' if gt['blocking'] else 'non-blocking':<13} "
              f"{len(gt['hazards'])} hazards  {case['title']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("sentinel", description="Review a database migration before it ships.")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("review", help="run the full agent pipeline on one case")
    r.add_argument("--case", required=True)
    r.add_argument("--out", default="results")
    r.add_argument("--trace-dir", default="trajectories")
    r.add_argument("--provider", default="scripted", choices=["scripted", "openai", "anthropic"])
    r.add_argument("--model", default=None)
    r.add_argument("--cassette", default=None, help="path to a prompt cassette for offline replay")
    r.add_argument("--cassette-mode", default="replay", choices=["replay", "record"])
    r.add_argument("--incidents", default=str(DEFAULT_INCIDENTS))
    r.add_argument("--learned", default=str(ROOT / "memory" / "learned.jsonl"))
    r.add_argument("--learn", action="store_true", help="write blocking hazards back to memory")
    r.add_argument("--max-attempts", type=int, default=3)
    r.add_argument("--no-trace", action="store_true")
    r.add_argument("--run-id", default=None)
    r.add_argument("--print-report", action="store_true")
    r.set_defaults(func=cmd_review)

    e = sub.add_parser("execute", help="dry-run phase 1 in a sandbox after human approval")
    e.add_argument("--report", required=True)
    e.add_argument("--case", required=True)
    e.add_argument("--i-approve", action="store_true")
    e.add_argument("--reviewer", default=None)
    e.add_argument("--override-block", action="store_true")
    e.set_defaults(func=cmd_execute)

    c = sub.add_parser("cases", help="list evaluation cases")
    c.add_argument("--dir", default=str(ROOT / "eval" / "cases"))
    c.set_defaults(func=cmd_cases)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
