#!/usr/bin/env python3
"""Audit the submission form's Description field against the repository.

`tools/check_results.py` audits the numbers. `tools/check_docs.py` audits what the
documentation claims about the repository. Both stop at the repository boundary, and the
eighth supervisor session found what lives on the other side of it:

    the first artefact a judge reads is not in the repository at all.

It is the Description field of the micro1 submission form. That field says "only plain
text", so the verified `SUBMISSION_DESCRIPTION.md` - which leads with a markdown table -
cannot be pasted into it as written. It was flattened by hand, and the flattening silently
dropped load-bearing content that no checker in this repository could see:

  * the verification lede. `python tools/check_results.py -> 27/27 claims hold` was the
    second sentence of the verified text and ended up mid-paragraph, five screens down,
    behind the results it exists to guarantee. Reproducibility is 15% of the rubric and the
    second tie-break;
  * the explicit baseline-and-advanced framing. The challenge requires an entry to present
    both. "Arms: A, B, Sentinel" is not that sentence;
  * the enumeration behind "byte-identical". "Byte-identical throughout" is an assertion;
    "byte-identical on verdict, hazards, severities, evidence, ledger, generated SQL and
    verification" is a list a judge can go and check;
  * the pointer to `trajectories/`. The pasted text cited `agent_traces/` alone, which holds
    the *development* traces. Deliverable 04 is the runtime trajectories of the five
    in-product agents, and those are in `trajectories/`.

None of that moves a metric. All of it is read before any metric is. So the pasted text is
committed verbatim as `SUBMISSION_FORM_TEXT.txt` and audited here, with an exit code, like
everything else in this repository.

Six checks. Standard library only, no network. Run from the repository root:

    python3 tools/check_submission_text.py
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORM_TEXT = ROOT / "SUBMISSION_FORM_TEXT.txt"
FORM_LIMIT = 10000

ARMS = ("baseline_prompt_only", "baseline_prompt_with_schema", "agent_pipeline")


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 1. fits the form

def check_fits_the_form(text):
    if len(text) > FORM_LIMIT:
        return [f"{len(text)} characters, over the form's {FORM_LIMIT} limit by "
                f"{len(text) - FORM_LIMIT}"]
    print(f"        {len(text)} of {FORM_LIMIT} characters, {FORM_LIMIT - len(text)} spare")
    return []


# ------------------------------------------------- 2. is actually plain text, and ASCII

# The form field is plain text. Markdown pasted into it renders as literal punctuation, and
# a smart quote or an en dash pasted into it is the same defect v7 found inside the repo:
# text a judge reads that nobody checked.
MARKDOWN = {
    "a markdown table row": re.compile(r"^\s*\|.*\|\s*$", re.M),
    "bold or italic asterisks": re.compile(r"\*\*|(?<!\*)\*[A-Za-z]"),
    "a backtick code span": re.compile(r"`"),
    "a markdown link": re.compile(r"\[[^\]]*\]\([^)]*\)"),
    "a markdown heading": re.compile(r"^\s*#{1,6}\s", re.M),
}


def check_is_plain_text(text):
    bad = []
    for label, pattern in MARKDOWN.items():
        m = pattern.search(text)
        if m:
            line = text[: m.start()].count("\n") + 1
            bad.append(f"line {line}: contains {label} - the form field renders it literally")
    non_ascii = sorted({c for c in text if ord(c) > 127})
    if non_ascii:
        bad.append("non-ASCII characters a plain-text field may mangle: "
                   + ", ".join(f"{c!r} (U+{ord(c):04X})" for c in non_ascii))
    if not bad:
        print("        no markdown, no smart punctuation, 7-bit ASCII throughout")
    return bad


# --------------------------------------- 3. the headline table survived being flattened

def _agg(ev, arm):
    return ev["arms"][arm]["aggregate"]


HEADLINE = [
    ("Unsafe approvals (primary)",
     lambda a: f"{a['unsafe_approvals']}/{a['cases']}"),
    ("Blind-spot cases cleared (primary)",
     lambda a: f"{a['gap_cases_cleared_without_signoff']}/{a['cases_with_coverage_gaps']}"),
    ("Blind spots named, with the object",
     lambda a: str(a["declared_coverage_gaps"])),
    ("Hazard recall / precision",
     lambda a: f"{a['strict']['recall']:.3f}/{a['strict']['precision']:.3f}"),
    ("Severity agreement on matched hazards",
     lambda a: f"{a['severity_agreement']:.3f}"),
    ("Findings backed by machine evidence",
     lambda a: f"{a['findings_with_evidence']}/{a['findings_total']}"),
    ("Verified expand/contract plans",
     lambda a: f"{a['verified_plans']}/{a['cases']}"),
    ("False alarms on the one clean migration",
     lambda a: str(a["false_alarms_on_clean_cases"])),
    ("Modelled reviewer minutes per case",
     lambda a: f"{a['modelled_reviewer_minutes_per_case']:g}"),
]


def _norm(s):
    """0.970 and 0.97 are the same claim; 1 and 1/12 are not."""
    out = []
    for part in re.split(r"[\s,]+", s.strip()):
        part = part.strip(".")          # a row ends a sentence; the full stop is not a digit
        if not part:
            continue
        out.append("/".join(f"{float(x):g}" if re.fullmatch(r"-?\d+(\.\d+)?", x) else x
                            for x in part.split("/")))
    return out


def check_headline_figures(text):
    ev = _load("results/evaluation.json")
    bad, checked = [], 0
    for label, reader in HEADLINE:
        m = re.search(re.escape(label) + r"\s*:\s*(.+)", text)
        if not m:
            bad.append(f"the pasted text no longer states {label!r}")
            continue
        got = _norm(m.group(1))
        want = _norm(", ".join(reader(_agg(ev, arm)) for arm in ARMS))
        if got != want:
            bad.append(f"{label}: form says {', '.join(got)}; "
                       f"results/evaluation.json says {', '.join(want)}")
        else:
            checked += 1
    if not bad:
        print(f"        {checked} headline rows match results/evaluation.json arm for arm")
    return bad


# ---------------------------------------------- 4. the ablation figures still match

ABLATION = {
    "All five components": "full",
    "Rules only": "no_replay",
    "Replay only": "no_static",
    "No coverage gate": "no_coverage",
}


def check_ablation_figures(text):
    ab = _load("results/ablation.json")
    bad = []
    for label, arm in ABLATION.items():
        m = re.search(re.escape(label) + r"\s*:\s*([0-9/., ]+)", text)
        if not m:
            bad.append(f"the pasted text no longer states the {label!r} ablation row")
            continue
        a = ab[arm]["aggregate"]
        want = _norm(f"{a['unsafe_approvals']}/{a['cases']}, {a['strict']['recall']:.3f}, "
                     f"{a['verified_plans']}/{a['cases']}, "
                     f"{a['gap_cases_cleared_without_signoff']}/"
                     f"{a['cases_with_coverage_gaps']}, "
                     f"{a['modelled_reviewer_minutes_per_case']:g}")
        got = _norm(m.group(1))
        if got != want:
            bad.append(f"{label}: form says {', '.join(got)}; "
                       f"results/ablation.json says {', '.join(want)}")
    total = (len(ARMS) + len(ab)) * ab["full"]["aggregate"]["cases"]
    if f"= {total} reviews" not in text:
        bad.append(f"the review-count arithmetic no longer reads '= {total} reviews' "
                   f"({len(ARMS)} headline + {len(ab)} ablation arms x "
                   f"{ab['full']['aggregate']['cases']} cases)")
    if not bad:
        print(f"        {len(ABLATION)} ablation rows and the {total}-review arithmetic "
              f"match results/ablation.json")
    return bad


# ------------------------------------- 5. the hostile-model figures still match

def check_invariance_figures(text):
    mi = _load("results/model_invariance.json")
    cases, providers, modes = mi["cases"], len(mi["providers"]), len(mi["modes"])
    total = cases * providers * modes
    bad = []
    if f"{cases} cases x {providers} models x {modes} narrator modes = {total} reviews" \
            not in text:
        bad.append(f"the invariance arithmetic no longer reads '{cases} cases x {providers} "
                   f"models x {modes} narrator modes = {total} reviews'")
    rows = mi["rows"]
    completed = sum(r["cases"] - r["crashed"] for r in rows)
    changed = sum(r["decision_surface_changed"] for r in rows)
    if f"changed in {changed} of {completed} completed reviews" not in text:
        bad.append(f"the decision-surface claim no longer reads 'changed in {changed} of "
                   f"{completed} completed reviews'")
    crashed = total - completed
    if f"The other {crashed} crashed" not in text:
        bad.append(f"the crash disclosure no longer reads 'The other {crashed} crashed' - "
                   "the incomplete runs are part of the claim, not a footnote")
    def _hostile(mode, field):
        return sum(r[field] for r in rows if r["mode"] == mode and r["provider"] != "scripted")

    per_mode = {m: _hostile(m, "cases") for m in mi["modes"]}
    if len(set(per_mode.values())) != 1:
        bad.append("the three narrator modes no longer see the same hostile review count, "
                   f"so the progression is not a comparison: {per_mode}")
    else:
        n = next(iter(per_mode.values()))
        want = (f"per {n} hostile reviews per mode: "
                f"{_hostile('off', 'misleading_headlines_printed')}/{n} unguarded, "
                f"{_hostile('pattern', 'misleading_headlines_printed')}/{n} blocklist, "
                f"{_hostile('structural', 'misleading_headlines_printed')}/{n} shipped")
        if want not in text:
            bad.append(f"the provenance progression no longer reads '{want}'")

    shipped = [r for r in rows if r["mode"] == mi["shipped_mode"]]
    authored = sum(r["model_written_headlines"] for r in shipped)
    of = sum(r["cases"] for r in shipped)
    if f"{authored} of {of} headlines model-written" not in text:
        bad.append(f"the headline-provenance claim no longer reads "
                   f"'{authored} of {of} headlines model-written'")

    if not bad:
        print(f"        invariance arithmetic, {changed}/{completed} decision surface, the "
              f"{crashed} declared crashes, the provenance progression and "
              f"{authored}/{of} model-written headlines all match "
              f"results/model_invariance.json")
    return bad


# ------------------------------- 6. the claims the flattening is most likely to drop

REQUIRED_CLAIMS = [
    ("the verification lede, in the first 1200 characters",
     re.compile(r"python tools/check_results\.py\s*->\s*27/27 claims hold"), 1200,
     "reproducibility is 15% and the second tie-break; the one command that proves every "
     "number has to be read before the numbers, not after them"),
    ("the explicit baseline-and-advanced framing",
     re.compile(r"the simple baseline.*the stronger baseline.*the advanced solution",
                re.S | re.I), None,
     "the challenge requires an entry to present both a baseline and an advanced solution; "
     "a bare list of arm names is not that sentence"),
    ("what byte-identical is over",
     re.compile(r"byte-identical on verdict, hazards, severities, evidence, ledger, "
                r"generated SQL and verification"), None,
     "an enumerated invariance claim is checkable; 'byte-identical throughout' is not"),
    ("the pointer to the in-product agent trajectories",
     re.compile(r"trajectories/"), None,
     "deliverable 04 is the runtime trajectories of the five in-product agents; "
     "agent_traces/ holds the development sessions and is a different artefact"),
    ("the video-versus-repo authority notice",
     re.compile(r"video and the repo disagree, results/comparison\.md and "
                r"results/model_invariance\.md are authoritative"), None,
     "the submitted video is older than the repository; the judge has to be told which "
     "artefact wins before either can mislead them"),
    ("the never-delegated list",
     re.compile(r"Never delegated: ground truth, hazard vocabulary, scorer, metrics"), None,
     "an agent that wrote the exam as well as the solution has self-graded every metric "
     "in the submission"),
    ("the denominator warning",
     re.compile(r"Do not quote the F1 without its denominator"), None,
     "twelve hand-labelled cases on one schema; the honest reading of 0.970 is part of "
     "the claim"),
]


def check_load_bearing_claims(text):
    bad = []
    for label, pattern, window, why in REQUIRED_CLAIMS:
        m = pattern.search(text)
        if not m:
            bad.append(f"missing {label} - {why}")
        elif window is not None and m.start() >= window:
            bad.append(f"{label} appears at character {m.start()}, past {window} - {why}")
    if not bad:
        print(f"        all {len(REQUIRED_CLAIMS)} load-bearing sentences survived the "
              f"flattening, in position")
    return bad


CHECKS = [
    ("the pasted description fits the form's plain-text field", check_fits_the_form),
    ("it is plain text: no markdown, no smart punctuation", check_is_plain_text),
    ("every headline figure matches results/evaluation.json", check_headline_figures),
    ("every ablation figure matches results/ablation.json", check_ablation_figures),
    ("every hostile-model figure matches results/model_invariance.json",
     check_invariance_figures),
    ("no load-bearing claim was lost in flattening", check_load_bearing_claims),
]


def main():
    if not FORM_TEXT.exists():
        print(f"FAIL  {FORM_TEXT.name} is absent, so the text actually submitted to the form "
              f"is not auditable")
        return 1
    text = FORM_TEXT.read_text(encoding="utf-8").strip()
    failed = 0
    for label, fn in CHECKS:
        problems = fn(text)
        if problems:
            failed += 1
            print(f"FAIL  {label}")
            for p in problems:
                print(f"        {p}")
        else:
            print(f"PASS  {label}")

    # The claim count is produced by another tool. Ask it rather than restating it.
    out = subprocess.run([sys.executable, str(ROOT / "tools/check_results.py")],
                         capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        print("FAIL  tools/check_results.py does not pass, so the lede above is false")
        failed += 1

    print()
    if failed:
        print(f"{len(CHECKS) - failed}/{len(CHECKS)} submission-text checks hold - "
              f"{failed} failed")
        return 1
    print(f"{len(CHECKS)}/{len(CHECKS)} submission-text checks hold: the description in the "
          f"form is the description this repository can back")
    return 0


if __name__ == "__main__":
    sys.exit(main())
