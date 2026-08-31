"""Run every case through both reviewers and write the comparison.

    python eval/run_eval.py                    # baseline (both variants) + agent pipeline
    python eval/run_eval.py --only agent
    python eval/run_eval.py --provider openai  # same code path against a hosted model

Outputs
    results/evaluation.json   every per-case score and the aggregates
    results/comparison.md     the table that goes in the README
    results/<case>.md         one review packet per case (agent pipeline)
    trajectories/<case>.md    one trajectory per case
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baseline.baseline_review import run_case as run_baseline  # noqa: E402
from eval.scoring import TIME_MODEL, aggregate, score_case  # noqa: E402
from sentinel.coverage import ledger as coverage_ledger  # noqa: E402
from sentinel.llm import HOSTILE, get_llm  # noqa: E402
from sentinel.tools import sql_parse  # noqa: E402
from sentinel.orchestrator import FEATURE_SETS, review  # noqa: E402
from sentinel.report import render  # noqa: E402

ARMS = ["baseline_prompt_only", "baseline_prompt_with_schema", "agent_pipeline"]


def load_cases(directory: pathlib.Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(directory.glob("*.json"))]


def case_gap_count(case: dict) -> int:
    """Blind spots that exist as a fact about the case, computed once and applied to every arm."""
    schema = sql_parse.parse_schema(case["schema_sql"], case.get("row_estimates", {}))
    ops = sql_parse.parse_migration(case["migration_sql"])
    return len(coverage_ledger(ops, schema, case.get("queries", []),
                              seed=case.get("seed", {}))["gaps"])


def agent_result(case: dict, args, features: str = "full", trace: bool = True) -> tuple[dict, dict]:
    llm = get_llm(args.provider, args.model)
    out = review(case, llm, incidents_path=str(ROOT / "memory" / "incidents.jsonl"),
                 learned_path=None, max_attempts=args.max_attempts, trace=trace,
                 run_id=f"eval-{case['id']}" + ("" if features == "full" else f"-{features}"),
                 features=features)
    report = out["report"]
    result = {
        "case_id": case["id"], "variant": "agent_pipeline", "verdict": report["verdict"],
        "hazards": report["hazards"], "model_usage": report["model_usage"],
        "wall_ms": report["wall_ms"], "plan": report["plan"],
        "plan_verified": report["plan_verification"]["verified"],
        "escalated": report["escalated_to_human"], "attempts": report["attempts"],
        "coverage_gaps": report["coverage_gaps"],
        "coverage_ledger": report["coverage_ledger"],
        "verdict_capped_by_coverage": report["verdict_capped_by_coverage"],
    }
    return result, out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("run_eval")
    ap.add_argument("--cases", default=str(ROOT / "eval" / "cases"))
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--trajectories", default=str(ROOT / "trajectories"),
                    help="where per-case runtime trajectories are written; the held-out run keeps "
                         "its own directory so the in-sample trajectories stay a clean set")
    ap.add_argument("--provider", default="scripted",
                    choices=["scripted", "openai", "anthropic"] + sorted(HOSTILE))
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--only", default="all", choices=["all", "agent", "baseline"])
    ap.add_argument("--ablations", action="store_true",
                    help="also run the pipeline with individual components disabled")
    args = ap.parse_args(argv)

    cases = load_cases(pathlib.Path(args.cases))
    outdir = pathlib.Path(args.out)
    (outdir / "baseline").mkdir(parents=True, exist_ok=True)
    scores: dict[str, list[dict]] = {arm: [] for arm in ARMS}
    per_case_notes: dict[str, dict] = {}

    gap_counts = {case["id"]: case_gap_count(case) for case in cases}

    for case in cases:
        gaps = gap_counts[case["id"]]
        if args.only in ("all", "baseline"):
            for variant in ("prompt_only", "prompt_with_schema"):
                llm = get_llm(args.provider, args.model)
                res = run_baseline(case, llm, variant)
                (outdir / "baseline" / f"{case['id']}.{variant}.json").write_text(
                    json.dumps(res, indent=1))
                (outdir / "baseline" / f"{case['id']}.{variant}.md").write_text(
                    f"# Baseline review ({variant}): {case['title']}\n\n```\n{res['review_text']}\n```\n")
                scores[f"baseline_{variant}"].append(score_case(case, res, gaps))
        if args.only in ("all", "agent"):
            res, out = agent_result(case, args)
            (outdir / f"{case['id']}.json").write_text(json.dumps(out["report"], indent=1, default=str))
            (outdir / f"{case['id']}.md").write_text(render(out["report"]))
            tdir = pathlib.Path(args.trajectories)
            tdir.mkdir(parents=True, exist_ok=True)
            out["tracer"].write_jsonl(tdir / f"{case['id']}.jsonl")
            (tdir / f"{case['id']}.md").write_text(
                out["tracer"].render_markdown(f"Trajectory - {case['id']}"))
            scores["agent_pipeline"].append(score_case(case, res, gaps))
            per_case_notes[case["id"]] = {
                "attempts": res["attempts"], "escalated": res["escalated"],
                "coverage_gaps": res["coverage_gaps"],
                "coverage_ledger": res["coverage_ledger"]["gaps"],
                "verdict_capped_by_coverage": res["verdict_capped_by_coverage"],
            }
        print(f"  scored {case['id']}")

    ablation = {}
    if args.ablations:
        for feature_set in FEATURE_SETS:
            rows = []
            for case in cases:
                res, _ = agent_result(case, args, features=feature_set, trace=False)
                rows.append(score_case(case, res, gap_counts[case["id"]]))
            ablation[feature_set] = {"per_case": rows, "aggregate": aggregate(rows)}
            print(f"  ablation {feature_set}: "
                  f"unsafe={ablation[feature_set]['aggregate']['unsafe_approvals']} "
                  f"f1={ablation[feature_set]['aggregate']['strict']['f1']}")
        (outdir / "ablation.json").write_text(json.dumps(ablation, indent=1))
        (outdir / "ablation.md").write_text(render_ablation(ablation))

    report = {
        "time_model_assumptions": TIME_MODEL,
        "arms": {arm: {"per_case": scores[arm], "aggregate": aggregate(scores[arm])}
                 for arm in ARMS if scores[arm]},
        "agent_notes": per_case_notes,
    }
    (outdir / "evaluation.json").write_text(json.dumps(report, indent=1))
    (outdir / "comparison.md").write_text(render_comparison(report, cases))
    print("\n" + render_comparison(report, cases))
    return 0


def render_ablation(ablation: dict) -> str:
    cases = ablation.get("full", {}).get("aggregate", {}).get("cases", 12)
    L = ["# Ablation: which component actually does the work", "",
         f"Same {cases} cases, same scripted model, one component removed at a time.", "",
         "| configuration | unsafe approvals | recall (strict) | precision (strict) | "
         "severity agreement | verified plans | gaps cleared without sign-off |",
         "|---|---|---|---|---|---|---|"]
    order = ["full", "no_replay", "no_static", "no_memory", "no_verify", "no_coverage",
             "no_rule_coverage"]
    for key in order:
        if key not in ablation:
            continue
        a = ablation[key]["aggregate"]
        L.append(f"| `{key}` | {a['unsafe_approvals']}/{a['cases']} | {a['strict']['recall']} | "
                 f"{a['strict']['precision']} | {a['severity_agreement']} | "
                 f"{a['verified_plans']}/{a['cases']} | "
                 f"{a['gap_cases_cleared_without_signoff']}/{a['cases_with_coverage_gaps']} |")
    L += ["", "Note: `no_replay` also disables plan verification, because the Verifier is the same "
          "replay tool pointed at the generated plan.", ""]
    return "\n".join(L)


def render_comparison(report: dict, cases: list[dict]) -> str:
    arms = report["arms"]
    L = ["# Baseline vs agent pipeline", "",
         f"{len(cases)} cases, identical inputs, identical hazard vocabulary. "
         "Primary metric first.", ""]
    labels = {"baseline_prompt_only": "Baseline A (prompt only)",
              "baseline_prompt_with_schema": "Baseline B (prompt + schema)",
              "agent_pipeline": "Agent pipeline"}
    keys = [k for k in ["baseline_prompt_only", "baseline_prompt_with_schema", "agent_pipeline"]
            if k in arms]
    header = "| metric | " + " | ".join(labels[k] for k in keys) + " |"
    L += [header, "|" + "---|" * (len(keys) + 1)]

    def row(name: str, fn) -> None:
        L.append(f"| {name} | " + " | ".join(str(fn(arms[k]["aggregate"])) for k in keys) + " |")

    row("**Unsafe approvals** (primary, lower is better)",
        lambda a: f"{a['unsafe_approvals']}/{a['cases']}")
    row("**Blocking cases given a clean verdict** (primary, lower is better)",
        lambda a: f"{a['clean_verdicts_on_blocking_cases']}/{a['blocking_cases']}")
    row("Hazard recall (strict code)", lambda a: a["strict"]["recall"])
    row("Hazard precision (strict code)", lambda a: a["strict"]["precision"])
    row("Hazard F1 (strict code)", lambda a: a["strict"]["f1"])
    row("Hazard recall (hazard family)", lambda a: a["lenient_family"]["recall"])
    row("Hazard precision (hazard family)", lambda a: a["lenient_family"]["precision"])
    row("Severity agreement on matched hazards", lambda a: a["severity_agreement"])
    row("False alarms on the clean case", lambda a: a["false_alarms_on_clean_cases"])
    row("Findings backed by machine evidence",
        lambda a: f"{a['findings_with_evidence']}/{a['findings_total']}")
    row("Verified expand/contract plans produced", lambda a: f"{a['verified_plans']}/{a['cases']}")
    row("**Coverage-gap cases cleared without a sign-off** (lower is better)",
        lambda a: f"{a['gap_cases_cleared_without_signoff']}/{a['cases_with_coverage_gaps']}")
    row("Blind spots named in the packet, with the object",
        lambda a: a["declared_coverage_gaps"])
    row("Modelled reviewer minutes per case", lambda a: a["modelled_reviewer_minutes_per_case"])
    row("Wall clock per case (ms, measured)", lambda a: a["wall_ms_per_case"])
    row("Model tokens for all cases (measured)", lambda a: a["tokens_total"])
    L += ["", "Reviewer minutes are **modelled**, not measured, from these assumptions: "
          + ", ".join(f"{k}={v}" for k, v in report["time_model_assumptions"].items())
          + ". Wall clock and tokens are measured.", "",
          "## Per-case detail (agent pipeline)", "",
          "| case | ground truth | verdict | missed | false alarms | attempts | plan verified | "
          "coverage gaps |", "|---|---|---|---|---|---|---|---|"]
    notes = report.get("agent_notes", {})
    for r in arms.get("agent_pipeline", {}).get("per_case", []):
        L.append(f"| `{r['case_id']}` | {'blocking' if r['gt_blocking'] else 'non-blocking'} | "
                 f"{r['verdict']} | {', '.join(r['fn']) or '-'} | {', '.join(r['fp']) or '-'} | "
                 f"{notes.get(r['case_id'], {}).get('attempts', '-')} | "
                 f"{'yes' if r['plan_verified'] else 'NO - escalated'} | "
                 f"{', '.join(g['kind'] for g in notes.get(r['case_id'], {}).get('coverage_ledger', [])) or '-'} |")
    L += ["", "## Per-case detail (baseline B, prompt + schema)", "",
          "| case | verdict | missed | false alarms |", "|---|---|---|---|"]
    for r in arms.get("baseline_prompt_with_schema", {}).get("per_case", []):
        L.append(f"| `{r['case_id']}` | {r['verdict']}"
                 f"{' **(unsafe approval)**' if r['unsafe_approval'] else ''} | "
                 f"{', '.join(r['fn']) or '-'} | {', '.join(r['fp']) or '-'} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
