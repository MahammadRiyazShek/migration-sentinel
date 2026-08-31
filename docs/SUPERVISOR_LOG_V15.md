# Supervisor log, v15: the last edit was never verified

Fourteen releases of this repository are about the distance between a claim and its
evidence. This one is about a shorter distance: between the last edit and the last run.

The brief for this pass was deliberately unglamorous. Not *is the pipeline right* - four
audit tools and 129 tests answer that with an exit code - but **does the archive a judge
downloads still pass the command its own front page tells them to run?**

It did not. `make verify` exited 1 with two test failures, on a tree in which all 67
published claims still held.

## PERSISTENT MEMORY: the log this pass was executed against

Written before the fixes and kept in the order it was produced, because the findings are
the reason the fixes are the shape they are.

| # | Finding | Evidence | Severity |
| --- | --- | --- | --- |
| F1 | `make verify` exits 1 on the packaged tree. Two tests fail. | `tests/test_all.py`, class `TestSubmissionText`, both cases | fatal to the qualification gate |
| F2 | `SUBMISSION_DESCRIPTION.md` had been overwritten with the flattened paste text, deleting the paste marker. | `tools/check_docs.py`: "has no marker, so its length is not auditable" | high |
| F3 | `SUBMISSION_FORM_TEXT.txt` had grown to 9,229 characters: 229 over the enforced budget as authored, 273 over once the browser normalises 46 line breaks to CRLF. | `tools/check_submission_text.py` check 1 | high |
| F4 | The text pasted into the live form was not `SUBMISSION_FORM_TEXT.txt`. It was a hand-trimmed variant, and it fails **3 of 7** checks. | the run quoted below | high |
| F5 | The enforced cap and the field's label had drifted apart, in the opposite direction from v9: the field now reads "under 10000", and the comment beside `FORM_LIMIT` still called 9,000 a quotation of it. | `tools/check_submission_text.py`, comment on `FORM_LIMIT` | medium |
| F6 | No new check is missing. The two that failed are the two written for exactly this defect, in v9 and v10. What was missing was the run. | the failure itself | the actual lesson |

## CRITIQUE LAYER: three hidden assumptions this pass broke

**A1: "the archive is verified because the repository is verified."** Not the same claim.
`make verify` was green when the last release was cut; two files were then edited by hand,
for a good reason, and the command was not re-run. Every number under `results/` was still
correct, all 67 claims still held, and the one command a judge is told to run still exited
1. A verified repository plus one unverified edit is an unverified repository - and the
qualification gate in the challenge rules is completeness and reproducibility *before*
rubric scoring, so the cheapest possible disqualification was sitting in front of the most
heavily audited artefact in the tree.

**A2: "the form text is the committed form text."** The v13 packaging audit found this
exact drift once (`SUBMISSION_AUDIT_LOG.md`, item 1: the live field still said "46/46
claims hold" at v13) and fixed it by pasting. Fixing an instance is not closing a class.
The two copies drifted again, and this time the live one was *shorter*: somebody trimmed
it to fit and dropped audited content. Run against the live text, the auditor says:

```
FAIL  every ablation figure matches results/ablation.json
        the pasted text no longer states the 'All five components' ablation row
        the review-count arithmetic no longer reads '= 132 reviews'
FAIL  every hostile-model figure matches results/model_invariance.json
        the crash disclosure no longer reads 'The other 12 crashed' - the incomplete
        runs are part of the claim, not a footnote
        the provenance progression no longer reads 'per 48 hostile reviews per mode:
        36/48 unguarded, 13/48 blocklist, 0/48 shipped'
FAIL  no load-bearing claim was lost in flattening
        missing the video-versus-repo authority notice

4/7 submission-text checks hold - 3 failed
```

Note what the trimming chose to drop: the 12 crashed runs, the two weaker guard modes, and
the paragraph telling a judge the video is older than the repository. Every one of them is
a disclosure that costs the submission something. Nothing that flatters it was lost. A
human trimming for length optimises for length and, without noticing, for flattery - the
reviewer-side twin of the sycophantic narrator in v5, and the reason the enforced list in
`tools/check_submission_text.py` is a list of *unflattering* sentences.

**A3: "9,000 is what the form says."** It was, in v9. The field now reads "under 10000
characters only. only plain text. no tables or other characters allowed." Both readings
cannot be evidence at once. The number is unchanged - it is the stricter one, and the count
that actually decides the outcome is the CRLF one, which no character counter in the page
reports - but it is now described as a **budget held deliberately**, not as a quotation. An
audit that calls its own policy a measurement is v9's defect with the shoes swapped, and it
was six releases old.

## VARIATION OPERATOR: two radically different ways to close this

**V1: make the live form unnecessary - ship the description as an artefact and have the
form point at it.** Put the audited text at a stable URL from the existing site build
(`tools/build_site.py` already emits `site/`), paste a two-line pointer into the field, and
the drift class disappears because there is only one copy. **Rejected.** It answers "the
two copies disagree" by making a judge follow a link to read the first artefact they are
handed, and the form field is the one surface where a broken link costs the whole entry. It
also moves the description outside the archive, the opposite of the direction v8 moved it,
for the same reason v8 was right.

**V2: raise `FORM_LIMIT` to 10,000 and keep the longer text.** One line, both tests green,
and defensible on the evidence: the label genuinely says 10,000 now. **Rejected, and it is
the more interesting rejection.** Editing the constant a test asserts, in the same pass in
which that test fails, converts a failing audit into a passing one without touching the
artefact the audit is about. Every number here is published because the alternative was a
claim nobody could check; a limit relaxed to fit its own text is that alternative arriving
through the audit tool. The characters came out of the prose instead, and checks 3 to 7
did not let any figure or any load-bearing sentence come out with them.

## What was done

1. **`SUBMISSION_DESCRIPTION.md` rebuilt** with a header that says what the file is, the
   paste marker restored, and the text below it byte-identical to
   `SUBMISSION_FORM_TEXT.txt` - which is what `tools/check_docs.py` asserts, rather than
   merely that both files exist.
2. **`SUBMISSION_FORM_TEXT.txt` trimmed from 9,229 to 8,903 characters** (8,948
   CRLF-normalised; 52 spare on the stricter count, roughly 1,100 against the field's
   current label). Eight edits, all prose, no figures: a "count what goes in, count what
   comes out" that the same paragraph restates as an arithmetic; a sentence on ablation
   shape compressed by half; four connective phrases; and "no detection metric moved",
   which `results/model_invariance.md` says at length.
3. **`FORM_LIMIT`'s provenance corrected** in `tools/check_submission_text.py`, in its
   module docstring, in `tools/check_docs.py`, and in the comment on the test in
   `tests/test_all.py`. Value unchanged at 9,000.
4. **Nothing under `sentinel/` touched.** The freeze still names the same ten files in
   `results/holdout/generalization.json`, so the held-out attestation is undisturbed, and
   no decision number could move because no decision code ran differently.

## What was deliberately not done

**No new check was added, and the test count is unchanged at 129.** The temptation at the
end of an audit is to leave a check behind, because that is what the previous fourteen
passes did. There was nothing to add: `check_paste_ready_description` caught F2 and
`check_fits_the_form` caught F3, on the first run, with exact counts and reasons. A
fifteenth guard over a suite that already reported the defect would confuse the finding
with the fix, and the finding is a process one. It is now written where the edit happens,
at the top of `SUBMISSION_DESCRIPTION.md`: do not hand-edit either copy without re-running
`make verify`.

The one guard that cannot be written is the one that matters most: **nothing inside a
repository can verify a textarea on someone else's website.** F4 is unfixable in code by
construction. It is fixable in sixty seconds by a human, once, and the auditor prints the
diff.

## Every number, after the edits

Re-asserted after the changes rather than before them:

```
python3 tools/check_results.py          -> 67/67 claims hold
python3 tools/check_docs.py             -> 9/9 documentation checks
python3 tools/check_submission_text.py  -> 7/7 submission-text checks
python3 -m unittest discover -s tests   -> 129 tests, OK
make verify                             -> exit 0
```

Unsafe approvals 0/12 and 0/9, recall 0.970 and 0.96, plans 12/12, modelled minutes 9.2
and 10.7, decision surface 0 of 168 completed reviews: none moved, which is the expected
result and is why it is stated. A packaging release that moved a decision number would be a
packaging release that changed the pipeline.

## Hot take

v14's lesson was *count what goes in, count what comes out, publish the difference*. v15 is
the same sentence pointed at the pipeline that produces the submission rather than the one
that reviews migrations: **an audit is a claim about the moment it last ran, and every edit
after that moment is unaudited by definition.** The tell is not a failing check. The tell is
a green check with a timestamp older than the file it describes.

The fix that generalises is not another check. It is that the last command before shipping
must be the same command the documentation tells a stranger to run first - which is why
`make verify` here has grown in five consecutive releases by absorbing suites that were
sitting outside it, and why the honest reading of every one of those growths is that the
suite was green and the command was not.
