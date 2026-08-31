# Submission Packaging Audit Log (deadline-day verification)

Regenerated on the submission deadline (2026-08-31, before 18:00 UTC) for the **v16**
archive, from a clean extract of the archive that had already been uploaded to the form.
The previous edition of this file recorded the v15 packaging pass and is superseded; its
numbers (453 authored files, 236 files in the determinism sweep, 9.2 and 10.7 modelled
minutes) are the honest record of that run and are not restated as current anywhere.

Full narrative for the release itself, with the evidence for every decision number below:
`docs/SUPERVISOR_LOG_V16.md`. This file audits the packaging, not the pipeline: no file
under `sentinel/`, `eval/`, `baseline/` or `tools/` was touched in this pass, and no
decision number moved.

## CRITIQUE LAYER - three hidden assumptions checked before re-packaging

1. **ASSUMED** the archive sitting in the submission form passes its own gate, because the
   repository was green when v16 was cut and the numbers had not been touched since.
   **FOUND**, on a clean extract of that archive: `make verify` exits **1**. One check of
   the nine in `tools/check_docs.py` failed - `SUBMISSION_DESCRIPTION.md` and
   `SUBMISSION_FORM_TEXT.txt` disagreed below the paste marker. Root cause, after diffing
   the two copies line by line: a single missing full stop, after "whether this lock
   survives 48M rows", in the markdown copy. One late sentence edit reached the text that
   was pasted into the form and never reached the audited source. Everything numeric was
   green through the failure - 75/75 claims, 139 tests, 7/7 submission-text checks - which
   is exactly why it survived to the deadline: the only red check in the tree was the only
   one whose subject lives outside the repository, and the one command the docs tell a judge
   to run is the command that exits non-zero on it.
   **RESOLVED**: the full stop is restored in `SUBMISSION_DESCRIPTION.md`. The two copies
   are byte-identical at **8,949** characters as authored, 8,993 CRLF-normalised, 7 spare on
   the stricter count that a form POST actually carries. `make verify` now exits **0**.

2. **ASSUMED** this file was current, because it is regenerated every packaging pass.
   **FOUND** it was describing v15: "the v15 archive", 453 authored files, 236 files
   compared for determinism, 9.2 and 10.7 modelled reviewer minutes. Three of those four
   numbers moved in v16 and none of them had been re-read. The file whose entire job is to
   audit the packaging is deliberately outside the `LIVE_DOCS` tuple in
   `tools/check_docs.py`, so that it may quote its own older run without failing the
   staleness check - and that exemption is precisely what let a stale current-state claim
   sit in it unflagged. A checker's exemption list is a blind spot with a comment on it.
   **RESOLVED**: rewritten as the v16 pass, with every number re-read from `results/` or
   printed by the checker that owns it, and the superseded v15 figures named as superseded
   in the first paragraph rather than deleted.

3. **ASSUMED** green checkers mean a valid submission. The qualification gate runs before
   rubric scoring, on four deliverables, and three of them are verifiable from inside the
   tree: solution code and changelog (`README.md`), reproduction guide (`REPRODUCTION.md`),
   agent trajectories (`trajectories/` for the five in-product agents, `agent_traces/` for
   the development sessions). The fourth, the video, is recorded against v2 and its every
   stale number is enumerated in `docs/VIDEO_ADDENDUM.md`.
   **FOUND** two facts about this submission that no code in this repository can check,
   because both live on someone else's website.
   **ACTION REQUIRED BY A HUMAN**: (a) re-upload this corrected archive, so that the
   `make verify` a judge runs is the `make verify` that exits 0; (b) leave the Description
   field alone - it already holds `SUBMISSION_FORM_TEXT.txt` verbatim, and this pass moved
   the repository copy toward the pasted text rather than the other way, specifically so
   that no re-paste is required.

## VARIATION OPERATOR - two approaches considered

**A. Move the audited markdown copy to match the pasted text (chosen).** One character.
The pasted text is already live in a textarea on a website this repository cannot read; the
markdown copy is the one that can still be corrected without a human action. The direction
of a fix should follow which copy is cheaper to change and which copy is load-bearing for
the reader, not which copy the diff happens to name first.

**B. Move the pasted text to match the markdown, then re-paste (rejected).** Equally green,
and it would have required a human to re-paste 8,949 characters into a live form inside the
final hour, under a plain-text field that truncates silently, to deliver a fix whose entire
content is a full stop. Rejected on blast radius: when two edits satisfy the same checker,
prefer the one that does not need a human to become true.

**Also considered and rejected: deleting the byte-identical check.** It fired on its first
live outing on a real drift, in the direction the v9 defect predicted, which is the
strongest possible argument for keeping it. A check that fails at the worst moment is doing
its job at the worst moment.

## PERSISTENT MEMORY - verification battery, after the edit

Run from a clean extract of the packaged tree, CPython 3.12.13, no network, no API key, no
dependencies. Total wall clock under one minute; cost $0.00.

```
make verify                            -> exit 0
python3 tools/check_results.py         -> 75/75 claims hold
python3 -m unittest discover -s tests  -> Ran 139 tests, OK
python3 tools/check_docs.py            -> 9/9 documentation checks, 462 authored files
python3 tools/check_submission_text.py -> 7/7 submission-text checks
python3 tools/check_determinism.py     -> PASS, 238 files, 0 decision differences
python3 tools/check_cross_version.py   -> PASS, CPython 3.11.2 and 3.12.13,
                                          0 decision differences, timings apart
python3 -m sentinel review --case eval/cases/case_12_release_train.json
                                       -> BLOCK, and the CLI refuses to execute phase 1
                                          without --i-approve and a named reviewer
```

Decision numbers, re-asserted after the edit: unsafe approvals **0/12** in sample and
**0/9** held out, hazard recall **0.970** and **0.96**, verified expand/contract plans
**12/12**, modelled reviewer minutes **10.0** and **11.7**, decision surface changed in
**0 of 168** completed hostile reviews. None moved. A packaging release that moved a
decision number would be a packaging release that changed the pipeline.

## PACKAGE

- Top-level folder: `migration-sentinel/`
- Excluded: `__pycache__/`, `.pyc`, editor and OS metadata. Nothing else is excluded, so
  `results/`, `trajectories/`, `agent_traces/` and `site/` ship as generated.
- 527 files, identical in name and count to the uploaded v16 archive: one character of
  `SUBMISSION_DESCRIPTION.md` and this file are the whole diff.
- No credentials, no private data, no network calls anywhere in the tree.
- Well under the 50 MB upload cap.

## HOT TAKE FROM THIS PASS

Every checker in this repository was written after a defect escaped it, and the last defect
to escape did not escape a checker: it escaped the deadline. The red check had been red
since v16 was cut. Nobody ran the one command the documentation tells judges to run against
the artefact that was actually uploaded, as opposed to the working tree it was built from.
Verify the archive, not the repository. They are different objects, and only one of them
gets scored.
