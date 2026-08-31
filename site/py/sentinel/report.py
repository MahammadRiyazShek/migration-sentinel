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
    if nar.get("summary_overridden"):
        L += ["> **The model's summary was not printed.** The narrator guard "
              "(`sentinel/narrator.py`) rejected it and the headline above was written from the "
              "tool output instead. Reason(s): " + "; ".join(nar["summary_reasons"])
              + f'. What the model wrote: "{nar.get("model_summary", "")}"', ""]
    if nar.get("questions_dropped"):
        L += ["> **Reviewer questions were filtered.** " + "; ".join(nar["questions_dropped"])
              + ".", ""]

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
    L += ["## Recommended rollout", "",
          f"Plan generated on attempt {plan['attempt']} of {r['attempts']}; phase 1 "
          + ("**verified**: every statement in the corpus still passes after phase 1."
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
        L += ["### Questions for the reviewer", ""] + [f"- {q}" for q in plan["questions"]] + [""]

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
    return "\n".join(L)
