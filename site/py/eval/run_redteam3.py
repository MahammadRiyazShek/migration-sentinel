"""Run RED-TEAM ROUND 3: the pipeline reviewing the SQL it writes itself.

    python3 eval/run_redteam3.py                 # 3 probes + parity over 34 labelled cases
    python3 eval/run_redteam3.py --report-only    # rebuild the report from results/ on disk

SUPERVISOR LOG (v16), carried at the top of the file that acts on it
-------------------------------------------------------------------
The three hidden assumptions this harness exists to test, and what it found:

  A1  "verified means the plan is safe."  It meant phase 1 breaks no statement in
      today's corpus.  Two thirds of every plan - the contract phase and the rollback -
      were never parsed, never partitioned by the rule inventory, never replayed and
      never gated, and the packet printed "phase 1 verified" above all three.  FOUND, on
      cases that were already in the repository: 6 defects across the 21 labelled cases,
      every one of them under a `plan verified: true`.

  A2  "if it mattered, a number would have moved."  No number could.  The hazard list is
      produced by rules that run over the input before the Rollout Engineer writes a
      line, and the ground truth labels describe the input, so a defect in our own SQL
      is unscoreable by every metric in `results/`.  This is the fourth time in this
      repository that the honest answer to "why did no number move" is "nothing was
      counting", and the first time it was true of the output rather than the input.

  A3  "the fix is to flag generated destructive statements."  That is the `case_06`
      failure with a new name: every additive migration in the world generates a
      rollback that drops the column it just added.  REMOVED after `rt3_03`: a rollback
      is a defect only when a code step in the same packet asks the team to start
      depending on what it removes.  A property of two artefacts, which is the class of
      question nothing here had ever asked - see the hot take in the README.

READ THE PARITY NUMBER FIRST
---------------------------
These 3 probes are IN SAMPLE: `sentinel/plan_audit.py` was written from them.  The
evidence that this layer was *missing* rather than tuned is computed below and runs the
other way: `no_plan_audit` reproduces v15 exactly, and `full` is identical to it on every
input verdict, hazard, severity and coverage gap across all 34 labelled cases in
`eval/cases`, `eval/holdout`, `eval/redteam` and `eval/redteam2`.

WHAT THIS SET CANNOT TELL YOU
-----------------------------
There is no baseline column in the table below, and it is not an oversight.  A one-prompt
review emits prose; it never writes an expand/contract plan, so on this axis the two
baselines cannot be wrong and cannot be right.  The arm that can generate this class of
defect is the advanced solution, and the only fair comparison is against the previous
release of the advanced solution.  Read `12/12 verified plans` in the headline table with
that in mind: it always meant "phase 1 replays clean", and 6 of those 21 verified plans
carried a step nothing had reviewed.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sentinel import plan_audit  # noqa: E402
from sentinel.llm import get_llm  # noqa: E402
from sentinel.orchestrator import review  # noqa: E402
from sentinel.tools import sql_parse  # noqa: E402

RT3_CASES = ROOT / "eval" / "redteam3"
OUT_JSON = ROOT / "results" / "redteam3.json"
OUT_MD = ROOT / "results" / "redteam3.md"
INCIDENTS = str(ROOT / "memory" / "incidents.jsonl")
V15 = "no_plan_audit"
V16 = "full"
LABELLED_DIRS = ("cases", "holdout", "redteam", "redteam2")
CLEAN_VERDICTS = {"SAFE", "SAFE_WITH_PLAN", "APPROVE"}


def load(directory: pathlib.Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(directory.glob("*.json"))]


def run(case: dict, features: str) -> dict:
    return review(case, get_llm("scripted"), incidents_path=INCIDENTS, learned_path=None,
                  trace=False, run_id=f"rt3-{features}", features=features)["report"]


def audit_of(report: dict, case: dict) -> dict:
    """Audit a report's plan with the v16 auditor, whatever arm produced it.

    Recomputed from the artefact under test rather than read out of the arm that
    produced it, so the count for v15 is a measurement of v15's own output.
    """
    plan = dict(report["plan"])
    # the v16 arm appends its own findings to `human_gates`, and a gate that names the
    # object is a gate as far as the matcher is concerned. Strip them before recounting,
    # so this number is what the arm *generated*, not what its own notice healed.
    plan["human_gates"] = [g for g in plan.get("human_gates", [])
                           if not g.startswith("PLAN DEFECT (")]
    schema = sql_parse.parse_schema(case["schema_sql"])
    for table, rows in (case.get("row_estimates") or {}).items():
        if table in schema.tables:
            schema.tables[table].row_estimate = rows
    return plan_audit.audit(plan, schema, case["queries"], case.get("seed", {}))


def surface(report: dict) -> tuple:
    """The decision surface about the migration under review. Not about our own SQL."""
    return (report.get("input_verdict", report["verdict"]),
            tuple(h["code"] for h in report["hazards"]),
            tuple(h["severity"] for h in report["hazards"]),
            len(report["coverage_ledger"]["gaps"]))


def probe_rows() -> list[dict]:
    rows = []
    for case in load(RT3_CASES):
        gt = case["ground_truth"]
        r15, r16 = run(case, V15), run(case, V16)
        a15, a16 = audit_of(r15, case), audit_of(r16, case)
        rows.append({
            "case_id": case["id"],
            "title": case["title"],
            "expected_plan_defects": gt.get("plan_defects", []),
            "v15": {"verdict": r15["verdict"], "plan_verified": r15["plan_verification"]["verified"],
                    "defects_reported": 0, "defects_present": len(a15["findings"]),
                    "defect_codes": a15["finding_codes"],
                    "human_gates": len(r15["plan"]["human_gates"])},
            "v16": {"verdict": r16["verdict"], "plan_verified": r16["plan_verification"]["verified"],
                    "defects_reported": len(r16["plan_audit"]["findings"]),
                    "defects_present": len(a16["findings"]),
                    "defect_codes": r16["plan_audit"]["finding_codes"],
                    "gates_trusted": r16["plan_audit"]["gates_trusted"],
                    "human_gates": len(r16["plan"]["human_gates"])},
        })
    return rows


def arm(rows: list[dict], key: str) -> dict:
    defective = [r for r in rows if r["expected_plan_defects"]]
    canaries = [r for r in rows if not r["expected_plan_defects"]]
    return {
        "cases": len(rows),
        "plan_defects_present": sum(r[key]["defects_present"] for r in rows),
        "plan_defects_reported": sum(r[key]["defects_reported"] for r in rows),
        "plan_defects_shipped_unreviewed": sum(r[key]["defects_present"] - r[key]["defects_reported"]
                                               for r in rows),
        "clean_verdict_over_defective_plan":
            sum(1 for r in defective if r[key]["verdict"] in CLEAN_VERDICTS),
        "defective_plan_cases": len(defective),
        "false_alarms_on_canary": sum(r[key]["defects_reported"] for r in canaries),
        "human_gates_total": sum(r[key]["human_gates"] for r in rows),
    }


def labelled() -> dict:
    """Parity on the input decision surface, and the defect count on plans nobody wrote for.

    Both computed, not asserted. If the audit had leaked into the hazard list, or had been
    tuned against anything it was shown, this is where it would show.
    """
    compared = moved = 0
    moved_ids: list[str] = []
    defects: list[dict] = []
    per_set: dict[str, dict] = {}
    for name in LABELLED_DIRS:
        cases = load(ROOT / "eval" / name)
        set_defects = 0
        for case in cases:
            r15, r16 = run(case, V15), run(case, V16)
            compared += 1
            if surface(r15) != surface(r16):
                moved += 1
                moved_ids.append(case["id"])
            found = r16["plan_audit"]["findings"]
            set_defects += len(found)
            for f in found:
                defects.append({"case_id": case["id"], "set": name, "code": f["code"],
                                "script": f["script"], "statement": f["statement"],
                                "v15_verdict": r15["verdict"],
                                "v15_plan_verified": r15["plan_verification"]["verified"]})
        per_set[name] = {"cases": len(cases), "plan_defects": set_defects}
    return {"cases_compared": compared, "cases_moved": moved, "moved_ids": moved_ids,
            "per_set": per_set, "defects": defects,
            "defect_cases": len({d["case_id"] for d in defects}),
            "defects_under_a_verified_plan": sum(1 for d in defects if d["v15_plan_verified"])}


def replay_only_interaction() -> dict:
    """The one number outside eval/redteam3 that this layer moved, and it was not `full`.

    `no_static` is the replay-only arm: the static rules are off and shadow replay is the
    whole review. Since v2 that arm has carried 2 unsafe approvals against 1 for
    rules-only, and `results/ablation.md` reads "replay alone is worse than rules alone"
    off it. Switching the plan audit on removes one of the two, on `case_10`: no rule
    priced the 48M-row constraint validation, and the plan the pipeline wrote for the
    migration it had not understood contained an ungated `VALIDATE CONSTRAINT`, so the
    verdict was capped instead of cleared.

    That is a real safety gain and a bad diagnosis. The reviewer is told a generated step
    has no human gate; nobody says the words "48 million rows". It stops the approval
    without naming the hazard, so the v2 sentence is corrected rather than kept: execution
    alone is not sufficient, and the arithmetic that used to prove it needs the audit
    switched off to reproduce.
    """
    from sentinel.orchestrator import FEATURE_SETS

    cases = load(ROOT / "eval" / "cases")
    out = {}
    for label, arm, audit_on in (("replay_only_v15", "no_static", False),
                                 ("replay_only_v16", "no_static", True),
                                 ("rules_only_v16", "no_replay", True)):
        feats = dict(FEATURE_SETS[arm], plan_audit=audit_on)
        unsafe, ids = 0, []
        for case in cases:
            r = review(case, get_llm("scripted"), incidents_path=INCIDENTS, learned_path=None,
                       trace=False, run_id="rt3-int", features=feats)["report"]
            blocking = bool(case["ground_truth"]["blocking"])
            if blocking and r["verdict"] in CLEAN_VERDICTS:
                unsafe += 1
                ids.append(case["id"])
        out[label] = {"unsafe_approvals": unsafe, "cases": ids}
    return out


def render(data: dict) -> str:
    rows, lab = data["per_case"], data["labelled"]
    a15, a16 = data["arms"][V15], data["arms"][V16]
    L = ["# Red team, round 3: the plan is an artefact too", "",
         "Round 1 asked whether a hazard class existed that nobody had enumerated. Round 2 asked "
         "whether the op list is the migration. Both aimed at the file a human wrote, because every "
         "honesty layer in this repository aims at the file a human wrote.", "",
         "This round aimed at the file *this pipeline* writes. Three scripts per run - phase 1, "
         "phase 2, a rollback - printed in the packet, one of them checked, by replay, which "
         "`results/ablation.md` has called the weaker half of the design since v2.", "",
         "```sql",
         "-- rt3_01, the migration. Genuinely safe, and v15 correctly says so.",
         "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL DEFAULT '';",
         "",
         "-- rt3_01, two of the things v15 then printed under 'phase 1 verified':",
         "--   code step: deploy code that always writes customers.billing_email",
         "--   rollback:  ALTER TABLE \"customers\" DROP COLUMN \"billing_email\";",
         "```", "",
         "Run those in the order the packet prints them and every write from the deploy the packet "
         "asked for fails. Shadow replay of that rollback breaks zero corpus statements, which is "
         "why no amount of execution could have found it: the statements that break are the ones "
         "the packet is asking someone to write tomorrow. It is a property of two artefacts, and "
         "every check in this repository until v16 was a property of one.", "",
         "## The three probes", "",
         "| case | v15 verdict | v15 plan | v16 verdict | defects present | v15 reported | "
         "v16 reported |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| `{r['case_id']}` | {r['v15']['verdict']} | "
                 f"{'verified' if r['v15']['plan_verified'] else 'not verified'} | "
                 f"{r['v16']['verdict']} | {r['v16']['defects_present']} | "
                 f"{r['v15']['defects_reported']} | {r['v16']['defects_reported']} |")
    L += ["", "| metric | Sentinel v15 | Sentinel v16 |", "|---|---|---|",
          f"| plan defects present in the SQL the arm generated | {a15['plan_defects_present']} | "
          f"{a16['plan_defects_present']} |",
          f"| plan defects reported to the reviewer | {a15['plan_defects_reported']} | "
          f"{a16['plan_defects_reported']} |",
          f"| plan defects shipped unreviewed | **{a15['plan_defects_shipped_unreviewed']}** | "
          f"**{a16['plan_defects_shipped_unreviewed']}** |",
          f"| clean verdict printed over a defective plan | "
          f"**{a15['clean_verdict_over_defective_plan']}/{a15['defective_plan_cases']}** | "
          f"**{a16['clean_verdict_over_defective_plan']}/{a16['defective_plan_cases']}** |",
          f"| false alarms on the canary (`rt3_03`) | {a15['false_alarms_on_canary']} | "
          f"{a16['false_alarms_on_canary']} |",
          f"| human gates in the plans | {a15['human_gates_total']} | {a16['human_gates_total']} |",
          "",
          "The defect count for v15 is not a claim about v15's opinion of its own plan - v15 has no "
          "opinion, it never looks. It is v15's generated SQL, audited afterwards by the v16 "
          "auditor, recomputed from the artefact rather than read out of a report.", "",
          "## The number to read first: 34 labelled cases, nothing moved", "",
          f"`no_plan_audit` reproduces v15 exactly. Across all {lab['cases_compared']} labelled "
          f"cases in `eval/cases`, `eval/holdout`, `eval/redteam` and `eval/redteam2`, `full` and "
          f"`no_plan_audit` are identical on every input verdict, every hazard code, every severity "
          f"and every coverage-gap count: **{lab['cases_moved']} case(s) moved**.", "",
          "That is by construction, and the construction is the argument. A plan defect is a "
          "property of our output, so it cannot enter the hazard list without corrupting every "
          "recall, precision and severity number in `results/` - those labels describe the input. "
          "It caps the verdict and becomes a human gate instead, exactly where v2 put a declared "
          "coverage gap.", "",
          f"On those same {lab['cases_compared']} cases the audit finds "
          f"**{len(lab['defects'])} defect(s)** across **{lab['defect_cases']} case(s)** in plans "
          f"this repository has been shipping since v2, "
          f"**{lab['defects_under_a_verified_plan']} of them** under a printed "
          f"`plan verified: true`:", "",
          "| case | set | defect | script | generated statement |", "|---|---|---|---|---|"]
    for d in lab["defects"]:
        L.append(f"| `{d['case_id']}` | {d['set']} | {d['code']} | {d['script']} | "
                 f"`{d['statement']}` |")
    it = data.get("replay_only_interaction") or {}
    if it:
        L += ["", "## The number this layer moved, and it was not the shipped one", "",
              "`full` is unchanged on all 34 labelled cases. One ablation arm is not, and the "
              "correction belongs here rather than in a commit message.", "",
              "| arm | unsafe approvals on the 12 in-sample cases |", "|---|---|",
              f"| replay only, plan audit off (the v2 through v15 number) | "
              f"**{it['replay_only_v15']['unsafe_approvals']}/12** |",
              f"| replay only, plan audit on | "
              f"**{it['replay_only_v16']['unsafe_approvals']}/12** |",
              f"| rules only | **{it['rules_only_v16']['unsafe_approvals']}/12** |", "",
              "`results/ablation.md` has read *replay alone is worse than rules alone* off that "
              "first row since v2. With the audit on, replay-only loses one of its two unsafe "
              "approvals - on `case_10`, where no rule priced the 48M-row constraint validation "
              "and the plan the pipeline wrote for the migration it had not understood contained "
              "an ungated `VALIDATE CONSTRAINT`. The verdict was capped instead of cleared.", "",
              "That is a real safety gain and a bad diagnosis. The reviewer is told that a "
              "generated step has no human gate. Nobody says the words *48 million rows*. So the "
              "v2 sentence is corrected rather than kept: **execution alone is not sufficient**, "
              "and the arithmetic that used to demonstrate it now needs `plan_audit=False` to "
              "reproduce. A plan is a second, independent view of the same risk, and a tool that "
              "refuses for the wrong reason is still a tool that refused.", ""]
    L += ["", "## What this round did not fix", "",
          "- **The gate matcher reads names, not questions.** A destructive contract step counts as "
          "gated when a human gate names its object. A gate that names the object and asks the "
          "wrong question passes. Every time this audit trusted a sentence it says so: "
          "`audit_gate_text_only` is in the gap list of the packet, and the count is in the report. "
          "It is R1 from `sentinel/rulebook.py` one level up again, declared rather than closed.",
          "- **`GENERATED_TEXT_UNPARSED` was written as a hypothesis and turned out to be the "
          "third defect class.** It went into the audit because the Rollout Engineer is a text "
          "producer and this repository has already been wrong once about a text producer "
          "(`eval/redteam2`). It fires on `rt2_03`, which nobody wrote for it: the input carries an "
          "unterminated string literal, v14 onwards correctly refuses to certify a file it cannot "
          "read - and the Rollout Engineer then built a keyset-batched UPDATE out of the mangled "
          "parse and the packet printed it under *Phase 1 - expand (safe to run now)*. The verdict "
          "was already BLOCK, so nobody would have run it; the packet was still handing a reviewer "
          "SQL that Postgres refuses, formatted as the recommendation. v16 names it, gates it, and "
          "`sentinel/report.py` stops presenting an unreadable script as runnable. The fix this "
          "round did **not** make: the engineer still generates a plan from a parse the pipeline "
          "has already declared unreliable. Refusing to plan at all is the right answer and it is "
          "a behaviour change to the arm under measurement, so it is written down here rather than "
          "shipped in the last hour of a deadline.",
          "- **There is no baseline column.** A one-prompt review never writes a plan, so it cannot "
          "produce this defect class, and it cannot avoid it either. The only fair comparison on "
          "this axis is against the previous release of the advanced solution, which is what the "
          "table above is.",
          "- **Phase 2 is still not proved safe, only replayed and counted.** The generated contract "
          "phase is *supposed* to break today's statements; that is what the code steps are for. "
          "The audit publishes which corpus statements it breaks so a reviewer can check that each "
          "one has a code step, instead of being told that it does.", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()
    if args.report_only and OUT_JSON.exists():
        data = json.loads(OUT_JSON.read_text())
    else:
        rows = probe_rows()
        data = {"per_case": rows,
                "arms": {V15: arm(rows, "v15"), V16: arm(rows, "v16")},
                "labelled": labelled(),
                "replay_only_interaction": replay_only_interaction()}
        OUT_JSON.write_text(json.dumps(data, indent=2) + "\n")
    OUT_MD.write_text(render(data))
    a15, a16 = data["arms"][V15], data["arms"][V16]
    print(f"red team 3: {a15['cases']} probes · plan defects shipped unreviewed "
          f"v15 {a15['plan_defects_shipped_unreviewed']} -> v16 "
          f"{a16['plan_defects_shipped_unreviewed']} · clean verdicts over a defective plan "
          f"v15 {a15['clean_verdict_over_defective_plan']}/{a15['defective_plan_cases']} -> v16 "
          f"{a16['clean_verdict_over_defective_plan']}/{a16['defective_plan_cases']} · "
          f"{data['labelled']['cases_moved']} of {data['labelled']['cases_compared']} labelled "
          f"cases moved · {len(data['labelled']['defects'])} defects found in shipped plans")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
