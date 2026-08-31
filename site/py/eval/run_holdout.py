"""Run the HELD-OUT set and publish the generalization delta, in one command.

    python3 eval/run_holdout.py                  # run both arms + the pipeline, then report
    python3 eval/run_holdout.py --report-only    # rebuild the report from results/ on disk
    python3 eval/run_holdout.py --ablations      # also re-run the 6 component arms out of sample

SUPERVISOR LOG (v9), carried at the top of the file that acts on it
------------------------------------------------------------------
The three hidden assumptions this harness exists to test, and what it found:

  A1  "recall 0.970 means the pipeline finds hazards."  It meant: in twelve cases on
      one billing schema, whose labels were written by the same person who wrote the
      rules.  FOUND: on a second schema, frozen code, 0/9 unsafe approvals and strict
      recall 0.96 - 1.00 if you exclude the one label the shared vocabulary cannot
      name.  The rules transfer.  The claim was true and it was untested.
  A2  "the coverage ledger names what the review could not see."  FOUND: two holes,
      both real, both invisible in sample.  (i) A narrowing type change whose
      offenders happen to be absent from the fixture was reported as a medium note
      under a "shippable" headline: the fixture is a sample of the data exactly as
      the corpus is a sample of the consumers, and only one of those two was in the
      ledger.  (ii) Where the parser modelled nothing at all, the ledger filed the
      gap against the literal string "unknown" while the statement said
      "ON shipment_stops" in plain text.
  A3  "unsafe approvals is the primary metric."  FOUND: it counts APPROVE and SAFE,
      so the failure in A2(i) scored zero on it.  A second primary metric now counts
      blocking cases given ANY verdict that reads as "proceed on what is written
      here".  It is published for every arm and both sets, and its first-contact
      value (1/7) is published beside the fixed one (0/7).

Two designs were weighed for this; see `eval/build_holdout.py` for the second (a
metamorphic fuzzer that needs no labels, kept as a test instead of a harness).

WHAT MAKES THE WORD "HELD-OUT" MEAN ANYTHING HERE
-------------------------------------------------
  * `tools/freeze_attest.py` hashed every file under `sentinel/` before the held-out
    world existed.  This report prints the freeze state at the top, every time.
  * `results/holdout/frozen_run.json` is the first-contact run, made while that state
    still read CLEAN.  The two fixes above landed after it and are labelled as such:
    the current held-out numbers are an AFTER-THE-FIX run, and both are shown.
  * Once a fix is derived from a held-out case, that case stops being held out. Said
    plainly here so nobody has to work it out: `holdout_06` and `holdout_07` are now
    in-sample for the two v6 fixes.  The remaining seven are not.
  * `tools/check_results.py` re-asserts every number below from raw JSON, including
    the three that make the pipeline look worse.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval import run_eval  # noqa: E402
from tools import freeze_attest  # noqa: E402

CLEAN_VERDICTS = {"APPROVE", "SAFE", "SAFE_WITH_PLAN"}
# The one held-out label the shared hazard vocabulary cannot express, by design.
UNNAMEABLE = {"TRIGGER_WRITE_AMPLIFICATION"}
HOLDOUT_CASES = ROOT / "eval" / "holdout"
HOLDOUT_OUT = ROOT / "results" / "holdout"
ARMS = ("baseline_prompt_only", "baseline_prompt_with_schema", "agent_pipeline")
LABELS = {"baseline_prompt_only": "Baseline A", "baseline_prompt_with_schema": "Baseline B",
          "agent_pipeline": "Sentinel"}


def clean_on_blocking(rows: list[dict]) -> tuple[int, int]:
    """Blocking cases that got a verdict a reviewer reads as 'you may proceed'."""
    hit = sum(1 for r in rows if r["gt_blocking"] and r["verdict"] in CLEAN_VERDICTS)
    return hit, sum(1 for r in rows if r["gt_blocking"])


def recall_excluding_unnameable(rows: list[dict]) -> float:
    """Strict recall with the one out-of-vocabulary label removed from the denominator."""
    tp = fn = 0
    for r in rows:
        tp += len([c for c in r["tp"] if c not in UNNAMEABLE])
        fn += len([c for c in r["fn"] if c not in UNNAMEABLE])
    return round(tp / (tp + fn), 3) if tp + fn else 1.0


def invariance_summary(path: pathlib.Path) -> dict:
    """Key figures from the hostile-model harness, run on the held-out world."""
    if not path.exists():
        return {}
    inv = json.loads(path.read_text())
    rows = inv["rows"]
    struct = [r for r in rows if r["mode"] == "structural"]
    fluent = next((r for r in struct if r["provider"] == "hostile-fluent"), {})
    done = sum(r["cases"] - r["crashed"] for r in rows)
    return {
        "inv_reviews": sum(r["cases"] for r in rows),
        "inv_changed": sum(r["decision_surface_changed"] for r in rows),
        "inv_done": done,
        "inv_headlines": sum(r["model_written_headlines"] for r in struct),
        "inv_struct": sum(r["cases"] for r in struct),
        "inv_fluent": fluent.get("misleading_headlines_printed", 0),
        "inv_cases": inv["cases"],
        "inv_crashed": sum(r["crashed"] for r in rows),
        "inv_packets": f"{inv['recorded_packets_matching_reference']}"
                       f"/{inv['recorded_packets_checked']}",
    }


def summarise(ev: dict) -> dict:
    out = {}
    for arm in ARMS:
        if arm not in ev["arms"]:
            continue
        agg = ev["arms"][arm]["aggregate"]
        rows = ev["arms"][arm]["per_case"]
        hit, total = clean_on_blocking(rows)
        out[arm] = {
            "cases": agg["cases"],
            "unsafe_approvals": agg["unsafe_approvals"],
            "clean_on_blocking": hit,
            "blocking_cases": total,
            "recall": agg["strict"]["recall"],
            "recall_excluding_unnameable": recall_excluding_unnameable(rows),
            "precision": agg["strict"]["precision"],
            "f1": agg["strict"]["f1"],
            "severity_agreement": agg["severity_agreement"],
            "false_alarms": agg["false_alarms_on_clean_cases"],
            "evidenced": f"{agg['findings_with_evidence']}/{agg['findings_total']}",
            "verified_plans": f"{agg['verified_plans']}/{agg['cases']}",
            "declared_gaps": agg["declared_coverage_gaps"],
            "gaps_cleared": f"{agg['gap_cases_cleared_without_signoff']}"
                            f"/{agg['cases_with_coverage_gaps']}",
            "minutes": agg["modelled_reviewer_minutes_per_case"],
            "cost_usd": agg["cost_usd_total"],
        }
    return out


def render(insample: dict, holdout: dict, frozen: dict, freeze_state: dict,
           ab_in: dict, ab_out: dict, cases: list[dict],
           unknown: dict[str, int] | None = None) -> str:
    unknown = unknown or {"frozen": 0, "current": 0}
    S_in, S_out = insample["agent_pipeline"], holdout["agent_pipeline"]
    L = ["# Held out: a second schema the rules were never written against", "",
         "```", freeze_attest.render(freeze_state), "```", "",
         f"In sample: {S_in['cases']} cases, one SaaS billing schema, the set every earlier number "
         f"in this repository was measured on.",
         f"Held out: {S_out['cases']} cases, a freight/logistics schema with its own corpus, its own "
         f"row estimates, composite natural keys, JSONB, NUMERIC money and write paths in the "
         f"corpus. No rule, threshold, hazard code or gap class was written or tuned against it "
         f"before the first-contact run.", "",
         "## The generalization table", "",
         "| metric | Sentinel, in sample | Sentinel, held out | Baseline B, held out |",
         "|---|---|---|---|"]

    def row(name: str, key: str, fmt=lambda v: v) -> None:
        L.append(f"| {name} | {fmt(S_in[key])} | {fmt(S_out[key])} | "
                 f"{fmt(holdout['baseline_prompt_with_schema'][key])} |")

    L.append(f"| **Unsafe approvals** (primary) | {S_in['unsafe_approvals']}/{S_in['cases']} | "
             f"{S_out['unsafe_approvals']}/{S_out['cases']} | "
             f"{holdout['baseline_prompt_with_schema']['unsafe_approvals']}/{S_out['cases']} |")
    L.append(f"| **Blocking cases given a clean verdict** (primary, v6) | "
             f"{S_in['clean_on_blocking']}/{S_in['blocking_cases']} | "
             f"{S_out['clean_on_blocking']}/{S_out['blocking_cases']} | "
             f"{holdout['baseline_prompt_with_schema']['clean_on_blocking']}"
             f"/{S_out['blocking_cases']} |")
    row("Hazard recall (strict code)", "recall")
    row("Hazard recall excluding the label no arm can name", "recall_excluding_unnameable")
    row("Hazard precision (strict code)", "precision")
    row("Severity agreement on matched hazards", "severity_agreement")
    row("False alarms on the deliberately clean case", "false_alarms")
    row("Findings backed by machine evidence", "evidenced")
    row("Verified expand/contract plans", "verified_plans")
    row("Blind spots named, with the object", "declared_gaps")
    row("Gap cases cleared without a sign-off", "gaps_cleared")
    row("Modelled reviewer minutes per case", "minutes")

    L += ["", "Read the recall row with its neighbour. `holdout_06` carries "
          "`TRIGGER_WRITE_AMPLIFICATION`, a hazard code deliberately outside the shared "
          "vocabulary, so no arm can name it and every arm loses the same recall point on it. "
          "Excluding it, the pipeline finds every held-out label; including it, the honest figure "
          f"is {S_out['recall']}. A held-out set whose labels all fit the tool's vocabulary would "
          "have tested the rules and quietly exempted the vocabulary.", "",
          "Precision is *higher* out of sample (1.0 vs "
          f"{S_in['precision']}) and severity agreement is slightly lower "
          f"({S_out['severity_agreement']} vs {S_in['severity_agreement']}). Both have the same "
          "cause: this world has no incident log. `memory/incidents.jsonl` belongs to the billing "
          "team, so out of sample nothing escalates a severity and nothing borrows a prior. See the "
          "`no_memory` row below, which is identical to `full` on every metric.", "",
          "## What first contact found, before anything was fixed", "",
          "| metric | frozen run (v5 code) | after the two v6 fixes |", "|---|---|---|",
          f"| Unsafe approvals | {frozen['agent_pipeline']['unsafe_approvals']}"
          f"/{frozen['agent_pipeline']['cases']} | {S_out['unsafe_approvals']}"
          f"/{S_out['cases']} |",
          f"| **Blocking cases given a clean verdict** | "
          f"{frozen['agent_pipeline']['clean_on_blocking']}"
          f"/{frozen['agent_pipeline']['blocking_cases']} | {S_out['clean_on_blocking']}"
          f"/{S_out['blocking_cases']} |",
          f"| Blind spots named, with the object | {frozen['agent_pipeline']['declared_gaps']} | "
          f"{S_out['declared_gaps']} |",
          f"| Gap objects named `unknown` | {unknown['frozen']} | {unknown['current']} |",
          f"| Modelled reviewer minutes per case | {frozen['agent_pipeline']['minutes']} | "
          f"{S_out['minutes']} |",
          "",
          "Two defects, both invisible in sample, both fixed in `sentinel/coverage.py` and "
          "`sentinel/tools/shadow_db.py`:", "",
          "1. **`holdout_07`, the fixture-bounded value scan.** `numeric(12,2) -> numeric(8,2)` on "
          "a 9.4M-row invoice table. The value scan ran over five seeded rows, found nothing that "
          "would be refused, filed a `medium`, and the packet printed *Shippable, but only as the "
          "staged plan below*. The scan was also wrong in kind: precision was treated as string "
          "truncation, so it could not have seen a 1,000,000.00 invoice even if one had been "
          "seeded. Fix: `offending_values` understands `numeric(p,s)`, and a clean scan over a "
          "fixture smaller than the declared row count is now a declared, irreversible coverage "
          "gap. Verdict moves `SAFE_WITH_PLAN` -> `NEEDS_COVERAGE_SIGNOFF`. No hazard invented, no "
          "severity moved.",
          "2. **`holdout_06`, the gap called `unknown`.** `CREATE TRIGGER ... ON shipment_stops` is "
          "outside the parser's model, so the ledger opened a gap - against the literal string "
          "`unknown`, in the one component whose job is naming the affected object. Fix: "
          "`relation_hint` reads the relation out of the statement text and the gap carries "
          "`object_inferred: true`, so the reviewer gets the object *and* the provenance of the "
          "name.", "",
          "Neither fix moves an in-sample number: `tools/check_results.py` still asserts the same "
          "in-sample figures it did before this work, and `case_08` (the in-sample narrowing) has "
          "offenders in its fixture, so it opens no new gap.", "",
          "## Ablation, out of sample", "",
          "| configuration | unsafe approvals | blocking cases given a clean verdict | recall | "
          "verified plans | gaps cleared | minutes/case |", "|---|---|---|---|---|---|---|"]
    for key in ("full", "no_replay", "no_static", "no_memory", "no_verify", "no_coverage"):
        if key not in ab_out:
            continue
        a = ab_out[key]["aggregate"]
        hit, tot = clean_on_blocking(ab_out[key]["per_case"])
        L.append(f"| `{key}` | {a['unsafe_approvals']}/{a['cases']} | {hit}/{tot} | "
                 f"{a['strict']['recall']} | {a['verified_plans']}/{a['cases']} | "
                 f"{a['gap_cases_cleared_without_signoff']}/{a['cases_with_coverage_gaps']} | "
                 f"{a['modelled_reviewer_minutes_per_case']} |")

    cov_in = ab_in.get("no_coverage", {}).get("aggregate", {})
    cov_out = ab_out.get("no_coverage", {}).get("aggregate", {})
    mem_out = ab_out.get("no_memory", {}).get("aggregate", {})
    L += ["", "**The one component that looked like a tax in sample pays for itself out of "
          "sample.** Removing the coverage gate costs "
          f"nothing in sample - {cov_in.get('unsafe_approvals')} unsafe approvals either way - and "
          f"saves 0.7 modelled minutes a case, which is why it is the only component whose removal "
          f"makes a published in-sample number look better. Out of sample, removing it costs "
          f"{cov_out.get('unsafe_approvals')} unsafe approval and lets "
          f"{clean_on_blocking(ab_out['no_coverage']['per_case'])[0]} of "
          f"{clean_on_blocking(ab_out['no_coverage']['per_case'])[1]} blocking migrations reach a "
          "clean verdict: on `holdout_06` the hazard is a statement class the parser cannot model "
          "and the vocabulary cannot name, so refusing to certify it is the *only* correct "
          "behaviour available, and the gate is the only thing that does it.", "",
          "**And the one component that is worth nothing here says so.** `no_memory` is identical "
          f"to `full` on every metric out of sample (recall {mem_out.get('strict', {}).get('recall')}"
          f", unsafe {mem_out.get('unsafe_approvals')}/{mem_out.get('cases')}). The incident log is "
          "the billing team's; a second team's tables have no history, so the memory layer "
          "contributes exactly zero. That is the correct value for a schema-specific component on "
          "a new schema, and no in-sample ablation could ever have told us.", "",
          "## Hostile models, out of sample", "",
          "`python3 eval/model_invariance.py --cases eval/holdout --out results/holdout` reruns the "
          "5 models x 3 narrator modes harness on this world: {inv_reviews} reviews. The numbers it "
          "produced in sample hold here too, on a schema none of it was tuned against.", "",
          "| out-of-sample invariance | value |", "|---|---|",
          "| decision surface changed, any model, any mode | {inv_changed} of {inv_done} completed "
          "reviews |",
          "| headlines written by a model in the shipped `structural` mode | {inv_headlines} of "
          "{inv_struct} |",
          "| the fluent liar reaching the reviewer, shipped mode | {inv_fluent} of {inv_cases} |",
          "| crashes with the narrator unguarded (a null model response) | {inv_crashed} |",
          "| recorded held-out packets matching a fresh reference run | {inv_packets} |", "",
          "## Per-case, held out", "",
          "| case | ground truth | Sentinel verdict | missed | false alarms | coverage gaps |",
          "|---|---|---|---|---|---|"]
    inv = holdout.get("_invariance") or {}
    L = [ln.format(**inv) if "{inv_" in ln else ln for ln in L]
    ev_rows = {r["case_id"]: r for r in holdout["_rows"]}
    notes = holdout["_notes"]
    for case in cases:
        r = ev_rows.get(case["id"])
        if not r:
            continue
        gaps = ", ".join(g["kind"] for g in notes.get(case["id"], {}).get("coverage_ledger", []))
        L.append(f"| `{case['id']}` | {'blocking' if r['gt_blocking'] else 'non-blocking'} | "
                 f"{r['verdict']} | {', '.join(r['fn']) or '-'} | {', '.join(r['fp']) or '-'} | "
                 f"{gaps or '-'} |")
    L += ["", "Commands, from a clean clone, no key and no network:", "",
          "```bash", "python3 eval/build_holdout.py     # regenerate the 9 held-out cases",
          "python3 eval/run_holdout.py --ablations   # 9 cases x 9 arms + the report",
          "python3 tools/freeze_attest.py            # what changed in the decision code, by hash",
          "```", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("run_holdout")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--ablations", action="store_true")
    args = ap.parse_args(argv)

    freeze_state = freeze_attest.verify()
    print(freeze_attest.render(freeze_state) + "\n")

    if not args.report_only:
        argv2 = ["--cases", str(HOLDOUT_CASES), "--out", str(HOLDOUT_OUT),
                 "--trajectories", str(ROOT / "trajectories" / "holdout")]
        if args.ablations:
            argv2.append("--ablations")
        rc = run_eval.main(argv2)
        if rc:
            return rc

    ev_out = json.loads((HOLDOUT_OUT / "evaluation.json").read_text())
    ev_in = json.loads((ROOT / "results" / "evaluation.json").read_text())
    frozen = json.loads((HOLDOUT_OUT / "frozen_run.json").read_text())
    ab_in = json.loads((ROOT / "results" / "ablation.json").read_text())
    ab_out_path = HOLDOUT_OUT / "ablation.json"
    ab_out = json.loads(ab_out_path.read_text()) if ab_out_path.exists() else {}
    cases = run_eval.load_cases(HOLDOUT_CASES)

    insample, holdout = summarise(ev_in), summarise(ev_out)
    holdout["_rows"] = ev_out["arms"]["agent_pipeline"]["per_case"]
    holdout["_notes"] = ev_out.get("agent_notes", {})
    inv_path = HOLDOUT_OUT / "model_invariance.json"
    holdout["_invariance"] = invariance_summary(inv_path)

    generalization = {
        "freeze": freeze_state,
        "in_sample": insample,
        "held_out": holdout | {"_rows": None, "_notes": None},
        "frozen_first_contact": summarise(frozen),
        "unnameable_labels": sorted(UNNAMEABLE),
        "gap_objects_named_unknown": {
            "frozen": sum(1 for c in frozen["agent_notes"].values()
                          for g in c.get("coverage_ledger", []) if g["object"] == "unknown"),
            "current": sum(1 for c in ev_out.get("agent_notes", {}).values()
                           for g in c.get("coverage_ledger", []) if g["object"] == "unknown"),
        },
        "invariance_held_out": invariance_summary(HOLDOUT_OUT / "model_invariance.json"),
        "ablation_held_out": {k: {"unsafe_approvals": v["aggregate"]["unsafe_approvals"],
                                  "recall": v["aggregate"]["strict"]["recall"],
                                  "clean_on_blocking": clean_on_blocking(v["per_case"])[0],
                                  "gap_cases_cleared_without_signoff":
                                      v["aggregate"]["gap_cases_cleared_without_signoff"],
                                  "minutes": v["aggregate"]
                                  ["modelled_reviewer_minutes_per_case"]}
                              for k, v in ab_out.items()},
    }
    (HOLDOUT_OUT / "generalization.json").write_text(json.dumps(generalization, indent=1) + "\n")
    report = render(insample, holdout, summarise(frozen), freeze_state, ab_in, ab_out, cases,
                    generalization["gap_objects_named_unknown"])
    (ROOT / "results" / "holdout.md").write_text(report + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
