"""Fail the build if the numbers the README claims are no longer true.

    python3 tools/check_results.py      # after eval/run_eval.py --ablations

Every assertion below is a sentence somewhere in README.md or on the site. If an
edit to the pipeline moves one of them, CI stops instead of quietly publishing a
page that disagrees with its own evidence.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLAIMS: list[tuple[str, bool, str]] = []


def claim(text: str, ok: bool, got: object) -> None:
    CLAIMS.append((text, bool(ok), str(got)))


def main() -> int:
    ev = json.loads((ROOT / "results" / "evaluation.json").read_text())
    ab = json.loads((ROOT / "results" / "ablation.json").read_text())
    arms = ev["arms"]
    S = arms["agent_pipeline"]["aggregate"]
    A = arms["baseline_prompt_only"]["aggregate"]
    B = arms["baseline_prompt_with_schema"]["aggregate"]

    claim("12 evaluation cases in every arm",
          S["cases"] == A["cases"] == B["cases"] == 12, S["cases"])
    claim("pipeline makes no unsafe approval", S["unsafe_approvals"] == 0, S["unsafe_approvals"])
    claim("both baselines make exactly one unsafe approval",
          A["unsafe_approvals"] == 1 and B["unsafe_approvals"] == 1,
          f"{A['unsafe_approvals']}, {B['unsafe_approvals']}")
    claim("pipeline strict F1 at least 0.95", S["strict"]["f1"] >= 0.95, S["strict"]["f1"])
    claim("pipeline names every blind spot it has, with the object",
          S["declared_coverage_gaps"] >= S["cases_with_coverage_gaps"],
          f"{S['declared_coverage_gaps']} gaps across {S['cases_with_coverage_gaps']} cases")
    claim("no coverage-gap case reaches a clean verdict",
          S["gap_cases_cleared_without_signoff"] == 0,
          S["gap_cases_cleared_without_signoff"])
    claim("pipeline beats both baselines on strict recall",
          S["strict"]["recall"] > max(A["strict"]["recall"], B["strict"]["recall"]),
          S["strict"]["recall"])
    claim("every pipeline finding cites machine evidence",
          S["findings_with_evidence"] == S["findings_total"],
          f"{S['findings_with_evidence']}/{S['findings_total']}")
    claim("no baseline finding cites machine evidence",
          A["findings_with_evidence"] == 0 and B["findings_with_evidence"] == 0,
          f"{A['findings_with_evidence']}, {B['findings_with_evidence']}")
    claim("12/12 verified expand/contract plans", S["verified_plans"] == 12, S["verified_plans"])
    claim("no false alarm on the clean case", S["false_alarms_on_clean_cases"] == 0,
          S["false_alarms_on_clean_cases"])
    claim("modelled reviewer minutes cut by at least half",
          S["modelled_reviewer_minutes_per_case"] <= B["modelled_reviewer_minutes_per_case"] / 2,
          S["modelled_reviewer_minutes_per_case"])
    claim("offline run costs nothing", S["cost_usd_total"] == 0, S["cost_usd_total"])

    if ab:
        replay_only = ab["no_static"]["aggregate"]["unsafe_approvals"]
        rules_only = ab["no_replay"]["aggregate"]["unsafe_approvals"]
        claim("replay only is worse than rules only on the primary metric",
              replay_only > rules_only, f"replay-only {replay_only} vs rules-only {rules_only}")
        claim("removing either layer costs at least one unsafe approval",
              min(replay_only, rules_only) > S["unsafe_approvals"],
              f"{replay_only}, {rules_only}")
        nocov = ab["no_coverage"]["aggregate"]
        claim("removing the coverage gate lets a declared blind spot reach a clean verdict",
              nocov["gap_cases_cleared_without_signoff"] > S["gap_cases_cleared_without_signoff"],
              f"no_coverage {nocov['gap_cases_cleared_without_signoff']} vs full "
              f"{S['gap_cases_cleared_without_signoff']}")
        claim("the coverage gate changes no detection metric",
              (nocov["strict"]["f1"] == S["strict"]["f1"]
               and nocov["unsafe_approvals"] == S["unsafe_approvals"]),
              f"f1 {nocov['strict']['f1']} vs {S['strict']['f1']}")
        claim("the coverage gate costs reviewer minutes rather than saving them",
              nocov["modelled_reviewer_minutes_per_case"]
              <= S["modelled_reviewer_minutes_per_case"],
              f"no_coverage {nocov['modelled_reviewer_minutes_per_case']} vs full "
              f"{S['modelled_reviewer_minutes_per_case']}")

    inv_path = ROOT / "results" / "model_invariance.json"
    if inv_path.exists():
        inv = json.loads(inv_path.read_text())
        rows = inv["rows"]
        hostile = [r for r in rows if r["provider"] != "scripted"]
        claim("no model, hostile or not, moves the decision surface",
              all(r["decision_surface_changed"] == 0 for r in rows),
              f"{sum(r['decision_surface_changed'] for r in rows)} changed of "
              f"{sum(r['cases'] for r in rows)} reviews")
        claim("the narrator guard stops every hostile headline it is tested against",
              all(r["summaries_contradicting_verdict"] == 0 for r in rows if r["guard"]),
              sum(r["summaries_contradicting_verdict"] for r in rows if r["guard"]))
        claim("without the guard a hostile narrator does reach the reviewer (so the guard is "
              "load-bearing)",
              max((r["summaries_contradicting_verdict"] for r in hostile if not r["guard"]),
                  default=0) >= 10,
              max((r["summaries_contradicting_verdict"] for r in hostile if not r["guard"]),
                  default=0))
        claim("the guard turns a null model response from an outage into a degraded review",
              all(r["crashed"] == 0 for r in rows if r["guard"])
              and any(r["crashed"] > 0 for r in hostile if not r["guard"]),
              f"guarded crashes {sum(r['crashed'] for r in rows if r['guard'])}, "
              f"unguarded crashes {sum(r['crashed'] for r in hostile if not r['guard'])}")
        claim("every recorded packet in results/ matches a fresh reference run",
              inv["recorded_packets_matching_reference"] == inv["recorded_packets_checked"] == 12,
              f"{inv['recorded_packets_matching_reference']}/{inv['recorded_packets_checked']}")

    width = max(len(c[0]) for c in CLAIMS)
    bad = 0
    for text, ok, got in CLAIMS:
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {text.ljust(width)}  {got}")
    print(f"\n{len(CLAIMS) - bad}/{len(CLAIMS)} claims hold")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
