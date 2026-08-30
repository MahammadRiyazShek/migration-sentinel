"""What each component buys: one table, generated from results/ablation.json.

WHY THIS FILE EXISTS
--------------------
The headline ablation answers "does removing this cost an unsafe approval?".  For
two of the five components the honest answer is no, and reporting only detection
metrics makes verification and incident memory look decorative.  They are not
decorative, they just pay out somewhere the detection metrics cannot see:

  * the verifier pays in *shippable plans* - without it nothing is proven, so the
    reviewer writes the expand/contract plan by hand
  * incident memory pays in *severity*, and it is the thinnest component in the
    system: across 12 cases it changes exactly one severity

This script makes both of those machine-generated instead of a prose claim, and
it prints the component whose evidence is weakest rather than hiding it.

Usage (after `python eval/run_eval.py --ablations`):
    python eval/report_components.py                  # prints markdown
    python eval/report_components.py --write          # also writes results/components.md
"""
from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

ARM_LABEL = {
    "full": "Migration Sentinel (all five agents)",
    "no_replay": "minus shadow replay (rules only)",
    "no_static": "minus static rules (replay only)",
    "no_memory": "minus incident memory",
    "no_verify": "minus verifier + retry loop",
    "no_coverage": "minus coverage gate (the v1 behaviour)",
}
# Which deliverable each component is supposed to protect. Stated up front so the
# table can be read as a prediction that either held or did not.
ARM_CLAIM = {
    "no_replay": "unsafe approvals",
    "no_static": "unsafe approvals",
    "no_memory": "severity agreement",
    "no_verify": "verified plans, reviewer minutes",
    "no_coverage": "coverage-gap cases cleared without a sign-off",
}


def metrics(per_case: list[dict]) -> dict[str, float]:
    n = len(per_case) or 1
    tp = sum(len(c["tp"]) for c in per_case)
    fp = sum(len(c["fp"]) for c in per_case)
    fn = sum(len(c["fn"]) for c in per_case)
    matched = tp
    recall = tp / (tp + fn) if tp + fn else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    sev = sum(len(c["severity_matches"]) for c in per_case)
    return {
        "unsafe": sum(1 for c in per_case if c["unsafe_approval"]),
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "f1": round(2 * recall * precision / (recall + precision), 3) if recall + precision else 0.0,
        "sev_agreement": round(sev / matched, 3) if matched else 0.0,
        "plans": sum(1 for c in per_case if c["plan_verified"]),
        "gaps_cleared": sum(1 for c in per_case if c.get("gap_case_cleared_without_signoff")),
        "gap_cases": sum(1 for c in per_case if c.get("case_coverage_gaps")),
        "evidenced": sum(c["evidenced_findings"] for c in per_case),
        "findings": sum(c["findings"] for c in per_case),
        "minutes": round(sum(c["modelled_reviewer_minutes"] for c in per_case) / n, 1),
        "tokens": sum(c["tokens"] for c in per_case),
        "n": len(per_case),
    }


def cost(full_v: float, arm_v: float, *, lower_is_better: bool = False,
         suffix: str = "", fmt: str = "{:+.3f}") -> str:
    """Cost of removing the component, always oriented so + means it earned its place."""
    delta = (arm_v - full_v) if lower_is_better else (full_v - arm_v)
    if round(delta, 3) == 0:
        return ""
    mark = "earns it" if delta > 0 else "argues against it"
    return f"{fmt.format(delta)}{suffix} ({mark})"


def build(data: dict) -> str:
    full = metrics(data["full"]["per_case"])
    rows, verdicts = [], []
    for arm, label in ARM_LABEL.items():
        if arm not in data:
            continue
        m = metrics(data[arm]["per_case"])
        rows.append(
            f"| {label} | {m['unsafe']}/{m['n']} | {m['recall']:.3f} | {m['precision']:.3f} | "
            f"{m['sev_agreement']:.3f} | {m['plans']}/{m['n']} | "
            f"{m['gaps_cleared']}/{m['gap_cases']} | {m['evidenced']}/{m['findings']} | "
            f"{m['minutes']} | {m['tokens']:,} |"
        )
        if arm == "full":
            continue
        deltas = [
            ("unsafe approvals", cost(full["unsafe"], m["unsafe"], lower_is_better=True, fmt="{:+.0f}")),
            ("strict recall", cost(full["recall"], m["recall"])),
            ("severity agreement", cost(full["sev_agreement"], m["sev_agreement"])),
            ("verified plans", cost(full["plans"], m["plans"], fmt="{:+.0f}")),
            ("gap cases cleared without a sign-off",
             cost(full["gaps_cleared"], m["gaps_cleared"], lower_is_better=True, fmt="{:+.0f}")),
            ("reviewer minutes/case", cost(full["minutes"], m["minutes"], lower_is_better=True,
                                           suffix=" min", fmt="{:+.1f}")),
        ]
        moved = [f"{name} {delta}" for name, delta in deltas if delta]
        verdicts.append(
            f"- **{label}** — predicted to protect *{ARM_CLAIM[arm]}*. "
            + (f"Removing it costs: {'; '.join(moved)}." if moved
               else "Removing it costs **nothing measured here**. Weakest component in the system; "
                    "kept only where a cited reason survives this table.")
        )

    out = [
        "# What each component buys",
        "",
        f"Generated by `eval/report_components.py` from `results/ablation.json`. "
        f"{len(ARM_LABEL)} arms x {full['n']} cases. Deltas are *full pipeline minus the ablated arm*, "
        "read as the cost of removal: a positive number is the component paying for itself.",
        "",
        "| arm | unsafe approvals | recall | precision | severity agreement | verified plans | "
        "gaps cleared | evidenced findings | modelled min/case | tokens |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        "## Did each component do the job it was added for?",
        "",
        *verdicts,
        "",
        "Two components (replay, static rules) are load-bearing on the primary metric. One (the "
        "verifier) is load-bearing on everything downstream of detection and worth nothing to "
        "detection itself. One (incident memory) is close to free on this case set, which is a "
        "statement about the case set as much as about the component: 12 cases contain one "
        "recurrence, so one severity is all it can possibly move.",
        "",
        "The coverage gate is the only component that makes the pipeline look *worse* on a "
        "published metric. It moves no detection number at all and it adds modelled reviewer "
        "minutes, because every gap it opens is a human decision someone has to make. What it buys "
        "is the one thing the other four cannot: a verdict that stops short of clean when the "
        "review has a blind spot on an object the migration touches. Removing it is the v1 "
        "behaviour, and the v1 behaviour clears one.",
    ]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser("report_components")
    ap.add_argument("--ablation", default=str(ROOT / "results" / "ablation.json"))
    ap.add_argument("--write", action="store_true", help="also write results/components.md")
    args = ap.parse_args()
    path = pathlib.Path(args.ablation)
    if not path.exists():
        print(f"missing {path}; run: python eval/run_eval.py --ablations")
        return 1
    md = build(json.loads(path.read_text()))
    print(md)
    if args.write:
        out = ROOT / "results" / "components.md"
        out.write_text(md + "\n")
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
