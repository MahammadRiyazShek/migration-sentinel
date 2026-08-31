# Submission Packaging Audit Log (deadline-day verification)

Generated on the submission deadline (2026-08-31, before 18:00 UTC) to confirm the
uploaded archive and the form text are internally consistent and reproducible.

## CRITIQUE LAYER - three hidden assumptions checked before packaging
1. ASSUMED the pasted form text == SUBMISSION_FORM_TEXT.txt in the repo.
   FOUND drift: the live submission still said "46/46 claims hold" and "repo is v12".
   RESOLVED: SUBMISSION_FORM_TEXT.txt is authoritative at v13 / "57/57 claims hold".
   ACTION: paste SUBMISSION_FORM_TEXT.txt verbatim into the Description field.
2. ASSUMED check_results.py "57/57" reproduces on a clean extract.
   CONFIRMED: 57/57 claims hold; tests 16/16; docs 9/9; determinism 0 decision diffs.
3. ASSUMED form constraints are met.
   CONFIRMED: form text is 8695 chars (< 10000), ASCII-only, no pipe/table characters.

## VARIATION OPERATOR - two approaches considered
A. Verification-first repackage (chosen). Validate, align form text, deterministic zip.
B. Rewrite description/README for polish (rejected): risk of unverified claims hours
   before the deadline; correctness of every number outranks new prose.

## PERSISTENT MEMORY - verification battery results (this machine, CPython 3.13)
- tools/check_results.py            -> 57/57 claims hold
- tests/test_all.py                 -> 16/16 passing
- tools/check_docs.py               -> 9/9 (all live docs say v13)
- tools/check_determinism.py        -> PASS, 194 files, 0 decision differences
- tools/check_submission_text.py    -> 7/7 (description matches results JSON)
- make verify                       -> PASS
- live run: python3 -m sentinel review --case eval/cases/case_12_release_train.json
                                    -> BLOCK (3 blocker / 5 high)
- tools/check_cross_version.py      -> SKIP on single-interpreter host (expected);
                                       cross-version equality is re-asserted from
                                       results/cross_version.json by check_results.py

## PACKAGE
- File: migration-sentinel-v13-source.zip
- Top-level folder: migration-sentinel/
- Size target: < 50 MB upload cap.
