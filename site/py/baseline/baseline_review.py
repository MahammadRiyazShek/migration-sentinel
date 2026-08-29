"""The baseline: one model call, one prompt, no tools.

This is what "use AI to review migrations" means in practice for most teams, and
it is what the agent pipeline has to beat.  Two variants:

  prompt_only        the migration file and its rollback, nothing else
  prompt_with_schema the same, plus the full current DDL and the row estimates

Both are given the same hazard vocabulary as the agent pipeline and the same
instruction to be exhaustive, so the comparison is about capability, not about
one side being told less.  The only thing the baseline cannot do is look
anything up: no query corpus, no data, no execution, no incident history.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sentinel.hazards import HAZARDS  # noqa: E402
from sentinel.llm import get_llm  # noqa: E402

SYSTEM = """You are a staff database engineer reviewing a PostgreSQL migration before it ships to
production. Be exhaustive and specific. For every risk you find, output a line:

- [SEVERITY] HAZARD_CODE: one sentence explaining the risk

Use only these hazard codes:
{codes}

Severity is one of low, medium, high, blocker. Use blocker when a statement the application issues
today would fail, when data would be lost, or when the migration itself could not complete.
Finish with a line "Verdict: APPROVE" or "Verdict: REQUEST_CHANGES".
""".format(codes="\n".join(f"  {code} - {meta['title']}" for code, meta in HAZARDS.items()))


def build_user_prompt(case: dict, variant: str) -> str:
    parts = [f"Migration to review (service: {case['owner_service']}):", "", "```sql",
             case["migration_sql"].strip(), "```"]
    if case.get("rollback_sql"):
        parts += ["", "Rollback script shipped with it:", "", "```sql",
                  case["rollback_sql"].strip(), "```"]
    else:
        parts += ["", "No rollback script was supplied."]
    if variant == "prompt_with_schema":
        parts += ["", "Current schema:", "", "```sql", case["schema_sql"].strip(), "```",
                  "", "Approximate row counts:",
                  *[f"- {t}: {n:,}" for t, n in case["row_estimates"].items()]]
    parts += ["", "Review it now."]
    return "\n".join(parts)


def run_case(case: dict, llm, variant: str) -> dict:
    started = time.perf_counter()
    user = build_user_prompt(case, variant)
    resp = llm.complete(SYSTEM, user, tag="baseline_review",
                        payload={"migration_sql": case["migration_sql"],
                                 "schema_sql": case["schema_sql"] if variant == "prompt_with_schema" else None,
                                 "rollback_sql": case.get("rollback_sql", "")})
    parsed = resp.payload or {"verdict": "APPROVE", "hazards": []}
    return {
        "case_id": case["id"], "variant": variant, "verdict": parsed["verdict"],
        "hazards": [{**h, "evidence": [], "source": "model"} for h in parsed["hazards"]],
        "review_text": resp.text,
        "model_usage": {"provider": llm.provider, "model": llm.model, "calls": 1,
                        "tokens_in": resp.tokens_in, "tokens_out": resp.tokens_out,
                        "cost_usd": round(resp.cost_usd, 6)},
        "wall_ms": round((time.perf_counter() - started) * 1000, 1),
        "plan": None, "plan_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("baseline_review")
    ap.add_argument("--case", required=True)
    ap.add_argument("--variant", default="prompt_with_schema",
                    choices=["prompt_only", "prompt_with_schema"])
    ap.add_argument("--provider", default="scripted", choices=["scripted", "openai", "anthropic"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default="results/baseline")
    ap.add_argument("--print-review", action="store_true")
    args = ap.parse_args(argv)

    case = json.loads(pathlib.Path(args.case).read_text())
    llm = get_llm(args.provider, args.model)
    result = run_case(case, llm, args.variant)
    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{case['id']}.{args.variant}.json").write_text(json.dumps(result, indent=1))
    (outdir / f"{case['id']}.{args.variant}.md").write_text(
        f"# Baseline review ({args.variant}): {case['title']}\n\n```\n{result['review_text']}\n```\n")
    print(f"{case['id']}: {result['verdict']} ({len(result['hazards'])} findings, no evidence, no plan)")
    if args.print_review:
        print(result["review_text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
