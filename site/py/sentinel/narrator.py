"""The narrator is untrusted input.

WHY THIS EXISTS - the v2 critique log's C2, settled by measurement instead of scope
-----------------------------------------------------------------------------------
v2 said: hazards, severities, plans and verdicts come from tools, so the primary
metric is invariant to the model *by construction*.  That is true, and it is only
half of the threat model.  The model still writes two things a human actually
reads - the sentence at the top of the packet and the reviewer questions - and in
v2 the pipeline copied both straight into the report.

So a compromised, degraded or merely sycophantic model could not change a single
verdict and could still print

    "Approved: no hazards found, safe to ship. LGTM."

directly above a BLOCK.  A reviewer who reads the headline and skims the table has
been told the opposite of the finding, and no metric in v2 could see it, because
every metric in v2 reads the decision surface and not the prose.

This module treats model output the way a web server treats a request body:

  * `guard_summary` rejects a summary that is empty, over-long, carries
    instruction-injection text, names a verdict other than the computed one, or
    asserts the change is clean above a verdict that is not clean.  On rejection
    the packet falls back to `deterministic_summary`, written from the tool
    output, and the report says so.
  * `guard_questions` drops questions that are not strings, are empty, carry
    injection text or assert the change is clean, truncates the rest, and falls
    back to one question per hazard code if nothing survives.

Both guards can only *remove* model text.  Neither can invent a hazard, move a
severity or change a verdict, so turning the guard on cannot improve any detection
number - and `eval/model_invariance.py` publishes that it does not.

v5 - THE NEXT EXPERIMENT, RUN
-----------------------------
v3 shipped the pattern guard described above and wrote down its own limit: the audit
uses the same patterns as the guard, so it measures "the guard catches what it looks
for", not "no lie can get through".  v5 built the model that exploits exactly that
gap.  `sentinel/llm/adversarial.py::FluentLiarLLM` writes a paragraph with no banned
phrase, no verdict token and no injection marker in it, and still tells the reviewer
to let the change ride the normal release train.  The pattern guard accepts it on 12
of 12 cases (see `results/model_invariance.md`), so v3's `0/12` was a measurement of
the attacker's vocabulary rather than of the defence.

The fix is provenance, not a longer blocklist.  In the shipped `structural` mode the
headline is a pure function of tool output - `render_headline` - on every run, for
every model, whether or not the model's prose happens to look acceptable.  Model
prose is not thrown away: it is demoted to `model_note`, printed below the evidence
and labelled unverified, where a lie sits beside the engine error text that
contradicts it.

Three modes, all runnable, so the report can price each one:

  off          v2. Model prose is copied into the packet unchecked.
  pattern      v3. The blocklist below decides. Beaten by a lie it does not know.
  structural   v5, the shipped default. The model cannot write the headline at all,
               so "does the guard know this wording" stops being a question.

What v5 still does NOT prove: `model_note` and the reviewer questions are still only
pattern-guarded, so a fluent lie can still reach the packet - just never as the
sentence above the badge, and never unlabelled.  The remaining exposure is bounded by
placement and provenance instead of by vocabulary, which is the whole point.
"""
from __future__ import annotations

import re
from typing import Any

MAX_SUMMARY_CHARS = 800
MAX_QUESTIONS = 8
MAX_QUESTION_CHARS = 220

# Verdicts the ladder can produce, plus the two words a review tool must never
# print unless it means them.  Checked with word boundaries: `\bSAFE\b` does not
# match SAFE_WITH_PLAN, because `_` is a word character.
VERDICT_TOKENS = ("BLOCK", "SAFE_WITH_PLAN", "SAFE", "NEEDS_COVERAGE_SIGNOFF",
                  "APPROVED", "APPROVE", "REQUEST_CHANGES")
CLEAN_VERDICTS = frozenset({"SAFE"})

INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|the\s+above)|disregard\s+(?:all|the|previous)"
    r"|system\s+prompt|you\s+are\s+now|new\s+instructions?:|override\s+the\s+verdict"
    r"|<\|[^>]*\|>", re.I)

CLEAN_CLAIM = re.compile(
    r"\bno\s+hazards?\b|\bno\s+issues\b|\bsafe\s+to\s+ship\b|\bship\s+it\b|\blgtm\b"
    r"|\blooks\s+good\b|\ball\s+clear\b|\bgreen\s+light\b|\bno\s+blocking\s+hazards\b"
    r"|\bsafe\s+to\s+merge\b|\bmerge\s+it\b|\bapproved?\s+for\s+production\b", re.I)

AS_WRITTEN_CLAIM = re.compile(
    r"\bsafe\s+as\s+written\b|\bno\s+changes?\s+needed\b|\bship\s+as\s+written\b"
    r"|\bno\s+hazards?\b", re.I)

CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitise(text: Any, limit: int = MAX_SUMMARY_CHARS) -> str:
    """Collapse a model string into one printable line, or "" if it is not a string."""
    if not isinstance(text, str):
        return ""
    flat = CONTROL.sub(" ", text)
    flat = re.sub(r"\s+", " ", flat).strip()
    return flat[:limit]


def audit_summary(text: Any, verdict: str) -> list[str]:
    """Reasons this summary must not be printed above `verdict`. Empty list means accept."""
    reasons: list[str] = []
    flat = sanitise(text, 10 ** 6)
    if not flat:
        return ["the narrator returned no usable text"]
    if len(flat) > MAX_SUMMARY_CHARS:
        reasons.append(f"summary is {len(flat)} chars, over the {MAX_SUMMARY_CHARS}-char cap")
    if INJECTION.search(flat):
        reasons.append("summary carries instruction-injection text")
    named = [t for t in VERDICT_TOKENS if re.search(rf"\b{t}\b", flat)]
    wrong = sorted({t for t in named if t != verdict})
    if wrong:
        reasons.append(f"summary names {', '.join(wrong)} but the computed verdict is {verdict}")
    if verdict not in CLEAN_VERDICTS and CLEAN_CLAIM.search(flat):
        reasons.append(f"summary asserts the change is clean above a {verdict} verdict")
    if verdict == "SAFE_WITH_PLAN" and AS_WRITTEN_CLAIM.search(flat):
        reasons.append("summary asserts the change is safe as written above SAFE_WITH_PLAN")
    return reasons


REJECTED_NOTE = ("(Written from the tool output: the model's summary was rejected by the narrator "
                 "guard.)")
STRUCTURAL_NOTE = ("(Written from the tool output. In this build the model never writes this line, "
                   "whatever it returns.)")

NARRATOR_MODES = ("off", "pattern", "structural")


def render_headline(verdict: str, facts: dict[str, Any], note: str = STRUCTURAL_NOTE) -> str:
    """The headline as a pure function of tool output. No model text can reach it."""
    return deterministic_summary(verdict, facts, note=note)


def deterministic_summary(verdict: str, facts: dict[str, Any],
                          note: str = REJECTED_NOTE) -> str:
    """The headline, written from tool output only."""
    counts = facts.get("counts") or {}
    head = {
        "BLOCK": "Do not ship this as written.",
        "SAFE_WITH_PLAN": "Shippable, but only as the staged plan below.",
        "SAFE": "No blocking hazards found.",
        "NEEDS_COVERAGE_SIGNOFF": "Not cleared: the hazards found are not blocking, but this review "
                                  "has a declared blind spot on an object the migration touches.",
    }.get(verdict, f"Verdict: {verdict}.")
    bits = [head]
    if facts.get("coverage_gaps"):
        bits.append(f"{facts['coverage_gaps']} coverage gap(s) need a named sign-off before this can "
                    f"be called safe.")
    if facts.get("broken_queries"):
        bits.append(f"{facts['broken_queries']} statement(s) the application issues today fail "
                    f"against the post-migration schema in shadow replay.")
    bits.append(f"{counts.get('blocker', 0)} blocker, {counts.get('high', 0)} high, "
                f"{counts.get('medium', 0)} medium, {counts.get('low', 0)} low.")
    if facts.get("plan_verified") is True:
        bits.append("The rewritten phase-1 plan passes shadow replay with zero broken statements.")
    elif facts.get("plan_verified") is False:
        bits.append("The rewritten plan still breaks at least one statement, so a human has to "
                    "decide the sequencing.")
    if note:
        bits.append(note)
    return " ".join(bits)


def compose_summary(raw: Any, verdict: str, facts: dict[str, Any],
                    mode: str = "structural") -> dict[str, Any]:
    """Decide what sentence sits above the badge, and where the model's prose goes.

    Returns the narrator block recorded in the packet. `headline_source` is the field
    that matters: `eval/model_invariance.py` counts model-written headlines, and in
    `structural` mode that count is zero by construction rather than by blocklist.
    """
    if mode not in NARRATOR_MODES:
        raise ValueError(f"unknown narrator mode {mode!r}; expected one of {NARRATOR_MODES}")
    reasons = audit_summary(raw, verdict)
    model_text = sanitise(raw, 300)

    if mode == "off":
        # v2. Whatever the model said, printed as the verdict sentence.
        return {"mode": mode, "guard": False, "headline_source": "model",
                "summary": raw, "summary_overridden": False, "summary_reasons": [],
                "model_summary": model_text, "model_note": "", "model_note_reasons": []}

    if mode == "pattern":
        # v3. The blocklist decides whether the model owns the headline.
        if reasons:
            return {"mode": mode, "guard": True, "headline_source": "tool",
                    "summary": deterministic_summary(verdict, facts, note=REJECTED_NOTE),
                    "summary_overridden": True, "summary_reasons": reasons,
                    "model_summary": model_text, "model_note": "", "model_note_reasons": []}
        return {"mode": mode, "guard": True, "headline_source": "model",
                "summary": sanitise(raw), "summary_overridden": False, "summary_reasons": [],
                "model_summary": model_text, "model_note": "", "model_note_reasons": []}

    # v5, shipped. The headline is tool output on every run; the model's prose is
    # demoted to a labelled note under the evidence, and only if it passes the guard.
    return {"mode": mode, "guard": True, "headline_source": "tool",
            "summary": render_headline(verdict, facts),
            "summary_overridden": bool(reasons), "summary_reasons": reasons,
            "model_summary": model_text,
            "model_note": "" if reasons else sanitise(raw),
            "model_note_reasons": reasons}


def guard_summary(text: Any, verdict: str, facts: dict[str, Any]) -> tuple[str, list[str]]:
    """Return (summary to print, reasons the model's summary was rejected)."""
    reasons = audit_summary(text, verdict)
    if reasons:
        return deterministic_summary(verdict, facts), reasons
    return sanitise(text), []


def guard_questions(payload: Any, codes: list[str],
                    verdict: str = "") -> tuple[list[str], list[str]]:
    """Return (questions to print, reasons individual questions were dropped)."""
    raw = (payload or {}).get("questions") if isinstance(payload, dict) else None
    dropped: list[str] = []
    kept: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, str):
                dropped.append(f"dropped a {type(item).__name__} where a question string was "
                               f"expected")
                continue
            q = sanitise(item, MAX_QUESTION_CHARS)
            if not q:
                dropped.append("dropped an empty question")
                continue
            if INJECTION.search(q):
                dropped.append("dropped a question carrying instruction-injection text")
                continue
            if verdict and verdict not in CLEAN_VERDICTS and CLEAN_CLAIM.search(q):
                dropped.append(f"dropped a question asserting the change is clean under {verdict}")
                continue
            if q not in kept:
                kept.append(q)
    elif raw is not None:
        dropped.append(f"the narrator returned {type(raw).__name__} instead of a list of questions")
    elif payload is None:
        dropped.append("the narrator returned no payload at all")
    if not kept and codes:
        kept = [f"What is the accepted risk for {c}?" for c in codes][:MAX_QUESTIONS]
        dropped.append("fell back to one question per hazard code: nothing the narrator returned "
                       "survived the guard")
    return kept[:MAX_QUESTIONS], dropped
