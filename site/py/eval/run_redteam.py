"""Run the RED-TEAM set: the two arms, the v12 pipeline and the v13 pipeline, side by side.

    python3 eval/run_redteam.py                 # 7 cases x 9 arms + the report
    python3 eval/run_redteam.py --report-only   # rebuild the report from results/ on disk

SUPERVISOR LOG (v13), carried at the top of the file that acts on it
-------------------------------------------------------------------
The three hidden assumptions this harness exists to test, and what it found:

  A1  "the coverage ledger names what this review could not see."  It named what the
      review could not see about objects a rule had already looked at.  Every gap class
      in `sentinel/coverage.py` before v13 was keyed to a statement kind something
      already handled.  A kind no rule inspects produced no hazard, no gap, and a clean
      verdict.  FOUND by probing statement kinds rather than hazards: 5 of the 26 kinds
      the parser can emit were in that condition.  An allow-list of known unknowns is
      still an allow-list, and the v2 fix - a declared gap constrains the verdict - was
      only ever half the property it claimed.

  A2  "twelve cases plus nine held-out cases is coverage."  Both sets were labelled from
      the shared hazard vocabulary, so both can only test hazards someone had already
      named.  FOUND: two hazard classes that are not in either set at all, one of which
      (`DROP INDEX` on a hot table) is among the most common migrations written
      anywhere, and one of which (`CONCURRENTLY` inside a transaction) the *text-only
      baseline* catches while the v12 pipeline did not.  On that class the advanced
      solution scored below the thing it exists to beat.  That is published here rather
      than left out.

  A3  "adding rules makes a reviewer safer."  Not on its own.  The first version of the
      residual-gap class opened a gap on `case_06`, the case that exists to catch
      reviewers who cry wolf, because it could not distinguish *a rule looked and
      cleared this* from *no rule exists for this*.  And the first version of the index
      rule raised a blocker on `rt_06`/`rt_07`, the commonest correct index migration
      there is, because it did not know that a B-tree on (a, b) serves a lookup on (a).
      Both are in the set as cases now: a safety tool that blocks correct changes gets
      switched off, and a switched-off tool has recall zero.

READ THE GENERALISATION NUMBER FIRST
------------------------------------
These 7 cases are IN SAMPLE: the v13 rules were written from these probes.  They prove
two holes are closed, not that the pipeline generalises.  The evidence that this layer
was *missing* rather than *tuned* runs the other way and is printed in this report:
`no_rule_coverage` reproduces v12 exactly and is identical to `full` on all 21 labelled
cases in `eval/cases` and `eval/holdout` - same verdicts, same hazards, same severities,
same gaps.  A layer that moves no existing number is a layer that was absent.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval import run_eval  # noqa: E402
from eval.run_holdout import clean_on_blocking  # noqa: E402

RT_CASES = ROOT / "eval" / "redteam"
RT_OUT = ROOT / "results" / "redteam"
ARMS = ("baseline_prompt_only", "baseline_prompt_with_schema", "agent_pipeline")
LABELS = {"baseline_prompt_only": "Baseline A", "baseline_prompt_with_schema": "Baseline B",
          "agent_pipeline": "Sentinel v13"}
V12 = "no_rule_coverage"


def arm_figures(rows: list[dict], agg: dict) -> dict:
    hit, total = clean_on_blocking(rows)
    return {
        "cases": agg["cases"],
        "unsafe_approvals": agg["unsafe_approvals"],
        "clean_on_blocking": hit,
        "blocking_cases": total,
        "recall": agg["strict"]["recall"],
        "precision": agg["strict"]["precision"],
        "f1": agg["strict"]["f1"],
        "false_alarms": agg["false_alarms_on_clean_cases"],
        "evidenced": f"{agg['findings_with_evidence']}/{agg['findings_total']}",
        "declared_gaps": agg["declared_coverage_gaps"],
        "gaps_cleared": agg["gap_cases_cleared_without_signoff"],
        "gap_cases": agg["cases_with_coverage_gaps"],
        "minutes": agg["modelled_reviewer_minutes_per_case"],
    }


def parity(insample_ab: dict, holdout_ab: dict) -> dict:
    """Per-case parity between `full` and `no_rule_coverage` on the 21 labelled cases.

    The generalisation claim for v13, computed rather than asserted: if the layer had been
    tuned to fit anything, this is where it would show.
    """
    compared = moved = 0
    moved_ids: list[str] = []
    for ab in (insample_ab, holdout_ab):
        if not ab or "full" not in ab or V12 not in ab:
            continue
        base = {r["case_id"]: r for r in ab[V12]["per_case"]}
        for row in ab["full"]["per_case"]:
            other = base.get(row["case_id"])
            if other is None:
                continue
            compared += 1
            same = (row["verdict"] == other["verdict"]
                    and sorted(row["tp"]) == sorted(other["tp"])
                    and sorted(row["fp"]) == sorted(other["fp"])
                    and sorted(row["fn"]) == sorted(other["fn"])
                    and row["declared_coverage_gaps"] == other["declared_coverage_gaps"])
            if not same:
                moved += 1
                moved_ids.append(row["case_id"])
    return {"labelled_cases_compared": compared, "cases_moved": moved, "moved_ids": moved_ids}


def render(figs: dict, v12: dict, rows: dict, notes: dict, par: dict, cases: list[dict]) -> str:
    S, T = figs["agent_pipeline"], v12
    A, B = figs["baseline_prompt_only"], figs["baseline_prompt_with_schema"]
    n = S["cases"]
    L = ["# Red team: migrations written to make this pipeline approve an outage", "",
         "`eval/cases` asks whether the pipeline finds the hazards I thought of. `eval/holdout` asks "
         "whether it finds them on a schema the rules were never written against. Neither can ask "
         "whether there is a class of hazard **nobody enumerated**, because both were labelled from "
         "the same hazard vocabulary, and a vocabulary is a list of what you already know.", "",
         "So this set was written the other way round: find a migration a Postgres primary would "
         "call an outage and this pipeline calls SAFE. Six probes, two hits. Neither hit was a wrong "
         "rule. Both were absent rules that nothing in this repository was counting.", "",
         "## The result", "",
         f"| metric | Baseline A | Baseline B | Sentinel v12 | Sentinel v13 |", "|---|---|---|---|---|",
         f"| **Unsafe approvals** (primary) | {A['unsafe_approvals']}/{n} | "
         f"{B['unsafe_approvals']}/{n} | **{T['unsafe_approvals']}/{n}** | "
         f"**{S['unsafe_approvals']}/{n}** |",
         f"| **Blocking cases given a clean verdict** (primary) | {A['clean_on_blocking']}"
         f"/{A['blocking_cases']} | {B['clean_on_blocking']}/{B['blocking_cases']} | "
         f"**{T['clean_on_blocking']}/{T['blocking_cases']}** | **{S['clean_on_blocking']}"
         f"/{S['blocking_cases']}** |",
         f"| Hazard recall (strict code) | {A['recall']} | {B['recall']} | {T['recall']} | "
         f"{S['recall']} |",
         f"| Hazard precision (strict code) | {A['precision']} | {B['precision']} | "
         f"{T['precision']} | {S['precision']} |",
         f"| False alarms on the two correct migrations | {A['false_alarms']} | "
         f"{B['false_alarms']} | {T['false_alarms']} | {S['false_alarms']} |",
         f"| Findings backed by machine evidence | {A['evidenced']} | {B['evidenced']} | "
         f"{T['evidenced']} | {S['evidenced']} |",
         f"| Blind spots named, with the object | {A['declared_gaps']} | {B['declared_gaps']} | "
         f"{T['declared_gaps']} | {S['declared_gaps']} |",
         f"| Gap cases cleared without a sign-off | {A['gaps_cleared']}/{A['gap_cases']} | "
         f"{B['gaps_cleared']}/{B['gap_cases']} | {T['gaps_cleared']}/{T['gap_cases']} | "
         f"{S['gaps_cleared']}/{S['gap_cases']} |",
         f"| Modelled reviewer minutes per case | {A['minutes']} | {B['minutes']} | {T['minutes']} | "
         f"{S['minutes']} |", "",
         "`Sentinel v12` is the `no_rule_coverage` ablation arm, which reproduces the shipped v12 "
         f"pipeline exactly. It approved every one of these {n} migrations.", "",
         "## The number to read first, because this set is in sample", "",
         "The v13 rules were written from these probes, so these seven cases prove two holes are "
         "closed - not that the pipeline generalises. The generalisation evidence runs the other "
         "way, and it is computed from the two ablation files rather than asserted here:", "",
         f"> `no_rule_coverage` and `full` are identical on "
         f"**{par['labelled_cases_compared'] - par['cases_moved']} of "
         f"{par['labelled_cases_compared']}** labelled cases in `eval/cases` and `eval/holdout`: "
         f"same verdict, same true positives, same false positives, same misses, same gap count. "
         f"Cases that moved: {par['cases_moved']}.",
         "",
         "A layer that moves no number that was already being measured is a layer that was missing. "
         "A layer tuned to fit the cases it was shown would have moved several.", "",
         "## What the baseline did better than the v12 pipeline, and why that is the point", "",
         "On `rt_02` and `rt_06` the text-only baseline names "
         "`CONCURRENT_DDL_IN_TRANSACTION` and the v12 pipeline does not. `BEGIN` and "
         "`CONCURRENTLY` in one file is a famous string, and a reviewer who reads the diff sees "
         "both. The v12 pipeline could not, and the reason is structural rather than accidental: "
         "every rule in `agents/risk_officer.py` was written to cover something *shadow replay is "
         "blind to*, so the rule set inherited the shape of replay's blind spots instead of the "
         "shape of the hazard space. Locks, volume, intent - all three are properties of one "
         "statement. Nothing in the design ever asked about a property of two.", "",
         "Baseline B pays for that reach on `rt_03`: it flags the index drop nothing uses, at "
         "`medium`, with no evidence and no way to tell the difference. That is the whole trade in "
         "one pair of cases. Naming a hazard is cheap; deciding is what costs.", "",
         "## Per case", "",
         "| case | ground truth | v12 verdict | v13 verdict | v13 findings | v13 coverage gaps |",
         "|---|---|---|---|---|---|"]
    v12_rows = {r["case_id"]: r for r in rows["v12"]}
    for case in cases:
        cid = case["id"]
        r = rows["v13"].get(cid)
        if not r:
            continue
        gaps = ", ".join(g["kind"] for g in notes.get(cid, {}).get("coverage_ledger", []))
        found = ", ".join(sorted(set(r["tp"]) | set(r["fp"]))) or "-"
        L.append(f"| `{cid}` | {'blocking' if r['gt_blocking'] else 'non-blocking'} | "
                 f"{v12_rows.get(cid, {}).get('verdict', '-')} | {r['verdict']} | {found} | "
                 f"{gaps or '-'} |")
    L += ["", "`rt_07` is the canary. It is a correct migration, and every arm has to stay quiet on "
          "it; the first version of the v13 rules did not, and neither did the first version of the "
          "residual-gap class, which flagged `case_06` as well. Both failures are recorded in "
          "`sentinel/rulebook.py` rather than deleted.", "",
          "## What this cost", "",
          f"The two new rules and the two new gap classes cost "
          f"{round(S['minutes'] - T['minutes'], 1)} modelled reviewer minutes per case on this set, "
          f"all of it in named human sign-offs on the three cases where the honest answer is a gap "
          f"rather than a finding. On the 21 labelled cases it costs nothing at all, because it "
          f"fires on nothing there.", "",
          "Commands, from a clean clone, no key and no network:", "",
          "```bash", "python3 eval/build_redteam.py            # regenerate the 7 red-team cases",
          "python3 eval/run_redteam.py               # 7 cases x 9 arms + this report",
          "```", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("run_redteam")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args(argv)

    if not args.report_only:
        rc = run_eval.main(["--cases", str(RT_CASES), "--out", str(RT_OUT), "--ablations",
                            "--trajectories", str(ROOT / "trajectories" / "redteam")])
        if rc:
            return rc

    ev = json.loads((RT_OUT / "evaluation.json").read_text())
    ab = json.loads((RT_OUT / "ablation.json").read_text())
    figs = {arm: arm_figures(ev["arms"][arm]["per_case"], ev["arms"][arm]["aggregate"])
            for arm in ARMS if arm in ev["arms"]}
    v12 = arm_figures(ab[V12]["per_case"], ab[V12]["aggregate"])
    rows = {"v13": {r["case_id"]: r for r in ev["arms"]["agent_pipeline"]["per_case"]},
            "v12": ab[V12]["per_case"]}
    par = parity(json.loads((ROOT / "results" / "ablation.json").read_text()),
                 json.loads((ROOT / "results" / "holdout" / "ablation.json").read_text()))
    cases = run_eval.load_cases(RT_CASES)

    summary = {
        "cases": len(cases),
        "arms": figs | {"sentinel_v12": v12},
        "in_sample_parity": par,
        "per_case": {cid: {"verdict": r["verdict"], "gt_blocking": r["gt_blocking"],
                           "tp": r["tp"], "fp": r["fp"], "fn": r["fn"],
                           "v12_verdict": next((x["verdict"] for x in rows["v12"]
                                                if x["case_id"] == cid), None)}
                     for cid, r in rows["v13"].items()},
    }
    (RT_OUT / "redteam.json").write_text(json.dumps(summary, indent=1) + "\n")
    report = render(figs, v12, rows, ev.get("agent_notes", {}), par, cases)
    (ROOT / "results" / "redteam.md").write_text(report + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
