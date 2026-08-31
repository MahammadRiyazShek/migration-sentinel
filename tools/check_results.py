"""Fail the build if the numbers the README claims are no longer true.

    python3 tools/check_results.py      # after eval/run_eval.py --ablations,
                                       # eval/run_holdout.py --ablations
                                       # and eval/run_redteam.py

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
        # v16 correction. This claim used to read "replay only is worse than rules only",
        # and it was true from v2 to v15: 2 unsafe approvals against 1. Switching the v16
        # plan audit on inside the replay-only arm removes one of the two - the plan the
        # pipeline wrote for the migration its missing rules had not understood carried an
        # ungated VALIDATE CONSTRAINT, so case_10 was capped instead of cleared. The
        # sentence the evidence still supports is the weaker one, so it is the one asserted,
        # and the arm-by-arm arithmetic including the historical number is recomputed in
        # results/redteam3.md rather than remembered.
        claim("execution alone is not sufficient: replay only is no better than rules only",
              replay_only >= rules_only, f"replay-only {replay_only} vs rules-only {rules_only}")
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
        # v13 moved five more decision files and added one, so the expected list moved with
        # it. The claim is unchanged in kind: every file that changed since the freeze is
        # named here, in the submission text, and in the report the held-out run prints.
        post_freeze = sorted(gen["freeze"]["changed"]) + sorted(gen["freeze"].get("added", []))
        claim("the decision code was hashed before the held-out labels existed, and every "
              "file changed or added since is named",
              man["files"] == 34 and post_freeze == [
                  "sentinel/agents/cartographer.py", "sentinel/agents/risk_officer.py",
                  "sentinel/agents/rollout_engineer.py", "sentinel/coverage.py",
                  "sentinel/hazards.py", "sentinel/llm/scripted.py", "sentinel/narrator.py",
                  "sentinel/orchestrator.py", "sentinel/report.py",
                  "sentinel/tools/query_corpus.py", "sentinel/tools/shadow_db.py",
                  "sentinel/tools/sql_parse.py", "sentinel/plan_audit.py",
                  "sentinel/rulebook.py", "sentinel/tools/parse_audit.py",
                  "sentinel/tools/sql_lex.py"],
              f"{man['files']} hashed, {len(post_freeze)} moved since: {post_freeze}")
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

    # ---------------------------------------------------------------- red team
    # v13. Everything above is measured on cases whose labels came out of the shared
    # hazard vocabulary, so everything above can only test hazards someone had already
    # named. These are measured on 7 cases written the other way round: find a migration
    # a Postgres primary calls an outage and this pipeline calls SAFE. Four of these
    # claims make the pipeline look worse, and one of them puts the text-only baseline
    # ahead of the v12 pipeline.
    rt_path = ROOT / "results" / "redteam" / "redteam.json"
    if rt_path.exists():
        rt = json.loads(rt_path.read_text())
        R = rt["arms"]["agent_pipeline"]
        R12 = rt["arms"]["sentinel_v12"]
        RB = rt["arms"]["baseline_prompt_with_schema"]
        par = rt["in_sample_parity"]
        per = rt["per_case"]

        claim("7 red-team cases, written to break the pipeline rather than to score it",
              rt["cases"] == 7 and R["cases"] == R12["cases"] == 7, rt["cases"])
        claim("the v12 pipeline approved every single red-team migration",
              R12["unsafe_approvals"] == 3
              and R12["clean_on_blocking"] == R12["blocking_cases"] == 3,
              f"{R12['unsafe_approvals']} unsafe, {R12['clean_on_blocking']}"
              f"/{R12['blocking_cases']} blocking cases cleared")
        claim("v13 makes no unsafe approval on the set built to produce them",
              R["unsafe_approvals"] == 0 and R["clean_on_blocking"] == 0,
              f"{R['unsafe_approvals']} unsafe, {R['clean_on_blocking']}"
              f"/{R['blocking_cases']} cleared")
        claim("the text-only baseline beat the v12 pipeline on this set (the unflattering one)",
              RB["clean_on_blocking"] < R12["clean_on_blocking"],
              f"baseline B cleared {RB['clean_on_blocking']}/{RB['blocking_cases']}, v12 cleared "
              f"{R12['clean_on_blocking']}/{R12['blocking_cases']}")
        claim("the v13 layer moves nothing that was already being measured",
              par["cases_moved"] == 0 and par["labelled_cases_compared"] == 21,
              f"{par['labelled_cases_compared'] - par['cases_moved']} of "
              f"{par['labelled_cases_compared']} labelled cases identical")
        claim("the correct index migration still comes back clean, so the new rule is not a "
              "wolf-crier",
              per["rt_07_index_swap_done_right"]["verdict"] == "SAFE"
              and R["false_alarms"] == 0,
              f"rt_07 {per['rt_07_index_swap_done_right']['verdict']}, "
              f"{R['false_alarms']} false alarms")
        claim("the correct-but-wrapped index swap raises the transaction hazard and NOT the "
              "access-path one",
              per["rt_06_index_swap_inside_transaction"]["fp"] == []
              and per["rt_06_index_swap_inside_transaction"]["tp"]
              == ["CONCURRENT_DDL_IN_TRANSACTION"],
              f"tp {per['rt_06_index_swap_inside_transaction']['tp']}, "
              f"fp {per['rt_06_index_swap_inside_transaction']['fp']}")
        claim("on three cases the honest answer is a declared gap rather than a finding, and "
              "none of them is cleared",
              R["declared_gaps"] == 3 and R["gaps_cleared"] == 0 and R["gap_cases"] == 3,
              f"{R['declared_gaps']} gaps, {R['gaps_cleared']}/{R['gap_cases']} cleared")
        claim("baseline B pays for its reach in false alarms the pipeline does not make",
              RB["false_alarms"] > R["false_alarms"],
              f"baseline B {RB['false_alarms']}, pipeline {R['false_alarms']}")
        claim("every red-team finding cites machine evidence and no baseline finding does",
              R["evidenced"].split("/")[0] == R["evidenced"].split("/")[1]
              and RB["evidenced"].startswith("0/"),
              f"pipeline {R['evidenced']}, baseline B {RB['evidenced']}")
        claim("closing these two holes costs reviewer minutes rather than saving them",
              R["minutes"] > R12["minutes"],
              f"{R12['minutes']} -> {R['minutes']} modelled minutes per case")

    # ------------------------------------------------------------ red team, round 2
    # v14. Round 1 asked whether a hazard class was unenumerated. This asks whether the op
    # list is the migration, and it is not: a `--` inside a string literal cost the v13
    # parser the second half of a two-statement file. Read the parity claim first - the same
    # splitter swap moves nothing on 28 labelled cases.
    rt2_path = ROOT / "results" / "redteam2" / "redteam2.json"
    if rt2_path.exists():
        rt2 = json.loads(rt2_path.read_text())
        Q = rt2["arms"]["agent_pipeline"]
        Q13 = rt2["arms"]["sentinel_v13"]
        QB = rt2["arms"]["baseline_prompt_with_schema"]
        par2 = rt2["in_sample_parity"]
        per2 = rt2["per_case"]
        loss = rt2["splitter_loss_totals"]

        claim("6 round-2 cases, aimed at the parser rather than at the rules",
              rt2["cases"] == 6 and Q["cases"] == Q13["cases"] == 6, rt2["cases"])
        claim("the retired splitter loses whole statements and invents others, recomputed from "
              "the retired code",
              loss["statements_lost"] >= 2 and loss["phantom_statements"] >= 2,
              f"{loss['statements_lost']} lost, {loss['phantom_statements']} phantom")
        claim("v14 more than doubles recall on the set the v13 parser could not read",
              Q["recall"] >= 2 * Q13["recall"], f"v13 {Q13['recall']} -> v14 {Q['recall']}")
        claim("every v14 finding on this set is about text Postgres executes",
              Q["precision"] == 1.0 and Q["false_alarms"] == 0,
              f"precision {Q['precision']}, {Q['false_alarms']} false alarms")
        claim("v13 raised false alarms here, all of them evidenced, which is the unflattering "
              "half: evidence is not the same property as being about the right file",
              Q13["false_alarms"] > 0
              and Q13["evidenced"].split("/")[0] == Q13["evidenced"].split("/")[1],
              f"{Q13['false_alarms']} false alarms, {Q13['evidenced']} evidenced, precision "
              f"{Q13['precision']}")
        claim("the commented-out destructive statement is a hazard to v13 and to baseline B, "
              "and to v14 it is a comment",
              per2["rt2_04_nested_comment_phantom"]["verdict"] == "SAFE"
              and per2["rt2_04_nested_comment_phantom"]["v13_verdict"] == "BLOCK",
              f"v14 {per2['rt2_04_nested_comment_phantom']['verdict']}, v13 "
              f"{per2['rt2_04_nested_comment_phantom']['v13_verdict']}")
        claim("a script Postgres refuses reports only that it is refused",
              per2["rt2_03_unterminated_literal"]["tp"] == ["MIGRATION_TEXT_UNPARSED"]
              and per2["rt2_03_unterminated_literal"]["fp"] == [],
              f"tp {per2['rt2_03_unterminated_literal']['tp']}, fp "
              f"{per2['rt2_03_unterminated_literal']['fp']}")
        claim("the DO block is named and still not cleared, and the two hazards inside it stay "
              "in the label as published misses",
              sorted(per2["rt2_02_do_block_hides_the_drop"]["fn"])
              == ["BREAKING_QUERY", "DESTRUCTIVE_NO_EXPAND_CONTRACT"]
              and per2["rt2_02_do_block_hides_the_drop"]["verdict"] == "BLOCK",
              f"found {per2['rt2_02_do_block_hides_the_drop']['tp']}, missed "
              f"{sorted(per2['rt2_02_do_block_hides_the_drop']['fn'])}")
        claim("the v14 layer moves nothing that was already being measured, across all three "
              "labelled sets",
              par2["cases_moved"] == 0 and par2["labelled_cases_compared"] == 28,
              f"{par2['labelled_cases_compared'] - par2['cases_moved']} of "
              f"{par2['labelled_cases_compared']} labelled cases identical")
        claim("closing the parser holes costs reviewer minutes on this set and none elsewhere",
              Q["minutes"] < Q13["minutes"] and QB["minutes"] > Q["minutes"],
              f"v13 {Q13['minutes']}, v14 {Q['minutes']}, baseline B {QB['minutes']} modelled "
              f"minutes per case")

    # -------------------------------------------------------- cross-interpreter
    # v12. Everything above is measured under one interpreter. "3.11 and 3.12 verified" used to
    # mean a green test suite on both, which is a claim about exceptions rather than about
    # numbers: dict ordering, float repr, `round`, `re` and the bundled sqlite3 can all move a
    # published verdict without raising. tools/check_cross_version.py reruns every generator
    # under both and diffs the two results/ trees. The second claim is the unflattering half.
    xv_path = ROOT / "results" / "cross_version.json"
    if xv_path.exists():
        xv = json.loads(xv_path.read_text())
        versions = " and ".join(i["version"] for i in xv["interpreters"])
        claim(f"no decision depends on the interpreter: CPython {versions} agree byte for byte",
              (xv["decision_differences"] == 0 and len(xv["interpreters"]) >= 2
               and not xv["files_present_in_one_tree_only"] and xv["files_compared"] >= 140),
              f"{xv['files_compared']} files compared, {xv['decision_differences']} decision "
              f"differences")
        claim("the published wall-clock figures are the one thing that is not portable",
              (xv["max_relative_clock_delta"] > 0 and xv["wall_clock_only"] > 0
               and xv["clock_numbers_compared"] > 100),
              f"{xv['wall_clock_only']} files moved on timing alone, worst delta "
              f"{xv['max_relative_clock_delta'] * 100:.0f}% "
              f"({xv['max_absolute_clock_delta_ms']} ms) over "
              f"{xv['clock_numbers_compared']} numbers")

    # -------------------------------------------------------------- red team 3 (v16)
    # The pipeline reviewing the SQL it writes itself. Two of these are unflattering: the
    # defect count is against plans this repository has been shipping since v2, and one
    # ablation arm got better for a reason nobody designed.
    rt3_path = ROOT / "results" / "redteam3.json"
    if rt3_path.exists():
        rt3 = json.loads(rt3_path.read_text())
        A15, A16 = rt3["arms"]["no_plan_audit"], rt3["arms"]["full"]
        lab3 = rt3["labelled"]
        it = rt3["replay_only_interaction"]
        claim("3 round-3 probes, aimed at the SQL this pipeline writes rather than the SQL it "
              "reads", A15["cases"] == A16["cases"] == 3, A16["cases"])
        claim("v15 printed a clean verdict over every defective plan it generated; v16 prints none",
              (A15["clean_verdict_over_defective_plan"] == A15["defective_plan_cases"]
               and A16["clean_verdict_over_defective_plan"] == 0),
              f"v15 {A15['clean_verdict_over_defective_plan']}/{A15['defective_plan_cases']}, "
              f"v16 {A16['clean_verdict_over_defective_plan']}/{A16['defective_plan_cases']}")
        claim("every plan defect v15 generated was shipped unreviewed, and none of v16's is",
              (A15["plan_defects_shipped_unreviewed"] == A15["plan_defects_present"] > 0
               and A16["plan_defects_shipped_unreviewed"] == 0),
              f"v15 {A15['plan_defects_shipped_unreviewed']}/{A15['plan_defects_present']}, "
              f"v16 {A16['plan_defects_shipped_unreviewed']}/{A16['plan_defects_present']}")
        claim("the canary stays silent: a rollback nothing depends on yet is not a defect",
              A16["false_alarms_on_canary"] == 0, A16["false_alarms_on_canary"])
        claim("the plan audit moves nothing that was already being measured, across all four "
              "labelled sets",
              lab3["cases_moved"] == 0 and lab3["cases_compared"] == 34,
              f"{lab3['cases_compared'] - lab3['cases_moved']} of {lab3['cases_compared']} "
              f"labelled cases identical")
        claim("the plans this repository has been shipping since v2 carry defects nobody wrote "
              "a case for (the unflattering half)",
              len(lab3["defects"]) >= 6 and lab3["defect_cases"] >= 5,
              f"{len(lab3['defects'])} defects across {lab3['defect_cases']} labelled cases, "
              f"{lab3['defects_under_a_verified_plan']} of them under a printed "
              f"'plan verified: true'")
        claim("closing it costs reviewer minutes rather than saving them, in named sign-offs",
              (ab and S["modelled_reviewer_minutes_per_case"]
               >= ab["no_plan_audit"]["aggregate"]["modelled_reviewer_minutes_per_case"]),
              f"v15 {ab['no_plan_audit']['aggregate']['modelled_reviewer_minutes_per_case']} -> "
              f"v16 {S['modelled_reviewer_minutes_per_case']} modelled minutes per case"
              if ab else "no ablation.json")
        claim("the one number outside redteam3 that this layer moved is an ablation arm, not the "
              "shipped one (the other unflattering half)",
              (it["replay_only_v15"]["unsafe_approvals"] == 2
               and it["replay_only_v16"]["unsafe_approvals"] == 1
               and replay_only == rules_only),
              f"replay-only 2/12 with the audit off, {it['replay_only_v16']['unsafe_approvals']}/12 "
              f"with it on, rules-only {rules_only}/12 in the scored arm - so 'replay "
              f"alone is worse than rules alone' now needs plan_audit=False to reproduce")

    width = max(len(c[0]) for c in CLAIMS)
    bad = 0
    for text, ok, got in CLAIMS:
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {text.ljust(width)}  {got}")
    print(f"\n{len(CLAIMS) - bad}/{len(CLAIMS)} claims hold")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
