"""Scoring for the baseline/agent comparison.

Primary metric: **unsafe approvals** - reviews that let a change through when the
ground truth says it breaks something. That is the number an on-call engineer
cares about, so it is the number this project optimises.

Secondary metrics: hazard recall and precision over the shared vocabulary, both
strict (exact code) and lenient (hazard family, so naming the right failure with
the wrong label is not counted as a miss), severity agreement, and whether the
review produced a plan that was actually verified.

Human-time and cost figures are clearly separated into measured (wall clock,
tokens) and modelled (reviewer minutes, from stated assumptions).
"""
from __future__ import annotations

from typing import Any

FAMILIES = {
    "BREAKING_QUERY": "consumer_breakage",
    "VIEW_BREAKAGE": "consumer_breakage",
    "SELECT_STAR_DRIFT": "consumer_breakage",
    "UNIQUE_VIOLATION_EXISTING_DATA": "data_integrity",
    "TYPE_NARROWING_DATA_LOSS": "data_integrity",
    "INTEGRITY_CONSTRAINT_REMOVED": "data_integrity",
    "NOT_NULL_NO_DEFAULT": "data_integrity",
    "INDEX_LOCK_NO_CONCURRENT": "operational_lock",
    "CONSTRAINT_VALIDATION_LOCK": "operational_lock",
    "TABLE_REWRITE_LOCK": "operational_lock",
    "UNBATCHED_BACKFILL": "operational_lock",
    "DESTRUCTIVE_NO_EXPAND_CONTRACT": "process",
    "MISSING_ROLLBACK": "process",
    "CROSS_SERVICE_UNCOORDINATED": "process",
}

# Reviewer-minute model. These are assumptions, not measurements. They are stated
# here so anyone can disagree with them by editing one dict.
TIME_MODEL = {
    "read_review_minutes": 5,
    "verify_unevidenced_claim_minutes": 4,   # grep the corpus, check the DDL, check row counts
    "write_expand_contract_plan_minutes": 20,
    "decide_human_gate_minutes": 3,
}

APPROVE_VERDICTS = {"APPROVE", "SAFE"}

# Verdicts that read as "you may proceed on what is written here". A packet that
# declares a blind spot on an affected object and still lands in this set is the
# v1 failure mode: the badge contradicts the appendix, and reviewers read badges.
CLEAN_VERDICTS = {"APPROVE", "SAFE", "SAFE_WITH_PLAN"}


def codes(hazards: list[dict[str, Any]]) -> set[str]:
    return {h["code"] for h in hazards}


def families(hazard_codes: set[str]) -> set[str]:
    return {FAMILIES.get(c, c) for c in hazard_codes}


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def score_case(case: dict[str, Any], result: dict[str, Any],
               case_coverage_gaps: int = 0) -> dict[str, Any]:
    """`case_coverage_gaps` is a property of the case, computed once from the migration and
    the corpus, so every arm is measured against the same factual blind spots rather than
    against its own opinion of them."""
    gt = case["ground_truth"]
    gt_codes = codes(gt["hazards"])
    pred_codes = codes(result["hazards"])
    tp = sorted(gt_codes & pred_codes)
    fp = sorted(pred_codes - gt_codes)
    fn = sorted(gt_codes - pred_codes)

    gt_fam, pred_fam = families(gt_codes), families(pred_codes)
    sev_gt = {h["code"]: h["severity"] for h in gt["hazards"]}
    sev_pred: dict[str, str] = {}
    for h in result["hazards"]:  # keep the highest severity the reviewer gave a code
        order = ["low", "medium", "high", "blocker"]
        if h["code"] not in sev_pred or order.index(h["severity"]) > order.index(sev_pred[h["code"]]):
            sev_pred[h["code"]] = h["severity"]
    sev_matches = [c for c in tp if sev_gt.get(c) == sev_pred.get(c)]

    approved = result["verdict"] in APPROVE_VERDICTS
    unsafe_approval = bool(approved and gt["blocking"])
    false_alarm = bool(not gt["blocking"] and not gt_codes and pred_codes)

    evidenced = sum(1 for h in result["hazards"] if h.get("evidence"))
    unevidenced = len(result["hazards"]) - evidenced
    gates = len((result.get("plan") or {}).get("human_gates", []) or [])
    plan_verified = bool(result.get("plan_verified"))

    minutes = TIME_MODEL["read_review_minutes"]
    minutes += unevidenced * TIME_MODEL["verify_unevidenced_claim_minutes"]
    if plan_verified:
        minutes += gates * TIME_MODEL["decide_human_gate_minutes"]
    elif gt["blocking"] or pred_codes:
        minutes += TIME_MODEL["write_expand_contract_plan_minutes"]

    declared_gaps = len((result.get("coverage_ledger") or {}).get("gaps", []))
    cleared_a_gap = bool(case_coverage_gaps and result["verdict"] in CLEAN_VERDICTS)

    return {
        "case_id": case["id"], "verdict": result["verdict"],
        "case_coverage_gaps": case_coverage_gaps,
        "declared_coverage_gaps": declared_gaps,
        "coverage_signoff_required": result["verdict"] == "NEEDS_COVERAGE_SIGNOFF",
        "gap_case_cleared_without_signoff": cleared_a_gap,
        "gt_blocking": gt["blocking"], "gt_codes": sorted(gt_codes), "pred_codes": sorted(pred_codes),
        "tp": tp, "fp": fp, "fn": fn,
        "fam_tp": sorted(gt_fam & pred_fam), "fam_fp": sorted(pred_fam - gt_fam),
        "fam_fn": sorted(gt_fam - pred_fam),
        "severity_matches": sev_matches,
        "unsafe_approval": unsafe_approval, "false_alarm_on_clean_case": false_alarm,
        "findings": len(result["hazards"]), "evidenced_findings": evidenced,
        "plan_verified": plan_verified, "human_gates": gates,
        "modelled_reviewer_minutes": minutes,
        "wall_ms": result.get("wall_ms", 0),
        "tokens": (result.get("model_usage", {}).get("tokens_in", 0)
                   + result.get("model_usage", {}).get("tokens_out", 0)),
        "cost_usd": result.get("model_usage", {}).get("cost_usd", 0.0),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(len(r["tp"]) for r in rows)
    fp = sum(len(r["fp"]) for r in rows)
    fn = sum(len(r["fn"]) for r in rows)
    ftp = sum(len(r["fam_tp"]) for r in rows)
    ffp = sum(len(r["fam_fp"]) for r in rows)
    ffn = sum(len(r["fam_fn"]) for r in rows)
    matched = sum(len(r["tp"]) for r in rows)
    sev = sum(len(r["severity_matches"]) for r in rows)
    return {
        "cases": len(rows),
        "unsafe_approvals": sum(r["unsafe_approval"] for r in rows),
        "false_alarms_on_clean_cases": sum(r["false_alarm_on_clean_case"] for r in rows),
        "strict": {**prf(tp, fp, fn), "tp": tp, "fp": fp, "fn": fn},
        "lenient_family": {**prf(ftp, ffp, ffn), "tp": ftp, "fp": ffp, "fn": ffn},
        "severity_agreement": round(sev / matched, 3) if matched else 0.0,
        "findings_total": sum(r["findings"] for r in rows),
        "findings_with_evidence": sum(r["evidenced_findings"] for r in rows),
        "verified_plans": sum(r["plan_verified"] for r in rows),
        "cases_with_coverage_gaps": sum(1 for r in rows if r.get("case_coverage_gaps")),
        "declared_coverage_gaps": sum(r.get("declared_coverage_gaps", 0) for r in rows),
        "gap_cases_cleared_without_signoff": sum(
            bool(r.get("gap_case_cleared_without_signoff")) for r in rows),
        "modelled_reviewer_minutes_total": sum(r["modelled_reviewer_minutes"] for r in rows),
        "modelled_reviewer_minutes_per_case": round(
            sum(r["modelled_reviewer_minutes"] for r in rows) / len(rows), 1),
        "wall_ms_per_case": round(sum(r["wall_ms"] for r in rows) / len(rows), 1),
        "tokens_total": sum(r["tokens"] for r in rows),
        "cost_usd_total": round(sum(r["cost_usd"] for r in rows), 6),
    }
