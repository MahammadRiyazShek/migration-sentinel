# Supervisor log v10: the session that read the form field

An external-supervisor pass over the finished v9 submission. Same protocol as v3-v9: act as the
critic, name the hidden assumptions, generate rival designs, pick one, run it, publish what falls
out - including the parts that make the submission look worse.

The one-line result: **the description this repository verified was 9,536 characters against a
9,000-character field, so the artefact a judge reads first was truncated somewhere inside the hot
take, and every gate upstream of it was green.** v8 found that class of defect on the way out of the
repository. v9 found the cap was 9,000 and not 10,000. v10 found that neither session ever measured
the shipped text against the number they had just corrected.

## 1. Critique layer: three hidden assumptions in v9

**A1. "The submission text is audited, so it is submittable."** `tools/check_submission_text.py`
asserted a 9,000-character cap and the committed text was 9,536. The audit ran, printed `FAIL`, and
nothing depended on the exit code that a human would see before submitting: `make verify` was not the
path anyone actually used, and the one test that guarded the checker asserted `6/6` while the checker
ran seven checks - so a genuinely failing audit and a stale expectation cancelled each other out into
a test suite that read `FAILED (failures=1)` and got scrolled past. A red check nobody reads is worth
exactly what a missing check is worth.

**A2. "A character count is a character count."** The field's counter is JavaScript over a string
with `\n` line breaks. A form POST normalises textarea line breaks to CRLF. This text has 50 line
breaks, so there were two answers to "how long is it" that differ by 50 characters, and the previous
release would have passed at 8,958 while the POST body carried 9,008. The cap was read off the form;
the *unit* never was.

**A3. "There is one copy of the description."** v9 asserted exactly that, and enforced it between
`SUBMISSION_DESCRIPTION.md` and `SUBMISSION_FORM_TEXT.txt`. Meanwhile `docs/SUBMISSION.md` - a
current-state document, listed as one in `tools/check_docs.py` - carried a *third* copy: a v5-era
description, 9,753 characters, under a "10,000 limit" note, with a different title, no held-out
section, and the sentence "Twelve cases, one schema, ground truth I wrote" that the freight schema had
made false two sessions earlier. Two copies were pinned to each other and the third was pinned to
nothing.

## 2. Variation operator: two rival designs

**V1, generate the description instead of auditing it.** Render `SUBMISSION_FORM_TEXT.txt` from
`results/*.json` and a template, so a stale figure is unrepresentable and the length is a build
constraint rather than a check. Rejected, and it is the design I would pick with another day: the
description's value is in the judgement about what to say, and a renderer would have produced a
fluent, on-cap, unreadable table of numbers. The failure being fixed is *truncation*, not drift - the
figures were already correct, because v8 and v9 already audit them.

**V2, make the transform the checked artefact.** Keep the hand-written text and assert every property
the form imposes on it, in the unit the form uses: both character counts, plain ASCII, no markdown,
and a list of load-bearing sentences that must survive. Chosen, because it extends the mechanism this
repository already trusts - `check_submission_text.py` had six of those properties and was missing the
only one that had already gone wrong.

The second variation is the one that generalises: the defect was never in what the text said. It was
in the boundary between the text and the field, and the boundary is what nobody owns.

## 3. Persistent memory: what carried into this session

1. **v8's lesson, re-applied one layer out.** Every lossy transform on the way to a human needs a
   statement of what has to survive it. v8 wrote that statement for *content*. It never wrote one for
   *length*, and length is the transform the form applies without asking.
2. **v9's lesson, turned back on v9.** A number read off the form (9,000) is only worth what the
   measurement against it is worth. v9 corrected the cap in two files and left the text over it.
3. **v5's lesson, still the sharpest.** A defence audited in its own vocabulary reports on the
   attacker's imagination. The test that guarded the description asserted `6/6` and a 10,000-character
   cap: it was auditing the checker's *past*, so the checker's present could fail in silence.

## 4. Execution: what changed

| # | change | file | why |
|---|---|---|---|
| 1 | description cut from 9,536 to 8,897 characters, every audited figure and all nine load-bearing sentences intact | `SUBMISSION_FORM_TEXT.txt`, `SUBMISSION_DESCRIPTION.md` | it now fits the field on both counts, with the failure mode and the hot take inside the cap instead of past it |
| 2 | the length check measures twice: as authored, and CRLF-normalised | `tools/check_submission_text.py` | a description whose fate depends on where it is counted is not a description that fits |
| 3 | the test stopped defending stale numbers: 10,000 -> 9,000 plus the CRLF count, and the hardcoded `6/6` became the checker's own arithmetic | `tests/test_all.py` | the guard was asserting a release that no longer existed, which is how a failing audit stayed invisible |
| 4 | `docs/SUBMISSION.md` no longer carries a description; it points at the single audited copy and keeps the submission mechanics | `docs/SUBMISSION.md` | a third copy, contradicting the other two, in a document `check_docs.py` calls current-state |
| 5 | "the repository is v5" and "33 tests, 27 claims" corrected to the current tree, and the held-out world added to the video correction table | `JUDGE_START_HERE.md`, `docs/VIDEO_ADDENDUM.md` | the video addendum's job is to be the authority on what moved; it was two sessions stale |

## 5. Self-review: three mistakes in the first version of this fix

**M1. The first cut fitted the counter, not the POST.** 8,958 characters as authored, 9,008 CRLF. The
fix that was supposed to close the truncation defect reintroduced it in the other unit. Caught by
writing the second count into the check *before* trusting the first one, which is the only reason it
was caught at all: the text passed every check at 8,958.

**M2. The first pass trimmed content the audit could not see the loss of.** Compressing prose is safe
where the checker holds a required sentence and unsafe everywhere else - the first draft had dropped
"An agent that grades its own work has graded itself" and the fixture-versus-corpus sentence in the
same pass, and only one of those is redundant with the hot take. The rule applied: cut connective
tissue and duplication, never a claim that appears exactly once.

**M3. The first version left `docs/SUBMISSION.md` alone** because it is "just docs". It is in
`LIVE_DOCS`, it is linked from the judge entry point, and it contained a description that contradicted
the submitted one on the title, the case count and the cap. Fixing two copies and leaving a third is
the same defect this session opened with.

## 6. What did not move

Every decision number. Unsafe approvals 0/12 in sample and 0/9 held out, strict recall and precision
0.970, severity agreement 0.969, plans 12/12, gap cases cleared 0/2, evidenced findings 35/35, 9.2
modelled minutes per case, 0 of 168 completed reviews changing the decision surface, 0 of 60 headlines
model-written. Nothing under `sentinel/`, `eval/cases/`, `eval/holdout/`, `eval/scoring.py` or
`memory/` was touched, and `tools/check_results.py` is unchanged, so **44/44 means in v10 what it
meant in v9.** The counts that moved are counts of audits: the submission-text checker went from six
properties to seven, and the tests it is pinned by stopped asserting a cap the form does not have.

**The lesson.** v7: a repository that audits only its measurements is audited only where it already
knows how to be wrong. v8: every lossy transform on the way to your user needs a statement of what has
to survive it. v10: **a check whose failure nobody is required to read is a comment, and a test that
asserts your last release will hide your current one.** The last edit before a human reads your work
is not made by your pipeline, and it is measured in a unit your pipeline has never seen.

## 7. Verify from a clean clone

```bash
python -m unittest discover -s tests     # 52 tests
python tools/check_results.py            # 44/44 claims hold
python tools/check_docs.py               # 6 documentation checks
python tools/check_submission_text.py    # 7 checks on the description in the form
```
