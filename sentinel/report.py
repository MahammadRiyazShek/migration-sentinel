"""Render the review packet a human actually reads."""
from __future__ import annotations

from typing import Any

BADGE = {"BLOCK": "BLOCK - do not merge", "SAFE_WITH_PLAN": "SHIP AS PLAN - not as written",
         "SAFE": "SAFE - no blocking hazards found",
         "NEEDS_COVERAGE_SIGNOFF": "NOT CLEARED - coverage gap on an affected object"}
GAP_LABEL = {
    "unmodelled_statement": "statement not modelled by the parser",
    "in_place_data_mutation": "existing rows rewritten; replay cannot see changed answers",
    "value_class_erased": "a value class is erased and the rollback does not restore it",
    "uncovered_object": "no statement in the corpus references this object",
}
SEV_LABEL = {"blocker": "BLOCKER", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}


def render(report: dict[str, Any]) -> str:
    r = report
    L: list[str] = []
    L += [f"# Migration review: {r['title'] or r['case_id']}", "",
          f"**{BADGE[r['verdict']]}**", "",
          r["summary"], "",
          f"`run {r['run_id']}` · case `{r['case_id']}` · owning service `{r['owner_service']}` · "
          f"{r['wall_ms']} ms · model {r['model_usage']['model']} "
          f"({r['model_usage']['calls']} calls, ${r['model_usage']['cost_usd']:.4f})", ""]

    nar = r.get("narrator") or {}
    mode = nar.get("mode", "pattern")
    if nar.get("headline_source") == "tool" and mode == "structural":
        L += ["> **The headline above was written by the tools, not by the model.** In this build "
              "the narrator cannot write the sentence above the badge on any run "
              "(`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows "
              "cannot become the verdict sentence. The model's prose, where it survives the guard, "
              "appears under *Model commentary* at the end, labelled unverified.", ""]
    if nar.get("summary_overridden"):
        L += ["> **The model's summary was not printed.** The narrator guard "
              "(`sentinel/narrator.py`) rejected it"
              + (" and it was dropped from the packet entirely" if mode == "structural"
                 else " and the headline above was written from the tool output instead")
              + ". Reason(s): " + "; ".join(nar["summary_reasons"])
              + f'. What the model wrote: "{nar.get("model_summary", "")}"', ""]
    if nar.get("questions_dropped"):
        L += ["> **Reviewer questions were filtered.** " + "; ".join(nar["questions_dropped"])
              + ".", ""]

    if r.get("verdict_capped_by_plan_audit"):
        L += ["> **Not cleared on this pipeline's own output.** The migration itself carries no "
              f"blocking hazard, and {len(r['plan_audit']['findings'])} statement(s) in the SQL "
              "this packet generated were never reviewed by anything until now. The verdict is "
              "capped rather than clean: no hazard has been invented and nothing has been "
              "certified. See *Plan self-audit* below.", ""]

    if r.get("verdict_capped_by_coverage"):
        gaps = r["coverage_ledger"]["gaps"]
        L += [f"> **Not cleared on coverage.** The hazards found here are not blocking, but "
              f"{len(gaps)} object(s) this migration touches sit inside a blind spot of the review. "
              "The verdict is capped rather than clean: no hazard has been invented, and nothing has "
              "been certified either. See *Coverage ledger* below.", ""]

    if r["escalated_to_human"]:
        L += ["> **Escalated to a human.** The pipeline could not produce a phase 1 it can prove is "
              "backwards compatible. Do not proceed on automation alone.", ""]

    L += ["## Hazards", ""]
    if not r["hazards"]:
        L += ["No hazards found by execution or by the static rules.", ""]
    else:
        L += ["| # | Severity | Hazard | Where | Found by |", "|---|---|---|---|---|"]
        for i, h in enumerate(r["hazards"], 1):
            where = ", ".join(h["objects"]) or "-"
            L.append(f"| {i} | **{SEV_LABEL[h['severity']]}** | {h['title']} | `{where}` | {h['source']} |")
        L.append("")
        for i, h in enumerate(r["hazards"], 1):
            L += [f"### {i}. [{SEV_LABEL[h['severity']]}] {h['title']}", "", h["summary"], ""]
            for ev in h["evidence"]:
                L.append(f"- evidence: {ev}")
            if h["memory_refs"]:
                L.append(f"- prior incidents: {', '.join(h['memory_refs'])}")
            if h["services"]:
                L.append(f"- services affected: {', '.join(h['services'])}")
            L.append("")

    rep = r["blast_radius"]["replay"]
    L += ["## Blast radius", "",
          f"- statements in the corpus that touch the changed objects: "
          f"{len(r['blast_radius']['dependent_queries'])} (weighted score {r['blast_radius']['blast_score']})",
          f"- shadow replay: {rep['queries_ok_before']}/{rep['queries_run']} statements passed before, "
          f"{rep['queries_ok_after']}/{rep['queries_run']} after",
          f"- reproduced failures: {len(rep['broken'])} · silent column changes: {len(rep['column_drift'])} "
          f"· data-migration failures: {len(rep['data_errors'])}", ""]
    if rep["broken"]:
        L += ["| statement | service | engine error |", "|---|---|---|"]
        for b in rep["broken"]:
            L.append(f"| `{b['query_id']}` | {b['service']} | {b['error']} |")
        L.append("")

    plan = r["plan"]
    pa_pre = r.get("plan_audit") or {}
    unreadable = sorted({f["script"] for f in (pa_pre.get("findings") or [])
                         if f["code"] == "GENERATED_TEXT_UNPARSED"})
    L += ["## Recommended rollout", ""]
    if unreadable:
        L += ["> **This is not runnable SQL and must not be treated as a recommendation.** The "
              f"generated {', '.join(unreadable)} script contains a construct this pipeline cannot "
              "read back, which means it was built from a parse of the input that is already known "
              "to be unreliable. It is printed for the reviewer's information only. See *Plan "
              "self-audit*.", ""]
    L += [
          f"Plan generated on attempt {plan['attempt']} of {r['attempts']}; phase 1 "
          + ("**verified**: every statement in the corpus still passes after phase 1. That is a "
             "statement about phase 1 and about today's corpus only - the audit of all three "
             "generated scripts is the section below."
             if r["plan_verification"]["verified"]
             else "**not verified** - see the escalation above."), ""]
    for label, key in [("Phase 1 - expand (safe to run now)", "phase1_sql"),
                       ("Phase 2 - contract (only after the code steps below)", "phase2_sql"),
                       ("Rollback for phase 1", "rollback_sql")]:
        if plan[key]:
            L += [f"### {label}", "", "```sql", *plan[key], "```", ""]
    if plan["code_steps"]:
        L += ["### Application changes required between the phases", ""]
        L += [f"{i}. {s}" for i, s in enumerate(plan["code_steps"], 1)] + [""]
    if plan["human_gates"]:
        L += ["### Human decisions required (the tool will not decide these)", ""]
        L += [f"- {g}" for g in plan["human_gates"]] + [""]
    if plan["questions"]:
        src = plan.get("questions_source", "model")
        label = ("### Questions for the reviewer, written from the hazard codes"
                 if src == "tool" else
                 "### Questions for the reviewer (drafted by the model, guarded prose, not evidence)")
        L += [label, ""] + [f"- {q}" for q in plan["questions"]] + [""]

    pa = r.get("plan_audit") or {}
    if pa and not pa.get("disabled"):
        L += ["## Plan self-audit", "",
              f"The three scripts above are output from this pipeline, so they are reviewed like "
              f"any other artefact it is handed: {pa['statements_audited']} generated statement(s) "
              f"parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked "
              f"against the code steps, and replayed. A defect here is a defect in *our* SQL, not "
              f"in the migration under review, so it never enters the hazard table - it caps the "
              f"verdict and becomes a human gate.", ""]
        if pa["findings"]:
            L += ["| # | defect | script | statement |", "|---|---|---|---|"]
            for i, f in enumerate(pa["findings"], 1):
                L.append(f"| {i} | **{f['code']}** | {f['script']} | `{f['statement']}` |")
            L.append("")
            for i, f in enumerate(pa["findings"], 1):
                L += [f"### {i}. {f['title']}", "", f["why"] + ".", ""]
                for ev in f["evidence"]:
                    L.append(f"- evidence: {ev}")
                L += [f"- closes when: {f['closes_with']}", ""]
        else:
            L += ["No defect found in the generated SQL: every destructive contract step is named "
                  "by a human gate, no rollback statement removes something a code step in this "
                  "packet asks the team to start using, and every generated statement has a kind "
                  "something in this pipeline inspects.", ""]
        if pa["gaps"]:
            L += ["What this audit trusted rather than checked:", ""]
            for g in pa["gaps"]:
                L.append(f"- `{g['object']}` ({g['kind']}, generated {g['script']}): {g['why']}")
            L.append("")
        rep_pa = pa.get("replay") or {}
        if rep_pa.get("ran"):
            for script, fig in sorted((rep_pa.get("scripts") or {}).items()):
                L.append(f"- shadow replay of the generated {script} script against the "
                         f"post-phase-1 schema: {fig['broken_after']} of {fig['queries_run']} "
                         f"corpus statement(s) break"
                         + (f" ({', '.join(fig['broken_query_ids'])})" if fig["broken_query_ids"]
                            else "")
                         + (" - expected for a contract step, which is what the code steps above "
                            "are for; the number is printed so it can be checked rather than "
                            "assumed" if script == "phase2" and fig["broken_after"] else ""))
            L.append("")
        elif rep_pa.get("why"):
            L += [f"- the generated scripts were not replayed: {rep_pa['why']}", ""]

    cov = r.get("coverage_ledger") or {"gaps": []}
    if cov["gaps"]:
        L += ["## Coverage ledger", "",
              f"{len(cov['gaps'])} gap(s) between what this migration touches and what this review "
              f"could actually observe. A gap is an absence of evidence, so it is recorded as a "
              f"decision for a person rather than as a finding with a severity.", "",
              "| object | gap | why it is a gap | closes when |", "|---|---|---|---|"]
        for g in cov["gaps"]:
            flag = " **(irreversible)**" if g["irreversible"] else ""
            L.append(f"| `{g['object']}`{flag} | {GAP_LABEL.get(g['kind'], g['kind'])} | "
                     f"{g['why']} | {g['closes_with']} |")
        L.append("")

    L += ["## What this review did not check", "",
          "- Lock behaviour is inferred from declared row estimates and static rules; the shadow "
          "database is SQLite and cannot reproduce PostgreSQL lock queues.",
          "- Fixture data is a small synthetic sample, so data-dependent hazards are detected only "
          "where the fixtures expose them.",
          "- Application code is only visible through the query corpus; anything issuing dynamic SQL "
          "that is not in the corpus is invisible here."]
    for gap in r["coverage_gaps"]:
        L.append(f"- unmodelled statement: {gap}")
    L += ["", "## Approval", "",
          "Nothing was executed against a real database. Phase 1 can be dry-run against a local "
          "sandbox copy with:", "", "```bash",
          f"python -m sentinel execute --report results/{r['case_id']}.json "
          "--i-approve --reviewer \"your name\"", "```", "",
          "A qualified reviewer signs off here before any deploy: ______________________", ""]

    # Model prose lands here, after the evidence, never above the badge. If it was
    # dropped by the guard the packet says so rather than hiding the fact.
    if mode == "structural":
        L += ["## Model commentary (unverified prose, not evidence)", ""]
        if nar.get("model_note"):
            L += [f"> {nar['model_note']}", "",
                  "The narrator wrote the paragraph above. It passed the prose guard, which is a "
                  "statement about its wording and not about its truth. Nothing in it produced, "
                  "removed or reordered a single finding in this packet: every hazard, severity, "
                  "plan statement and verdict above comes from a tool call recorded in the "
                  "trajectory.", ""]
        else:
            L += ["The narrator's prose was rejected by the guard and is not reproduced here. "
                  "Reason(s): " + "; ".join(nar.get("model_note_reasons") or ["none recorded"])
                  + ".", ""]
    return "\n".join(L)
