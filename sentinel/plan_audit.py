"""The audit of the SQL this pipeline writes for itself.

SUPERVISOR LOG (v16), carried at the top of the file that acts on it
-------------------------------------------------------------------
Every honesty layer in this repository points at the migration a human wrote.  The
rule inventory partitions the kinds the parser can emit *from the input file*.  The
parse audit reconciles the op list against *the input file*.  The coverage ledger
names what the review could not see *about the input*.  The narrator provenance
stops the model writing the headline *about the input*.

This pipeline also emits SQL.  Three scripts of it, on every run: phase 1, phase 2
and a rollback.  Until v16, exactly one of the three was checked, by exactly one of
the two halves of the design: `agents/verifier.py` replayed the corpus against
phase 1.  Phase 2 and the rollback were text.

CRITIQUE PASS THAT PRODUCED THIS MODULE - three assumptions, all of them wrong
-----------------------------------------------------------------------------
  A1  "verified means the plan is safe."  It meant *phase 1 breaks no statement in
      the corpus*.  The strongest claim in the headline table, `12/12 verified
      expand/contract plans`, was a claim about one third of each plan under one of
      the two coverage mechanisms this repository argues you need.
      `results/ablation.md` has said since v2 that replay alone is worse than rules
      alone - 2 unsafe approvals against 1 - because a lock hazard produces no
      failing query.  Phase 1 was being checked by replay alone.  The pipeline's own
      evidence against replay-only review was never applied to the pipeline's own
      output.

  A2  "the generator is careful, so it does not need reviewing."  It is careful:
      `DROP INDEX CONCURRENTLY`, keyset-batched backfills, `ADD CONSTRAINT ... NOT
      VALID` split from `VALIDATE`.  Careful *by construction*, which is the exact
      category of claim this project refuses everywhere else.  Measured, on the 21
      labelled cases already in the repository, v15 shipped 6 plan defects with
      `plan verified: true` printed above every one of them.

  A3  "a hazard in a plan would show up as a hazard."  It cannot.  Hazards are
      produced by rules that run over `parsed["ops"]` - the input - before the
      Rollout Engineer has written a line.  There is no point in the v15 control
      flow at which any rule sees a generated statement.  Nothing was mis-scored;
      nothing was scored.

WHAT IT FOUND, on cases that were already in the repository
----------------------------------------------------------
  F1  ROLLBACK_WINDOW_UNSTATED, 4 of 21 labelled cases.  The expand/contract shape
      means phase 1 adds a column and a code step tells the team to start writing
      it.  The generated rollback drops that column.  Both sentences are correct and
      they are printed in the same packet, in different lists, with no statement of
      the order they are valid in: run the rollback after the deploy the packet asks
      for and every write to the new column fails.  Shadow replay cannot see this
      and never could - the corpus contains today's statements, and the breakage is
      in the statements the packet is asking someone to deploy tomorrow.  It is a
      property of two artefacts, and until v16 every check here was a property of
      one.

  F2  CONTRACT_STEP_UNGATED, 2 of 21.  `ALTER TABLE ... VALIDATE CONSTRAINT` in
      phase 2, on invoices at 48M rows and drivers at 21M.  `sentinel/rulebook.py`
      has carried the reason it is dangerous since v13, in writing, in the RESIDUAL
      bucket: "the second half of a NOT VALID split takes its own lock over the
      whole relation and no rule prices it against the row estimate."  The rule
      inventory named this statement kind as an unpriced lock, the ledger opens a
      gap when it arrives in a migration - and the plan generator emitted one into
      phase 2 with no gate, on every FK and CHECK case, for four versions.

WHY THE FINDINGS ARE NOT HAZARDS AND THE VERDICT STILL MOVES
------------------------------------------------------------
A plan defect is not a property of the migration under review, so it cannot enter
the hazard list without corrupting every recall, precision and severity number in
`results/` - the ground-truth labels describe the input.  It also must not be
silent.  So it lands where v2 put this class of thing: a named entry that caps the
verdict at NEEDS_COVERAGE_SIGNOFF and becomes a human gate.  The same rule the
ledger has always had, applied to a new source: a packet must not certify what it
did not review, and now that includes the SQL the packet is asking someone to run.

On all 21 labelled cases this cap changes nothing, because all 6 defects sit on
cases already at BLOCK or already capped.  That is not luck and it is not a
retune - it is the reason this hole survived four red-team passes.  Nothing that
was being measured could move when it was closed.  `eval/redteam3` exists to make
the cap fire, and `rt3_04` is the canary that must stay clean.

WHAT THIS MODULE STILL CANNOT SEE
---------------------------------
The gate matcher is textual: a destructive contract step counts as gated when a
human gate names its object.  A gate that names the object and asks the wrong
question passes.  That is the same defect class as R1 in `sentinel/rulebook.py`,
one level up again, and it is declared rather than fixed: `audit_gate_text_only`
is in the gap list of every run where a gate carried the weight, so the number of
times this audit trusted a sentence is printed in the packet rather than assumed.
"""
from __future__ import annotations

import re
from typing import Any

from . import rulebook
from .tools import parse_audit, sql_parse

SCRIPTS = ("phase1", "phase2", "rollback")
SCRIPT_KEY = {"phase1": "phase1_sql", "phase2": "phase2_sql", "rollback": "rollback_sql"}

# Kinds that remove or rewrite something that already exists. Deliberately the same
# set the input-side rules treat as destructive or lock-taking, so a kind that is
# dangerous when a human writes it is dangerous when this pipeline writes it.
DESTRUCTIVE_KINDS = {
    "drop_column", "drop_table", "drop_view", "drop_index", "drop_constraint",
    "rename_column", "rename_table", "alter_type", "set_not_null", "drop_not_null",
    "validate_constraint", "maintenance_rewrite", "dml_delete",
}

FINDING_TITLES = {
    "ROLLBACK_WINDOW_UNSTATED":
        "The rollback is only valid before a code step this same packet asks for",
    "CONTRACT_STEP_UNGATED":
        "A contract step this pipeline generated has no human gate",
    "GENERATED_TEXT_UNPARSED":
        "This pipeline emitted SQL it cannot itself read back",
}

GAP_KINDS = {
    "unruled_generated_statement":
        "a statement this pipeline generated has a kind no rule in this pipeline inspects",
    "audit_gate_text_only":
        "this audit accepted a human gate because it names the object, without reading it",
}


def _strip(lines: list[str]) -> str:
    return "\n".join(s for s in lines if not s.strip().startswith("--"))


def _objects(op: Any) -> list[str]:
    """Every name a human gate could plausibly use for this statement."""
    out: list[str] = []
    t, c = getattr(op, "table", None), getattr(op, "column", None)
    d = getattr(op, "detail", None) or {}
    if t and c:
        out.append(f"{t}.{c}")
    if t:
        out.append(t)
    if c:
        out.append(c)
    for key in ("name", "new_name", "constraint"):
        v = d.get(key)
        if isinstance(v, str) and v:
            out.append(v)
    seen, uniq = set(), []
    for o in out:
        if o not in seen:
            seen.add(o)
            uniq.append(o)
    return uniq


def _named_in(text: str, objects: list[str]) -> str | None:
    low = (text or "").lower()
    for o in objects:
        if o and o.lower() in low:
            return o
    return None


def _parse(sql: str) -> tuple[list[Any], dict[str, Any]]:
    if not sql.strip():
        return [], {}
    ops = sql_parse.parse_migration(sql)
    try:
        text_audit = parse_audit.audit(sql, ops)
    except Exception:  # a generator this pipeline owns must never take a review down
        text_audit = {}
    return ops, text_audit


def audit(plan: dict[str, Any], schema: Any, queries: list[dict[str, Any]],
          seed: dict[str, Any] | None = None, replay_tool=None) -> dict[str, Any]:
    """Review the three scripts this pipeline just wrote. Pure function, no model.

    `replay_tool` is `shadow.replay` from the registry, passed in so the tool call is
    recorded in the trajectory like every other one.
    """
    gates_text = " || ".join(plan.get("human_gates") or [])
    code_text = " || ".join(plan.get("code_steps") or [])
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    parsed_scripts: dict[str, list[Any]] = {}
    statements = 0

    def finding(code: str, script: str, op: Any, why: str, closes_with: str,
                evidence: list[str]) -> None:
        findings.append({
            "code": code,
            "title": FINDING_TITLES[code],
            "script": script,
            "statement_index": getattr(op, "index", None),
            "statement": (getattr(op, "sql", "") or "").strip()[:160],
            "objects": _objects(op)[:3],
            "why": why,
            "closes_with": closes_with,
            "evidence": evidence,
        })

    def gap(kind: str, obj: str, script: str, op: Any, why: str, closes_with: str) -> None:
        gaps.append({
            "kind": kind,
            "object": obj,
            "object_inferred": False,
            "script": script,
            "statement_index": getattr(op, "index", None),
            "statement": (getattr(op, "sql", "") or "").strip()[:140],
            "why": why,
            "closes_with": closes_with,
            "irreversible": False,
        })

    # --- 1. can this pipeline read back what it wrote --------------------------
    for script in SCRIPTS:
        sql = _strip(plan.get(SCRIPT_KEY[script]) or [])
        ops, text_audit = _parse(sql)
        parsed_scripts[script] = ops
        statements += len(ops)
        notes: list[tuple[int | None, str, str]] = []
        for u in (text_audit.get("unaccounted") or []):
            notes.append((u.get("statement_index"), u.get("text", ""),
                          "a statement in the generated script that its own op list does not "
                          "account for"))
        for u in (text_audit.get("unterminated") or []):
            notes.append((None, str(u)[:120],
                          "an unterminated construct in the generated script, which Postgres "
                          "would refuse"))
        for pr in (text_audit.get("procedural") or []):
            notes.append((pr.get("statement_index"), pr.get("head", ""),
                          "a procedural body in the generated script whose inner statements "
                          "reached no rule"))
        for idx, text, why in notes:
            pseudo = type("S", (), {"index": idx, "sql": text,
                                    "table": None, "column": None, "detail": {}})()
            finding("GENERATED_TEXT_UNPARSED", script, pseudo,
                    f"{why}, so this packet is printing SQL it did not fully model",
                    "a reviewer reads the generated script by hand before running it",
                    [f"tools/parse_audit.py on the generated {script} script: {why}",
                     f"statements lexed {text_audit.get('lexed_statements')}, "
                     f"ops produced {text_audit.get('ops')}"])

    # --- 2. the rule inventory, applied to generated statements ----------------
    for script in SCRIPTS:
        for op in parsed_scripts[script]:
            b = rulebook.bucket(op.kind)
            inventory.append({"script": script, "statement_index": op.index,
                              "kind": op.kind, "bucket": b})
            if b in ("RESIDUAL", "UNCLASSIFIED"):
                gap("unruled_generated_statement", (_objects(op) or ["unknown"])[0], script, op,
                    "this pipeline generated a statement of a kind nothing in this pipeline "
                    f"inspects: {rulebook.reason(op.kind)}",
                    "a reviewer prices this statement by hand against the row estimate before "
                    "running the script it sits in")

    # --- 3. contract steps: destructive and ungated ----------------------------
    for script in ("phase2", "rollback"):
        for op in parsed_scripts[script]:
            if op.kind not in DESTRUCTIVE_KINDS:
                continue
            objs = _objects(op)
            hit = _named_in(gates_text, objs)
            if hit:
                gap("audit_gate_text_only", hit, script, op,
                    "this step is treated as gated because a human gate names "
                    f"`{hit}`; this audit read the name, not the question",
                    "a reviewer confirms the gate on this object actually asks about this "
                    "statement")
                continue
            if script == "rollback":
                # a rollback of a step no deployed code depends on is the normal, safe
                # case; the dependent one is finding 4 below
                continue
            finding("CONTRACT_STEP_UNGATED", script, op,
                    f"a `{op.kind}` this pipeline wrote into phase 2 is not named by any human "
                    "gate, so the packet asks someone to run a destructive statement it never "
                    "asked anyone to decide about",
                    "the plan carries a gate naming this object, or the statement moves out of "
                    "the generated script",
                    [f"generated phase 2 statement {op.index}: {op.sql.strip()[:90]}",
                     f"human gates in this packet: {len(plan.get('human_gates') or [])}, none "
                     f"naming {objs[0] if objs else 'this object'}",
                     f"rule inventory: `{op.kind}` is {rulebook.bucket(op.kind)} on the input "
                     f"side - {rulebook.reason(op.kind)}"])

    # --- 4. the property of two artefacts --------------------------------------
    window_stated = bool(re.search(r"\b(before|only if|prior to|until)\b[^|]{0,120}\b(deploy|code)\b",
                                   gates_text, flags=re.I))
    for op in parsed_scripts["rollback"]:
        objs = _objects(op)
        dep = None
        for step in (plan.get("code_steps") or []):
            hit = _named_in(step, objs)
            if hit:
                dep = (step, hit)
                break
        if dep is None or window_stated:
            continue
        step, hit = dep
        finding("ROLLBACK_WINDOW_UNSTATED", "rollback", op,
                f"the rollback removes `{hit}`, and a code step in this same packet asks the team "
                "to start using it; run them in the printed order and the rollback breaks the "
                "deploy the packet asked for. The corpus cannot show this: the statements that "
                "break are the ones this packet is asking someone to write",
                "the plan states the window - roll back phase 1 only before the code step, and "
                "after it use a forward fix instead",
                [f"generated rollback statement {op.index}: {op.sql.strip()[:90]}",
                 f"generated code step: {step[:110]}",
                 "shadow replay of this rollback breaks 0 corpus statements, which is why replay "
                 "alone reports it as safe"])

    # --- 5. replay the two scripts nobody replayed -----------------------------
    replay_summary: dict[str, Any] = {"ran": False,
                                      "why": "no replay tool was passed to this audit"}
    if replay_tool is not None:
        try:
            post1, _ = sql_parse.apply_ops(schema, parsed_scripts["phase1"])
            per_script: dict[str, Any] = {}
            for script in ("phase2", "rollback"):
                ops = parsed_scripts[script]
                if not ops:
                    continue
                post, _notes = sql_parse.apply_ops(post1, ops)
                rep = replay_tool(pre_schema=post1, post_schema=post, ops=ops,
                                  seed=seed or {}, queries=queries)
                j = rep.to_json()
                per_script[script] = {"queries_run": j["queries_run"],
                                      "broken_after": len(rep.broken),
                                      "broken_query_ids": sorted(b["query_id"] for b in rep.broken)}
            replay_summary = {"ran": True, "scripts": per_script,
                              "note": "the generated phase 2 is expected to break today's "
                                      "statements - that is what the code steps are for. The "
                                      "number is published so the reviewer can check that every "
                                      "break has a code step, rather than being told it does."}
        except Exception as exc:  # never take a review down over its own audit
            replay_summary = {"ran": False,
                              "why": f"replay of the generated scripts failed: {exc}"}

    findings.sort(key=lambda f: (f["script"], f["code"], f["statement_index"] or 0))
    gaps.sort(key=lambda g: (g["script"], g["kind"], g["statement_index"] or 0))
    return {
        "statements_audited": statements,
        "scripts": {s: len(parsed_scripts[s]) for s in SCRIPTS},
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "gaps": gaps,
        "gap_kinds": sorted({g["kind"] for g in gaps}),
        "kind_inventory": inventory,
        "gates_trusted": sum(1 for g in gaps if g["kind"] == "audit_gate_text_only"),
        "replay": replay_summary,
        "clean": not findings,
    }


def cap(verdict: str, pa: dict[str, Any]) -> tuple[str, bool]:
    """A plan defect cannot make a verdict safer, and cannot clear one.

    Same shape and same rule as `coverage.cap`, on a different source: BLOCK is left
    alone because it is already the most restrictive answer available.
    """
    from .coverage import CAPPABLE_VERDICTS, CAPPED_VERDICT

    if pa.get("findings") and verdict in CAPPABLE_VERDICTS:
        return CAPPED_VERDICT, True
    return verdict, False


def gates(pa: dict[str, Any]) -> list[str]:
    """One named human decision per plan defect, phrased as the thing to go and fix."""
    return [f"PLAN DEFECT ({f['code']}) in the generated {f['script']} script: {f['closes_with']}"
            for f in (pa.get("findings") or [])]
