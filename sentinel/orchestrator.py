"""Deterministic orchestration of the five agents.

The control flow is a fixed pipeline with one feedback loop, not a free-running
"figure it out" agent.  That is a design choice: for a review that gates a
production deploy, a reviewer needs the same steps in the same order every time,
and every claim traceable to a tool call.  The model contributes wording and
reviewer questions; it never decides whether something is a hazard.

  cartographer -> blast_radius -> risk_officer -> (rollout_engineer <-> verifier)* -> approval gate

v14 adds one step inside the cartographer rather than a sixth agent, on purpose: the parse
is reconciled against an independent lexical scan of the same file before anything
downstream is allowed to treat the op list as the migration. A defect upstream of every
agent does not get its own agent; it gets an invariant. See `sentinel/tools/parse_audit.py`.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from .agents.blast_radius import BlastRadius
from .agents.cartographer import Cartographer
from .agents.risk_officer import RiskOfficer
from .agents.rollout_engineer import Policy, RolloutEngineer
from .agents.verifier import Verifier
from . import coverage as coverage_tools
from . import narrator as narrator_tools
from . import plan_audit as plan_audit_tools
from .hazards import SEVERITY_ORDER
from .tools import parse_audit, query_corpus, shadow_db, sql_parse
from .tools.incident_memory import IncidentMemory
from .tools.registry import ToolRegistry
from .trace import Tracer

MAX_ATTEMPTS = 3

# Ablation switches. `full` is the shipped configuration; the others exist so the
# changelog can point at a number instead of a feeling.
FEATURE_SETS = {
    "full": {"replay": True, "static": True, "memory": True, "verify": True, "coverage": True,
             "rule_coverage": True, "text_conservation": True, "plan_audit": True},
    "no_replay": {"replay": False, "static": True, "memory": True, "verify": False,
                  "coverage": True, "rule_coverage": True, "text_conservation": True, "plan_audit": True},
    "no_static": {"replay": True, "static": False, "memory": True, "verify": True,
                  "coverage": True, "rule_coverage": True, "text_conservation": True, "plan_audit": True},
    "no_memory": {"replay": True, "static": True, "memory": False, "verify": True,
                  "coverage": True, "rule_coverage": True, "text_conservation": True, "plan_audit": True},
    "no_verify": {"replay": True, "static": True, "memory": True, "verify": False,
                  "coverage": True, "rule_coverage": True, "text_conservation": True, "plan_audit": True},
    # v2 component. `no_coverage` reproduces the v1 behaviour exactly: gaps are
    # still reported, they just do not constrain the verdict.
    "no_coverage": {"replay": True, "static": True, "memory": True, "verify": True,
                    "coverage": False, "rule_coverage": True, "text_conservation": True, "plan_audit": True},
    # v13 component. `no_rule_coverage` reproduces v12 exactly: the two rules the
    # red-team pass found missing are off, and the ledger goes back to declaring blind
    # spots only about objects some rule had already looked at. It is identical to
    # `full` on all 21 labelled cases in this repository, which is the evidence that
    # this layer was absent rather than retuned - and it is 2/6 unsafe approvals on
    # eval/redteam, where `full` is 0/6.
    "no_rule_coverage": {"replay": True, "static": True, "memory": True, "verify": True,
                         "coverage": True, "rule_coverage": False, "text_conservation": True,
                         "plan_audit": True},
    # v14 component. `no_text_conservation` reproduces v13 exactly, splitter included: the
    # migration is split by the retired regex stripper, and the reconciliation between the
    # op list and the file does not run. It is identical to `full` on all 28 labelled cases
    # in eval/cases, eval/holdout and eval/redteam, which is the evidence that this layer
    # was absent rather than retuned - and it loses two thirds of a migration on
    # eval/redteam2/rt2_01 without reporting anything.
    "no_text_conservation": {"replay": True, "static": True, "memory": True, "verify": True,
                             "coverage": True, "rule_coverage": True, "text_conservation": False,
                             "plan_audit": True},
    # v16 component. `no_plan_audit` reproduces v15 exactly: the three scripts this
    # pipeline generates are never parsed, partitioned, cross-checked against the code
    # steps or replayed, and "plan verified" means phase 1 broke no corpus statement. It
    # is identical to `full` on every verdict, hazard and severity in all 34 labelled
    # cases - the plan audit cannot touch the hazard list by construction - and it ships
    # 6 unreviewed plan defects on the 21 cases in eval/cases and eval/holdout, where
    # `full` ships 0. See sentinel/plan_audit.py and results/redteam3.md.
    "no_plan_audit": {"replay": True, "static": True, "memory": True, "verify": True,
                      "coverage": True, "rule_coverage": True, "text_conservation": True,
                      "plan_audit": False},
}


def build_registry(memory: IncidentMemory, tracer: Tracer,
                   text_conservation: bool = True) -> ToolRegistry:
    reg = ToolRegistry(tracer)
    reg.register("schema.parse", sql_parse.parse_schema,
                 "Parse current DDL into a structural schema model.")
    reg.register("migration.parse",
                 (sql_parse.parse_migration if text_conservation
                  else lambda sql: sql_parse.parse_migration(sql, legacy_split=True)),
                 "Parse a migration script into typed operations.")
    reg.register("migration.audit", parse_audit.audit,
                 "Reconcile the op list against an independent lexical scan of the same file: "
                 "unterminated constructs, statements no operation accounts for, procedural bodies.")
    reg.register("schema.apply_ops", sql_parse.apply_ops,
                 "Apply operations to a schema model, returning the post-migration schema.")
    reg.register("corpus.dependents", query_corpus.dependents,
                 "Find application statements that reference touched objects.")
    reg.register("corpus.blast_score", query_corpus.blast_score,
                 "Weight dependent statements by declared criticality.")
    reg.register("shadow.replay", shadow_db.replay,
                 "Materialise pre/post schemas in SQLite, seed fixtures, execute the corpus in both.")
    reg.register("memory.escalation", memory.escalation,
                 "Look up prior incidents for a hazard code and table; returns severity bump + ids.")
    reg.register("memory.recall", memory.recall, "Full prior-incident records for a hazard code.")
    reg.register("corpus.access_path_users", query_corpus.access_path_users,
                 "Statements that use given columns as a lookup, sort or grouping key.")
    reg.register("plan.audit", plan_audit_tools.audit,
                 "Review the SQL this pipeline generated: parse all three scripts, partition every "
                 "generated statement by the rule inventory, cross-check the rollback against the "
                 "code steps, and replay the two scripts the verifier never ran.")
    reg.register("coverage.ledger", coverage_tools.ledger,
                 "Enumerate what this review structurally could not see, per affected object.")
    return reg


def review(case: dict[str, Any], llm, incidents_path: str, learned_path: str | None = None,
           max_attempts: int = MAX_ATTEMPTS, trace: bool = True,
           run_id: str | None = None, features: str | dict[str, bool] = "full",
           narrator_mode: str = "structural",
           guard_narrator: bool | None = None) -> dict[str, Any]:
    """Run the five agents over one case.

    `narrator_mode` decides who owns the sentence a reviewer reads first:

      "structural"  v5, shipped. The headline is a pure function of tool output on
                    every run. Model prose is demoted to a labelled note under the
                    evidence, and only if it passes the guard.
      "pattern"     v3. A blocklist in `sentinel/narrator.py` decides whether the
                    model's headline is printed. `eval/model_invariance.py` shows
                    `hostile-fluent` walking straight through it.
      "off"         v2. Model prose is copied into the packet unchecked.

    `guard_narrator` is the v3 argument, kept so older call sites keep working:
    True maps to "pattern", False to "off".
    """
    if guard_narrator is not None:
        narrator_mode = "pattern" if guard_narrator else "off"
    if narrator_mode not in narrator_tools.NARRATOR_MODES:
        raise ValueError(f"unknown narrator mode {narrator_mode!r}")
    guarded = narrator_mode != "off"
    feat = FEATURE_SETS[features] if isinstance(features, str) else features
    started = time.perf_counter()
    run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
    tracer = Tracer(run_id, case["id"], enabled=trace)
    memory = IncidentMemory(incidents_path, learned_path)
    tools = build_registry(memory, tracer,
                           text_conservation=feat.get("text_conservation", True))

    parsed = Cartographer(tools, llm, tracer).run(
        case, text_conservation=feat.get("text_conservation", True))
    blast = BlastRadius(tools, llm, tracer).run(case, parsed, use_replay=feat["replay"])
    risk = RiskOfficer(tools, llm, tracer).run(case, parsed, blast,
                                               use_static=feat["static"], use_memory=feat["memory"],
                                               use_coverage=feat.get("coverage", True),
                                               use_rule_coverage=feat.get("rule_coverage", True),
                                               use_text_conservation=feat.get("text_conservation", True))

    engineer = RolloutEngineer(tools, llm, tracer)
    engineer.guard_narrator = guarded
    verifier = Verifier(tools, llm, tracer)
    policy = Policy()
    attempt, plan, check = 1, None, None
    if not feat["verify"]:
        plan = engineer.run(case, parsed, blast, risk, policy, 1)
        check = {"verified": False, "problems": ["plan verification disabled for this run"],
                 "replay": {}, "unmodelled": []}
        tracer.note(verifier.NAME, "plan verification disabled for this run")
        max_attempts = 0
    while attempt <= max_attempts:
        plan = engineer.run(case, parsed, blast, risk, policy, attempt)
        check = verifier.run(case, parsed, plan)
        if check["verified"]:
            break
        reason = "; ".join(check["problems"][:3])
        tracer.feedback(verifier.NAME,
                        f"phase 1 is not safe yet: {reason}. Tightening the policy and regenerating.",
                        attempt)
        views_in_phase1 = [s for s in plan["phase1_sql"] if "view" in s.lower()]
        if views_in_phase1 and policy.include_view_changes:
            policy.include_view_changes = False
            policy.notes.append("view redefinitions moved to phase 2: replacing a view in phase 1 "
                                "changed the column set a live consumer depends on")
        elif not policy.minimal_phase1:
            policy.minimal_phase1 = True
            policy.notes.append("fell back to a minimal additive phase 1: everything not provably "
                                "backwards compatible moved to phase 2")
        else:
            break
        attempt += 1
        tracer.retry(engineer.NAME, attempt, reason)

    # v16: the plan is an artefact this pipeline produced, so it gets reviewed like any
    # other artefact this pipeline was handed. Findings cap the verdict and become human
    # gates; they never enter the hazard list, because the hazard list is a statement
    # about the migration under review and this is a statement about our own output.
    if feat.get("plan_audit", True) and plan is not None:
        plan_review = tools.call("plan.audit", agent="verifier", plan=plan, schema=parsed["schema"],
                                 queries=case["queries"], seed=case.get("seed", {}),
                                 replay_tool=shadow_db.replay)
        new_gates = plan_audit_tools.gates(plan_review)
        if new_gates:
            plan["human_gates"] = list(dict.fromkeys(list(plan["human_gates"]) + new_gates))
        for f in plan_review["findings"]:
            tracer.checkpoint("plan self-audit", "PLAN DEFECT",
                              f"{f['code']} in the generated {f['script']} script: {f['why']} "
                              f"Closes when: {f['closes_with']}")
    else:
        plan_review = {"statements_audited": 0, "scripts": {}, "findings": [],
                       "finding_codes": [], "gaps": [], "gap_kinds": [], "kind_inventory": [],
                       "gates_trusted": 0, "clean": None,
                       "replay": {"ran": False, "why": "plan audit disabled for this run"},
                       "disabled": True}

    verdict, capped_by_plan_audit = plan_audit_tools.cap(risk["verdict"], plan_review)
    if capped_by_plan_audit:
        tracer.checkpoint("plan self-audit sign-off", "REQUIRED",
                          "The verdict is capped at NEEDS_COVERAGE_SIGNOFF by this pipeline's audit "
                          "of its own output: the migration itself carries no blocking hazard, but "
                          f"{len(plan_review['findings'])} statement(s) in the SQL this packet is "
                          "asking someone to run were never reviewed by anything. No hazard has "
                          "been invented and nothing has been cleared.")

    escalated = feat["verify"] and not check["verified"]
    if escalated:
        tracer.checkpoint("plan verification", "ESCALATED",
                          "The pipeline could not produce a phase 1 it can prove is safe. "
                          "A human must decide the sequencing. Remaining problems: "
                          + "; ".join(check["problems"][:5]))

    raw_summary = llm.complete(
        "You write the two-sentence verdict at the top of a database migration review.",
        f"verdict={verdict} counts={risk['counts']} broken={len(blast['replay'].broken)}",
        tag="executive_summary",
        payload={"verdict": verdict, "counts": risk["counts"],
                 "broken_queries": len(blast["replay"].broken),
                 "coverage_gaps": len(risk["coverage_ledger"]["gaps"]),
                 "plan_verified": check["verified"]}).text
    tracer.model_call("orchestrator", llm.calls[-1])

    # The narrator writes the sentence a reviewer reads first, so it is treated as
    # untrusted input rather than as output. The guard can only remove model text:
    # it cannot invent a hazard, move a severity or change a verdict.
    narrator_facts = {"counts": risk["counts"], "broken_queries": len(blast["replay"].broken),
                      "coverage_gaps": len(risk["coverage_ledger"]["gaps"]),
                      "plan_verified": check["verified"],
                      "plan_defects": len(plan_review["findings"])}
    narrator_info = narrator_tools.compose_summary(
        raw_summary, verdict, narrator_facts, mode=narrator_mode)
    summary = narrator_info.pop("summary")
    summary_reasons = narrator_info["summary_reasons"]
    if narrator_mode == "structural":
        tracer.checkpoint("narrator provenance", "HEADLINE FROM TOOLS",
                          "The sentence above the badge was rendered from the tool output. The "
                          "model cannot write it in this build, so a lie in wording the guard has "
                          "never seen cannot become the verdict sentence. "
                          + ("The model's prose also failed the guard and was dropped entirely "
                             "(reasons: " + "; ".join(summary_reasons) + ")."
                             if summary_reasons else
                             "The model's prose is printed below the evidence, labelled "
                             "unverified."))
    elif summary_reasons:
        tracer.checkpoint("narrator guard", "SUMMARY REJECTED",
                          "The model's headline was not printed. Reasons: "
                          + "; ".join(summary_reasons)
                          + ". The packet shows a summary written from the tool output instead.")
    narrator_info.update({
        "questions_source": plan.get("questions_source", "model"),
        "questions_dropped": plan.get("questions_dropped", []),
    })

    if risk["verdict_capped_by_coverage"]:
        tracer.checkpoint("coverage sign-off", "REQUIRED",
                          "The verdict is capped at NEEDS_COVERAGE_SIGNOFF. The hazards found are "
                          "not blocking, but this review has "
                          f"{len(risk['coverage_ledger']['gaps'])} declared blind spot(s) on objects "
                          "the migration touches, and a packet must not certify what it did not see. "
                          "Each gap is a human gate in the plan.")

    tracer.checkpoint("pre-execution approval", "REQUIRED",
                      "Nothing has been executed against any real database. `sentinel execute` runs "
                      "phase 1 against a local sandbox copy only, and refuses to run without "
                      "--i-approve plus the reviewer's name.")

    tin, tout = llm.total_tokens
    report = {
        "run_id": run_id,
        "case_id": case["id"],
        "title": case.get("title", ""),
        "owner_service": case.get("owner_service"),
        "verdict": verdict,
        "input_verdict": risk["verdict"],
        "summary": summary,
        "narrator": narrator_info,
        "counts": risk["counts"],
        "hazards": [h.to_json() for h in risk["hazards"]],
        "blast_radius": {
            "dependent_queries": blast["dependents"],
            "blast_score": blast["blast_score"],
            "replay": blast["replay"].to_json(),
        },
        "plan": plan,
        "plan_verification": check,
        "plan_audit": plan_review,
        "verdict_capped_by_plan_audit": capped_by_plan_audit,
        "escalated_to_human": escalated,
        "coverage_gaps": risk["coverage_gaps"] + check.get("unmodelled", []),
        "coverage_ledger": risk["coverage_ledger"],
        "verdict_capped_by_coverage": risk["verdict_capped_by_coverage"],
        "change_set": parsed["change_set"],
        "attempts": attempt,
        "features": feat,
        "tool_calls": tools.calls,
        "model_usage": {"provider": llm.provider, "model": llm.model, "calls": len(llm.calls),
                        "tokens_in": tin, "tokens_out": tout,
                        "cost_usd": round(llm.total_cost, 6)},
        "wall_ms": round((time.perf_counter() - started) * 1000, 1),
        "severity_order": SEVERITY_ORDER,
    }
    return {"report": report, "tracer": tracer, "memory": memory,
            "hazards": risk["hazards"], "case": case}


def record_learning(memory: IncidentMemory, report: dict[str, Any]) -> list[str]:
    """Opt-in: remember the blocking hazards of this run so later runs escalate faster."""
    written = []
    for h in report["hazards"]:
        if h["severity"] != "blocker":
            continue
        tables = sorted({o.split(".")[0] for o in h["objects"]}) or []
        entry = {"id": f"learned:{report['case_id']}:{h['code']}", "hazard_code": h["code"],
                 "tables": tables, "services": h.get("services", []), "severity_bump": 1,
                 "source_run": report["run_id"],
                 "summary": h["summary"][:180]}
        before = len(memory.learned)
        memory.record(entry)
        if len(memory.learned) > before:
            written.append(entry["id"])
    return written
