"""Fail the build if the numbers the README claims are no longer true.

    python3 tools/check_results.py      # after eval/run_eval.py --ablations
                                       # and eval/run_holdout.py --ablations

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
        claim("no model, hostile or not, moves the decision surface",
              all(r["decision_surface_changed"] == 0 for r in rows),
              f"{sum(r['decision_surface_changed'] for r in rows)} changed of "
              f"{sum(r['cases'] for r in rows)} reviews")
        pat = [r for r in rows if r["mode"] == "pattern"]
        struct = [r for r in rows if r["mode"] == "structural"]
        off = [r for r in rows if r["mode"] == "off"]
        fluent_pat = next(r for r in rows
                          if r["provider"] == "hostile-fluent" and r["mode"] == "pattern")
        fluent_str = next(r for r in rows
                          if r["provider"] == "hostile-fluent" and r["mode"] == "structural")
        claim("the v3 pattern guard stops every hostile headline whose wording it knows",
              all(r["summaries_contradicting_verdict"] == 0 for r in pat),
              sum(r["summaries_contradicting_verdict"] for r in pat))
        claim("with no guard at all a hostile narrator owns the headline (so a guard is "
              "load-bearing)",
              max((r["summaries_contradicting_verdict"] for r in off
                   if r["provider"] != "scripted"), default=0) >= 10,
              max((r["summaries_contradicting_verdict"] for r in off
                   if r["provider"] != "scripted"), default=0))
        claim("a lie in words the v3 blocklist never learned walks through it onto the headline",
              fluent_pat["misleading_headlines_printed"] == 12
              and fluent_pat["summaries_contradicting_verdict"] == 0,
              f"printed {fluent_pat['misleading_headlines_printed']}/12, v3 audit flagged "
              f"{fluent_pat['summaries_contradicting_verdict']}/12")
        claim("the shipped structural narrator lets no model write the headline, hostile or not",
              sum(r["model_written_headlines"] for r in struct) == 0,
              f"{sum(r['model_written_headlines'] for r in struct)} of "
              f"{sum(r['cases'] for r in struct)} headlines model-written")
        claim("and so the fluent liar reaches the reviewer on no case at all",
              fluent_str["misleading_headlines_printed"] == 0,
              fluent_str["misleading_headlines_printed"])
        claim("provenance costs no detection metric: the narrator never touched one",
              S["strict"]["f1"] >= 0.95 and S["unsafe_approvals"] == 0,
              f"f1 {S['strict']['f1']}, unsafe {S['unsafe_approvals']}")
        claim("either guarded mode turns a null model response from an outage into a degraded "
              "review",
              all(r["crashed"] == 0 for r in rows if r["guard"])
              and any(r["crashed"] > 0 for r in off if r["provider"] != "scripted"),
              f"guarded crashes {sum(r['crashed'] for r in rows if r['guard'])}, "
              f"unguarded crashes {sum(r['crashed'] for r in off)}")
        claim("every recorded packet in results/ matches a fresh reference run",
              inv["recorded_packets_matching_reference"] == inv["recorded_packets_checked"] == 12,
              f"{inv['recorded_packets_matching_reference']}/{inv['recorded_packets_checked']}")

    # ------------------------------------------------------------------ held out
    # v6. Everything above is measured on the 12 cases whose labels were written by the
    # same hand as the rules. These are measured on a second schema, hashed-code-frozen
    # before the labels existed. Three of them make the pipeline look worse.
    gen_path = ROOT / "results" / "holdout" / "generalization.json"
    if gen_path.exists():
        gen = json.loads(gen_path.read_text())
        H = gen["held_out"]["agent_pipeline"]
        HB = gen["held_out"]["baseline_prompt_with_schema"]
        HA = gen["held_out"]["baseline_prompt_only"]
        F = gen["frozen_first_contact"]["agent_pipeline"]
        hab = gen["ablation_held_out"]
        man = json.loads((ROOT / "results" / "holdout"
                          / "decision_code_manifest.json").read_text())

        claim("9 held-out cases on a second schema, same three arms",
              H["cases"] == HB["cases"] == HA["cases"] == 9, H["cases"])
        claim("the decision code was hashed before the held-out labels existed, and every "
              "file changed since is named",
              man["files"] == 34 and sorted(gen["freeze"]["changed"]) == [
                  "sentinel/agents/risk_officer.py", "sentinel/coverage.py",
                  "sentinel/tools/shadow_db.py"],
              f"{man['files']} hashed, changed since: {gen['freeze']['changed']}")
        claim("no unsafe approval out of sample either", H["unsafe_approvals"] == 0,
              H["unsafe_approvals"])
        claim("out-of-sample recall at least 0.90, and 1.0 once the label no arm can name is "
              "excluded",
              H["recall"] >= 0.90 and H["recall_excluding_unnameable"] == 1.0,
              f"{H['recall']} strict, {H['recall_excluding_unnameable']} excluding "
              f"{gen['unnameable_labels']}")
        claim("the one out-of-vocabulary hazard is still missed, out of sample, on purpose",
              H["recall_excluding_unnameable"] > H["recall"],
              f"{H['recall']} vs {H['recall_excluding_unnameable']}")
        claim("both baselines miss more than a third of the held-out hazards",
              HA["recall"] < 0.65 and HB["recall"] < 0.65,
              f"A {HA['recall']}, B {HB['recall']}")
        claim("out-of-sample precision is no worse than in sample",
              H["precision"] >= S["strict"]["precision"],
              f"{H['precision']} vs {S['strict']['precision']}")
        claim("still no false alarm on the deliberately clean held-out case, where baseline B "
              "raises one", H["false_alarms"] == 0 and HB["false_alarms"] == 1,
              f"{H['false_alarms']} vs {HB['false_alarms']}")
        claim("every out-of-sample finding cites machine evidence, and 9/9 plans are verified",
              H["evidenced"].split("/")[0] == H["evidenced"].split("/")[1]
              and H["verified_plans"] == "9/9",
              f"{H['evidenced']} evidenced, {H['verified_plans']} plans")
        claim("first contact gave one blocking migration a clean verdict; the fix took it to zero",
              F["clean_on_blocking"] == 1 and H["clean_on_blocking"] == 0,
              f"frozen {F['clean_on_blocking']}/{F['blocking_cases']} -> "
              f"now {H['clean_on_blocking']}/{H['blocking_cases']}")
        claim("no gap is filed against `unknown` any more, and one was on first contact",
              gen["gap_objects_named_unknown"]["frozen"] == 1
              and gen["gap_objects_named_unknown"]["current"] == 0,
              f"frozen {gen['gap_objects_named_unknown']['frozen']}, "
              f"now {gen['gap_objects_named_unknown']['current']}")
        claim("the v6 gap class opens no new in-sample gap: same 3 blind spots on the same 2 cases",
              S["declared_coverage_gaps"] == 3 and S["cases_with_coverage_gaps"] == 2,
              f"{S['declared_coverage_gaps']} gaps across {S['cases_with_coverage_gaps']} cases")
        if hab:
            claim("the coverage gate costs no unsafe approval in sample and prevents one out of "
                  "sample",
                  ab["no_coverage"]["aggregate"]["unsafe_approvals"] == 0
                  and hab["no_coverage"]["unsafe_approvals"] == 1,
                  f"in-sample {ab['no_coverage']['aggregate']['unsafe_approvals']}, held-out "
                  f"{hab['no_coverage']['unsafe_approvals']}")
            claim("the memory layer is worth exactly nothing on a schema with no incident log",
                  (hab["no_memory"]["recall"] == hab["full"]["recall"]
                   and hab["no_memory"]["unsafe_approvals"] == hab["full"]["unsafe_approvals"]
                   and hab["no_memory"]["minutes"] == hab["full"]["minutes"]),
                  f"no_memory {hab['no_memory']['recall']}/{hab['no_memory']['minutes']}min vs "
                  f"full {hab['full']['recall']}/{hab['full']['minutes']}min")
        hinv = gen.get("invariance_held_out") or {}
        if hinv:
            claim("no model, hostile or not, moves the decision surface out of sample either",
                  hinv["inv_changed"] == 0 and hinv["inv_done"] >= 120,
                  f"{hinv['inv_changed']} changed of {hinv['inv_done']} completed held-out "
                  f"reviews")
            claim("no model writes a held-out headline in the shipped narrator mode",
                  hinv["inv_headlines"] == 0 and hinv["inv_fluent"] == 0,
                  f"{hinv['inv_headlines']} of {hinv['inv_struct']} headlines model-written, "
                  f"fluent liar printed {hinv['inv_fluent']}/{hinv['inv_cases']}")
        claim("out-of-sample reviewer minutes still under half of baseline B",
              H["minutes"] <= HB["minutes"] / 2, f"{H['minutes']} vs {HB['minutes']}")

    width = max(len(c[0]) for c in CLAIMS)
    bad = 0
    for text, ok, got in CLAIMS:
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {text.ljust(width)}  {got}")
    print(f"\n{len(CLAIMS) - bad}/{len(CLAIMS)} claims hold")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
