# Submission Packaging Audit Log (deadline-day verification)

Regenerated on the submission deadline (2026-08-31, before 18:00 UTC) for the **v15**
archive. The previous edition of this file recorded the v13 packaging pass and is
superseded; its numbers (57 claims, 16 tests, v13) are the honest record of that run and
are not restated as current anywhere.

Full narrative, with the evidence for every line below: `docs/SUPERVISOR_LOG_V15.md`.

## CRITIQUE LAYER - three hidden assumptions checked before packaging

1. **ASSUMED** the packaged tree passes its own gate, because the repository was green when
   the last release was cut.
   **FOUND**, on a clean extract: `make verify` exits **1**. Two failures in
   `tests/test_all.py::TestSubmissionText`. `SUBMISSION_DESCRIPTION.md` had been
   overwritten with the flattened paste text, deleting the `<!-- PASTE BELOW THIS LINE -->`
   marker, and `SUBMISSION_FORM_TEXT.txt` was 9,229 characters against a 9,000-character
   budget (9,275 CRLF-normalised, which is what a form POST carries).
   **RESOLVED**: description rebuilt around the marker; form text trimmed to 8,903
   characters (8,948 CRLF-normalised, 52 spare) with no figure and no load-bearing sentence
   touched. `make verify` now exits **0**.

2. **ASSUMED** the text pasted into the live form is `SUBMISSION_FORM_TEXT.txt`.
   **FOUND** drift, for the second release running: the live field held a third,
   hand-trimmed variant of 7,550 characters that fails **3 of 7** submission-text checks -
   the `= 132 reviews` ablation arithmetic and the `All five components` row, the
   `The other 12 crashed` disclosure, the 36/48 -> 13/48 -> 0/48 provenance progression,
   and the video-versus-repo authority notice. Every omission is a disclosure that costs
   the submission something.
   **ACTION REQUIRED BY A HUMAN**: paste `SUBMISSION_FORM_TEXT.txt` verbatim into the
   Description field. No check inside a repository can verify a textarea on someone else's
   website; this one is unfixable in code by construction.

3. **ASSUMED** the enforced character cap is what the form says.
   **FOUND** it is no longer a quotation: v9 read "9000 characters only" off the field, and
   the field now reads "under 10000 characters only. only plain text. no tables or other
   characters allowed."
   **RESOLVED**: value unchanged at 9,000, the stricter of the two readings, and now
   documented as a budget held deliberately rather than as a measurement - in
   `tools/check_submission_text.py`, `tools/check_docs.py` and `tests/test_all.py`.

## VARIATION OPERATOR - two approaches considered

**A. Verify first, then cut prose (chosen).** Fix the marker, trim the description below
budget, correct the cap's provenance, touch nothing under `sentinel/`, re-assert every
number after the edits rather than before them.

**B. Raise `FORM_LIMIT` to 10,000 and keep the longer text (rejected).** One line, both
tests green, defensible on the current label. Rejected because editing the constant a test
asserts, in the pass in which that test fails, turns a failing audit into a passing one
without touching the artefact the audit is about. Recorded in the README changelog as a
rejected variation rather than quietly dropped.

## PERSISTENT MEMORY - verification battery, after the edits

Run from a clean extract of the packaged tree, CPython 3.12.13, no network, no API key:

```
make verify                          -> exit 0
python3 tools/check_results.py       -> 67/67 claims hold
python3 -m unittest discover -s tests-> Ran 129 tests, OK
python3 tools/check_docs.py          -> 9/9 documentation checks, 453 authored files
python3 tools/check_submission_text.py -> 7/7 submission-text checks
python3 tools/check_determinism.py   -> PASS, 236 files, 0 decision differences
python3 tools/check_cross_version.py -> PASS, CPython 3.11.2 and 3.12.13, 0 decision differences
python3 -m sentinel review --case eval/cases/case_12_release_train.json
                                     -> BLOCK, and the CLI refuses to execute phase 1
                                        without --i-approve and a named reviewer
```

Decision numbers, re-asserted after the edits: unsafe approvals **0/12** in sample and
**0/9** held out, hazard recall **0.970** and **0.96**, verified plans **12/12**, modelled
reviewer minutes **9.2** and **10.7**, decision surface changed in **0 of 168** completed
hostile reviews. None moved. A packaging release that moved a decision number would be a
packaging release that changed the pipeline.

## PACKAGE

- Top-level folder: `migration-sentinel/`
- Excluded: `__pycache__/`, `.pyc`, editor and OS metadata. Nothing else is excluded, so
  `results/`, `trajectories/`, `agent_traces/` and `site/` ship as generated.
- No credentials, no private data, no network calls anywhere in the tree.
- Well under the 50 MB upload cap.
