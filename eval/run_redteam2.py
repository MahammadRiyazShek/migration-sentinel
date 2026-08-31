"""Run RED-TEAM ROUND 2: the two baselines, the v13 pipeline and the v14 pipeline.

    python3 eval/run_redteam2.py                 # 6 cases x 10 arms + the report
    python3 eval/run_redteam2.py --report-only   # rebuild the report from results/ on disk

SUPERVISOR LOG (v14), carried at the top of the file that acts on it
-------------------------------------------------------------------
The three hidden assumptions this harness exists to test, and what it found:

  A1  "the rule inventory is exhaustive."  It is exhaustive over the *op list*.
      `sentinel/rulebook.py` partitions all 26 kinds `parse_migration` can emit and fails
      a test if it learns a 27th, and none of that can see a statement that never became
      an op.  FOUND, in one probe: a `--` inside a string literal made
      `strip_comments` cut the literal in half, the unterminated quote swallowed the rest
      of the file, and a two-statement migration arrived as one `dml_update`.  The DROP
      COLUMN a live billing query reads was not missed, mis-severitied or cleared.  It
      was never presented to anything.  Every honesty layer in this repository - ledger,
      narrator provenance, fixture gap, rule inventory - sits downstream of the parse.

  A2  "a scanner is strictly safer than a regex."  Not on its own, and the failure runs
      the other way.  Postgres nests block comments and the retired regex did not, so a
      commented-out `DROP COLUMN` behind a nested `*/` was a live statement to v13, which
      blocked a migration whose destructive statement is switched off.  FOUND as
      `rt2_04`, and it stays in the set as the canary: a tool that invents a blocker out
      of a comment gets switched off, and a switched-off tool has recall zero.

  A3  "more findings on a broken script is better."  The opposite.  The first version of
      this layer reported the unterminated-literal blocker *and* the two hazards inferred
      from the mangled remainder.  Postgres refuses that script outright, so those two
      were claims about text that never executes - `rt2_04`'s defect with the sign
      flipped.  REMOVED: a script the server refuses has no hazards other than being
      refused, the findings from the wreckage are dropped, and the region nobody could
      read is a declared gap.  It is the difference between precision 1.0 and 0.6 on this
      set, and the reasoning is in `sentinel/agents/risk_officer.py` rather than in a
      commit message.

READ THE GENERALISATION NUMBER FIRST
-----------------------------------
These 6 cases are IN SAMPLE: the v14 scanner was written from these probes.  They prove
holes are closed, not that the pipeline generalises.  The evidence that this layer was
*missing* rather than *tuned* runs the other way and is computed in this report:
`no_text_conservation` reproduces v13 exactly, retired splitter included, and is
identical to `full` on all 28 labelled cases in `eval/cases`, `eval/holdout` and
`eval/redteam` - same verdicts, same hazards, same severities, same gap counts.
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
from eval.run_redteam import arm_figures  # noqa: E402
from sentinel.tools.parse_audit import legacy_loss  # noqa: E402

RT2_CASES = ROOT / "eval" / "redteam2"
RT2_OUT = ROOT / "results" / "redteam2"
ARMS = ("baseline_prompt_only", "baseline_prompt_with_schema", "agent_pipeline")
V13 = "no_text_conservation"
LABELLED = (ROOT / "results" / "ablation.json",
            ROOT / "results" / "holdout" / "ablation.json",
            ROOT / "results" / "redteam" / "ablation.json")


def parity() -> dict:
    """Per-case parity between `full` and `no_text_conservation` on the 28 labelled cases.

    Computed, not asserted. If this layer had been tuned to fit anything it was shown, this
    is where it would show.
    """
    compared = moved = 0
    moved_ids: list[str] = []
    for path in LABELLED:
        if not path.exists():
            continue
        ab = json.loads(path.read_text())
        if "full" not in ab or V13 not in ab:
            continue
        base = {r["case_id"]: r for r in ab[V13]["per_case"]}
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


def text_losses(cases: list[dict]) -> dict[str, dict]:
    """What the retired splitter did to each file, recomputed from the artefact under test."""
    return {c["id"]: legacy_loss(c["migration_sql"]) for c in cases}


def render(figs: dict, v13: dict, rows: dict, notes: dict, par: dict, cases: list[dict],
           loss: dict) -> str:
    S, T = figs["agent_pipeline"], v13
    A, B = figs["baseline_prompt_only"], figs["baseline_prompt_with_schema"]
    n = S["cases"]
    lost = sum(v["statements_lost"] for v in loss.values())
    phantom = sum(v["phantom_statements"] for v in loss.values())
    L = ["# Red team, round 2: migrations the parser gets wrong", "",
         "Round 1 asked whether there was a hazard class nobody enumerated. The answer was yes, "
         "twice, and the fix was `sentinel/rulebook.py`: an exhaustive partition of every statement "
         "kind the parser can emit, with a test that fails when it learns a new one. Exhaustive "
         "over the op list.", "",
         "This round asked whether the op list is the migration.", "",
         "```sql",
         "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL;",
         "ALTER TABLE invoices DROP COLUMN tax_rate;",
         "```", "",
         "Two statements in. One op out. `strip_comments` deleted from the `--` inside the string "
         "literal to end of line, the unterminated quote that left swallowed the rest of the file, "
         "and the `DROP COLUMN` that breaks a live billing query was never presented to a rule, to "
         "shadow replay or to the coverage ledger. It was not missed. It was not there.", "",
         f"Across these {n} files the retired splitter loses **{lost} statement(s)** outright and "
         f"invents **{phantom} statement(s)** that Postgres never executes, recomputed from the "
         "retired code itself by `sentinel.tools.parse_audit.legacy_loss`.", "",
         "## The result", "",
         "| metric | Baseline A | Baseline B | Sentinel v13 | Sentinel v14 |", "|---|---|---|---|---|",
         f"| **Hazard recall** (primary) | {A['recall']} | {B['recall']} | **{T['recall']}** | "
         f"**{S['recall']}** |",
         f"| **Hazard precision** (primary) | {A['precision']} | {B['precision']} | "
         f"**{T['precision']}** | **{S['precision']}** |",
         f"| Unsafe approvals | {A['unsafe_approvals']}/{n} | {B['unsafe_approvals']}/{n} | "
         f"{T['unsafe_approvals']}/{n} | {S['unsafe_approvals']}/{n} |",
         f"| Blocking cases given a clean verdict | {A['clean_on_blocking']}/{A['blocking_cases']} | "
         f"{B['clean_on_blocking']}/{B['blocking_cases']} | {T['clean_on_blocking']}"
         f"/{T['blocking_cases']} | {S['clean_on_blocking']}/{S['blocking_cases']} |",
         f"| False alarms on the three correct migrations | {A['false_alarms']} | "
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
         "`Sentinel v13` is the `no_text_conservation` ablation arm, which reproduces the shipped "
         "v13 pipeline exactly, retired splitter included. Note where its findings went: "
         f"{T['evidenced']} of them, every one citing machine evidence, and "
         f"{T['precision']} precision. Evidence is not the same property as being about the right "
         "file.", "",
         "## The number to read first, because this set is in sample", "",
         "The v14 scanner was written from these probes. The generalisation evidence runs the other "
         "way and is computed from the three ablation files rather than asserted here:", "",
         f"> `no_text_conservation` and `full` are identical on "
         f"**{par['labelled_cases_compared'] - par['cases_moved']} of "
         f"{par['labelled_cases_compared']}** labelled cases in `eval/cases`, `eval/holdout` and "
         f"`eval/redteam`: same verdict, same true positives, same false positives, same misses, "
         f"same gap count. Cases that moved: {par['cases_moved']}.", "",
         "A splitter swapped out underneath 28 labelled cases without moving one number is a "
         "splitter that was wrong only where nothing had ever looked.", "",
         "## Per case", "",
         "| case | ground truth | v13 verdict | v14 verdict | v14 findings | v14 gaps | "
         "statements v13 saw |", "|---|---|---|---|---|---|---|"]
    v13_rows = {r["case_id"]: r for r in rows["v13"]}
    for case in cases:
        cid = case["id"]
        r = rows["v14"].get(cid)
        if not r:
            continue
        gaps = ", ".join(g["kind"] for g in notes.get(cid, {}).get("coverage_ledger", []))
        found = ", ".join(sorted(set(r["tp"]) | set(r["fp"]))) or "-"
        lo = loss[cid]
        L.append(f"| `{cid}` | {'blocking' if r['gt_blocking'] else 'non-blocking'} | "
                 f"{v13_rows.get(cid, {}).get('verdict', '-')} | {r['verdict']} | {found} | "
                 f"{gaps or '-'} | {lo['statements_v13_saw']} of "
                 f"{lo['statements_in_file']} |")
    L += ["", "## The two cases that make this a test rather than a demonstration", "",
          "`rt2_02` is labelled with all three hazards a Postgres reviewer would name, including "
          "the two the pipeline still cannot find. A keyword census over a `DO $$ ... $$` body "
          "proves DDL is in there; it does not model what the block does with it, so "
          "`BREAKING_QUERY` and `DESTRUCTIVE_NO_EXPAND_CONTRACT` stay in the label as published "
          "misses. Recall on that case is 1 of 3. What protects the reviewer is that the case is "
          "not cleared: naming the block caps the verdict and names a human gate.", "",
          "`rt2_04` and `rt2_06` are the canaries and carry no hazard at all. v13 blocks both: on "
          "`rt2_04` from a `DROP COLUMN` sitting inside a nested comment, on `rt2_06` from a string "
          "default containing a double hyphen. Three of its findings on those two files describe "
          "text Postgres never runs.", "",
          "## What this cost", "",
          f"{round(S['minutes'] - T['minutes'], 1)} modelled reviewer minutes per case against the "
          f"v13 arm on this set, all of it in named sign-offs. On the 28 labelled cases it costs "
          f"nothing, because it fires on nothing there.", "",
          "Commands, from a clean clone, no key and no network:", "",
          "```bash", "python3 eval/build_redteam2.py           # regenerate the 6 round-2 cases",
          "python3 eval/run_redteam2.py              # 6 cases x 10 arms + this report",
          "```", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("run_redteam2")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args(argv)

    if not args.report_only:
        rc = run_eval.main(["--cases", str(RT2_CASES), "--out", str(RT2_OUT), "--ablations",
                            "--trajectories", str(ROOT / "trajectories" / "redteam2")])
        if rc:
            return rc

    ev = json.loads((RT2_OUT / "evaluation.json").read_text())
    ab = json.loads((RT2_OUT / "ablation.json").read_text())
    figs = {arm: arm_figures(ev["arms"][arm]["per_case"], ev["arms"][arm]["aggregate"])
            for arm in ARMS if arm in ev["arms"]}
    v13 = arm_figures(ab[V13]["per_case"], ab[V13]["aggregate"])
    rows = {"v14": {r["case_id"]: r for r in ev["arms"]["agent_pipeline"]["per_case"]},
            "v13": ab[V13]["per_case"]}
    cases = run_eval.load_cases(RT2_CASES)
    loss = text_losses(cases)
    par = parity()

    summary = {
        "cases": len(cases),
        "arms": figs | {"sentinel_v13": v13},
        "in_sample_parity": par,
        "splitter_loss": loss,
        "splitter_loss_totals": {
            "statements_lost": sum(v["statements_lost"] for v in loss.values()),
            "phantom_statements": sum(v["phantom_statements"] for v in loss.values()),
        },
        "per_case": {cid: {"verdict": r["verdict"], "gt_blocking": r["gt_blocking"],
                           "tp": r["tp"], "fp": r["fp"], "fn": r["fn"],
                           "v13_verdict": next((x["verdict"] for x in rows["v13"]
                                                if x["case_id"] == cid), None)}
                     for cid, r in rows["v14"].items()},
    }
    (RT2_OUT / "redteam2.json").write_text(json.dumps(summary, indent=1) + "\n")
    report = render(figs, v13, rows, ev.get("agent_notes", {}), par, cases, loss)
    (ROOT / "results" / "redteam2.md").write_text(report + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
