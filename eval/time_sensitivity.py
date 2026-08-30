"""Sensitivity band on the modelled reviewer-minute claim.

Why this exists
---------------
`eval/scoring.py:TIME_MODEL` holds four constants I chose, and `tools/check_results.py`
re-asserts the reviewer-minute claim from those same constants. That is circular: the audit
cannot fail, because the number and its check share an assumption. "Cut reviewer time by two
thirds" is the most quotable figure in the submission and the only headline figure that is
modelled rather than measured, so it is the one that needs a band rather than a point estimate.

What it does
------------
Recomputes the per-case reviewer-minute model for every arm from the already-committed
`results/evaluation.json` and `results/ablation.json`, under alternate constant sets: the
published midpoint, a global 0.5x and 2x scaling, and three adversarial sets chosen specifically
to shrink the pipeline's advantage as far as the model structurally allows.

The point is not to find a set where the pipeline wins by more. The point is to find a set where
it stops winning. If one exists, that belongs in the README; if none does, the direction of the
claim is a property of the arms rather than of my constants.

Provenance
----------
Reads committed results only. Runs no reviews, calls no model, mutates nothing. The midpoint row
is recomputed from the raw per-case fields and asserted equal to the stored
`modelled_reviewer_minutes`, so drift between this script and `eval/scoring.py` fails loudly
instead of quietly reporting a comfortable number.

Usage
-----
    python eval/time_sensitivity.py            # print the band
    python eval/time_sensitivity.py --write    # also write results/time_sensitivity.md
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# Published constants, mirrored from eval/scoring.py:TIME_MODEL.
PUBLISHED = {"read": 5, "verify": 4, "plan": 20, "gate": 3}

# Below this reduction the advantage is reported as collapsed rather than as a win.
COLLAPSE_PCT = 10

ARM_LABELS = {
    "ablation_no_replay": "minus shadow replay (rules only)",
    "ablation_no_static": "minus static rules (replay only)",
    "ablation_no_memory": "minus incident memory",
    "ablation_no_verify": "minus verifier + retry loop",
}

# (label, constants, rationale)
SCENARIOS: list[tuple[str, dict[str, float], str]] = [
    ("published midpoint", dict(PUBLISHED),
     "the constants in `eval/scoring.py`"),
    ("all constants 0.5x", {k: v * 0.5 for k, v in PUBLISHED.items()},
     "a fast reviewer on a schema they know well"),
    ("all constants 2x", {k: v * 2 for k, v in PUBLISHED.items()},
     "a careful reviewer on an unfamiliar service"),
    ("adversarial: cheap verification", {"read": 5, "verify": 1, "plan": 20, "gate": 3},
     "an unevidenced claim costs only 1 minute to check, which removes most of the penalty the "
     "baselines pay"),
    ("adversarial: cheap plan, dear gate", {"read": 5, "verify": 1, "plan": 6, "gate": 6},
     "writing an expand/contract plan by hand takes 6 minutes and approving a generated one also "
     "takes 6, so both of the pipeline's structural advantages are priced away"),
    ("adversarial: reading dominates", {"read": 20, "verify": 1, "plan": 6, "gate": 6},
     "the previous set plus a long read, so fixed cost swamps every variable term"),
]


def case_minutes(row: dict, c: dict[str, float]) -> float:
    """eval/scoring.py's minute model, parameterised on the constants.

    Kept deliberately literal so it can be diffed against score_case() by eye.
    """
    unevidenced = row["findings"] - row["evidenced_findings"]
    minutes = c["read"]
    minutes += unevidenced * c["verify"]
    if row["plan_verified"]:
        minutes += row["human_gates"] * c["gate"]
    elif row["gt_blocking"] or row["pred_codes"]:
        minutes += c["plan"]
    return minutes


def arm_mean(rows: list[dict], c: dict[str, float]) -> float:
    return round(sum(case_minutes(r, c) for r in rows) / len(rows), 1)


def load_arms() -> dict[str, list[dict]]:
    evaluation = json.loads((RESULTS / "evaluation.json").read_text())
    arms = {name: arm["per_case"] for name, arm in evaluation["arms"].items()}

    ablation_path = RESULTS / "ablation.json"
    if ablation_path.exists():
        ablation = json.loads(ablation_path.read_text())
        for name, arm in ablation.items():
            if name == "full":
                continue
            rows = arm.get("per_case") if isinstance(arm, dict) else None
            if rows:
                arms[f"ablation_{name}"] = rows
    return arms


def selfcheck(arms: dict[str, list[dict]]) -> None:
    """The midpoint recomputation must equal the stored value, case by case."""
    bad = []
    for name, rows in arms.items():
        for row in rows:
            recomputed = case_minutes(row, PUBLISHED)
            stored = row["modelled_reviewer_minutes"]
            if abs(recomputed - stored) > 1e-9:
                bad.append((name, row["case_id"], stored, recomputed))
    if bad:
        print("SELF-CHECK FAILED: this script has drifted from eval/scoring.py", file=sys.stderr)
        for name, case_id, stored, recomputed in bad[:10]:
            print(f"  {name} {case_id}: stored {stored} != recomputed {recomputed}", file=sys.stderr)
        raise SystemExit(1)
    total = sum(len(r) for r in arms.values())
    print(f"self-check: {total} per-case minute figures recomputed from raw fields, all identical "
          f"to eval/scoring.py at the published constants\n")


def render(arms: dict[str, list[dict]]) -> str:
    lines: list[str] = []
    lines.append("# Reviewer-minute sensitivity band\n")
    lines.append(
        "Generated by `eval/time_sensitivity.py` from the committed `results/`. Reviewer minutes are\n"
        "the one headline number that is **modelled rather than measured**, and `tools/check_results.py`\n"
        "re-asserts the claim from the same four constants that produce it, so that audit cannot fail.\n"
        "This table exists so the claim is reported as a range, and so a reader can see exactly what it\n"
        "would take to overturn it.\n"
    )
    lines.append("Minutes per case, mean over the same 12 cases in every row.\n")

    lines.append("| constant set | A (prompt only) | B (prompt + schema) | Migration Sentinel "
                 "| best baseline - Sentinel | reduction |")
    lines.append("|---|---|---|---|---|---|")

    rows_out = []
    for label, constants, _rationale in SCENARIOS:
        a = arm_mean(arms["baseline_prompt_only"], constants)
        b = arm_mean(arms["baseline_prompt_with_schema"], constants)
        s = arm_mean(arms["agent_pipeline"], constants)
        best_baseline = min(a, b)
        delta = round(best_baseline - s, 1)
        pct = round(100.0 * delta / best_baseline) if best_baseline else 0
        rows_out.append((label, a, b, s, delta, pct))
        if delta <= 0:
            flag = " **(claim reverses)**"
        elif pct < COLLAPSE_PCT:
            flag = " **(advantage collapses)**"
        else:
            flag = ""
        lines.append(f"| {label} | {a} | {b} | **{s}** | {delta:+} | {pct}%{flag} |")

    lines.append("")
    lines.append("Constant sets, in the order above:\n")
    for label, constants, rationale in SCENARIOS:
        pretty = ", ".join(f"`{k}={v:g}`" for k, v in constants.items())
        lines.append(f"- **{label}** - {pretty}. {rationale}")

    robust = [r for r in rows_out if r[5] >= COLLAPSE_PCT]
    collapsed = [r for r in rows_out if r[5] < COLLAPSE_PCT]
    reversed_rows = [r for r in rows_out if r[4] <= 0]
    lo = min(r[5] for r in rows_out)
    hi = max(r[5] for r in rows_out)

    lines.append("")
    lines.append("## What the band says\n")
    lines.append(
        f"The reduction against the *better* baseline ranges from **{lo}%** to **{hi}%** across "
        f"{len(rows_out)} constant sets. The sign never reverses"
        + (" and no set makes a baseline faster than the pipeline"
           if not reversed_rows else ", except in the flagged row") + ", "
        f"but that is the weaker claim: **{len(collapsed)} of {len(rows_out)} sets shrink the "
        f"advantage to under {COLLAPSE_PCT}%**, which for practical purposes is no advantage at all.\n"
    )
    lines.append(
        "Reported honestly, that splits into two findings.\n\n"
        "**The claim is robust to how expensive you think a reviewer's time is.** Scaling all four\n"
        "constants together leaves the reduction at "
        + "/".join(f"{r[5]}%" for r in rows_out[:3])
        + " for 1x, 0.5x and 2x, because a uniform scale cancels. Halving the cost of checking an\n"
        "unevidenced claim still leaves "
        f"{rows_out[3][5]}%. None of the plausible ways of being wrong about the *magnitude* of the\n"
        "constants touch the result.\n\n"
        "**The claim is not robust to their ratio, and one specific ratio carries all of it:**\n"
        "`write_expand_contract_plan` against `human_gate`. The last two sets price a hand-written\n"
        "expand/contract plan at 6 minutes and approving a generated one at 6 minutes, and the\n"
        "advantage goes to "
        + " and ".join(f"{r[5]}%" for r in rows_out[-2:])
        + ". So the load-bearing assumption is not that reviewers are slow, it is that **writing a\n"
        "staged migration plan from scratch costs several times more than approving one that has\n"
        "already been replayed.** I believe that (the plans in `results/*.md` are 20 to 40 lines of\n"
        "phased DDL with backfill batching and a rollback for each phase, and `case_01` needed a retry\n"
        "a human would have had to catch), but it is a belief about reviewers, not a measurement, and\n"
        "the whole time claim rests on it rather than on the four numbers in `TIME_MODEL`.\n"
    )
    lines.append(
        "Two terms cannot be flipped by any choice of constants, only zeroed, and both are properties\n"
        "of the arms rather than of the model:\n\n"
        "1. Pipeline findings are 34/34 evidenced against 0/19 and 0/29 for the baselines, so the\n"
        "   `verify` term only ever charges the baselines. Driving `verify` to 0 deletes the term.\n"
        "2. The pipeline produces 12/12 verified plans, so it pays `gate` where a baseline pays `plan`.\n"
        "   Reversing that needs `gate * human_gates > plan`.\n"
    )
    lines.append(
        "What the band does *not* do: it does not test the model's shape. Four linear terms with no\n"
        "interaction is an assumption no choice of constants can falsify. Measuring this properly means\n"
        "timing real reviewers on the twelve cases against the packet and against the raw diff. That is\n"
        "the next experiment and it is not in this submission.\n"
    )

    ablation_arms = [k for k in arms if k.startswith("ablation_")]
    if ablation_arms:
        lines.append("## Ablation arms at the published constants\n")
        lines.append("| arm | modelled min/case |")
        lines.append("|---|---|")
        for name in ablation_arms:
            label = ARM_LABELS.get(name, name.replace("ablation_", "minus "))
            lines.append(f"| {label} | {arm_mean(arms[name], PUBLISHED)} |")
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sensitivity band on the reviewer-minute claim.")
    parser.add_argument("--write", action="store_true",
                        help="write results/time_sensitivity.md as well as printing it")
    args = parser.parse_args(argv)

    arms = load_arms()
    selfcheck(arms)
    text = render(arms)
    print(text)
    if args.write:
        out = RESULTS / "time_sensitivity.md"
        out.write_text(text)
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
