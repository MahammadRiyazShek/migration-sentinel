# Session 08 - supervisor: the artefact outside the repository

**Agent:** Claude Opus 5, ClickUp Brain agentic assistant. Fresh context, supervisor role.
**Given:** the v7 source archive (`migration-sentinel-source.zip`), the challenge brief and rubric,
and the text as actually pasted into the micro1 submission form.
**Tools:** one sandboxed Python 3.12.13 shell. **No network access. No `pip install`.**
**Instruction:** find the assumptions this submission does not know it is making and try to make a
published number false; then fix what breaks; do not hand the work back.

Full reasoning, the critique layer and the rejected variations are in
[`docs/SUPERVISOR_LOG_V8.md`](../docs/SUPERVISOR_LOG_V8.md). This file is the trace.

---

## Step 1 - reproduce everything from the archive before touching it

```
$ python3 --version
Python 3.12.13

$ python3 -m unittest discover -s tests
Ran 33 tests in 1.34s
OK

$ python3 eval/run_eval.py --ablations
... 3 headline arms + 6 ablation arms x 12 cases = 108 reviews

$ python3 eval/model_invariance.py
... 180 reviews, 0/168 decision surface changed

$ python3 tools/check_results.py
PASS  ... (27 lines)
27/27 claims hold

$ python3 tools/check_docs.py
5/5 documentation checks hold across 191 authored files

$ python3 tools/test_browser_driver.py
12/12 cases reproduce the recorded packet through the browser driver
```

**Human checkpoint.** Nothing false. Seven sessions have audited the numbers, the packet prose and the
documentation's claims about the repository. I asked the operator which artefacts a judge sees that
are *not* in this repository. Answer: the submission form, the uploaded zip, the video, the live demo.
Of those, the form's Description field is the only one every judge reads before opening anything.

## Step 2 - diff the form text against the verified source

```
$ python3 - <<'EOF'
# SUBMISSION_DESCRIPTION.md is the text v7 verified line by line.
# /tmp/drift/as_submitted.txt is the text actually in the form.
EOF
```

Tool response, summarised: the verified text leads with a nine-row markdown table. The form field is
plain text, cap 10,000. The submitted text is a hand-flattened version at 3,752 characters, and five
things are missing or demoted:

1. the verification lede (`python tools/check_results.py -> 27/27 claims hold`) demoted from the
   second sentence to mid-paragraph, behind the results it guarantees;
2. "**Baseline vs advanced.** A: ... B: ... Sentinel: ..." collapsed to "Arms: A, B, Sentinel";
3. "byte-identical on verdict, hazards, severities, evidence, ledger, generated SQL and verification"
   compressed to "byte-identical throughout";
4. `trajectories/` never cited - only `agent_traces/`, which is the development traces, not
   deliverable 04;
5. "An agent that grades its own work has graded itself." deleted.

Plus: "9 arms x 12 cases = 108 reviews, one component removed at a time" - three of the nine arms are
the headline arms and have no component removed.

**This is the feedback that shaped every step after it.** `tools/check_docs.py` asserts the
description *fits* the field. Nothing asserted what it *contains*. Length was audited; content was
not; so the lossy transform on the way out of the repository was free to drop the one sentence that
licenses trust in all the others.

## Step 3 - first attempt at the checker, and four of my own bugs

```
$ python3 tools/check_submission_text.py
FAIL  every ablation figure matches results/ablation.json
        All five components: form says 0/12, 0.97, 12/12, 0/2, 9.2.; results/ablation.json says 0/12, 0.97, 12/12, 0/2, 9.2
        Rules only: form says 1/12, 0.576, 0/12, 0/2, 23.3.; ...
        Replay only: form says 2/12, 0.333, 12/12, 0/2, 8.8.; ...
        No coverage gate: form says 0/12, 0.97, 12/12, 1/2, 8.5.; ...
FAIL  every hostile-model figure matches results/model_invariance.json
        the decision-surface claim no longer reads 'changed in 0 of 0 completed reviews'
        the crash disclosure no longer reads 'The other 180 crashed' - ...
4/6 submission-text checks hold - 2 failed
```

Six failures, **all six false**. Retries and what each taught:

**M1.** `([0-9/., ]+)` captured the sentence-final full stop, so `9.2.` was compared against `9.2` and
four correct rows failed. Fixed with `part.strip(".")` and a comment saying why.

**M2.** The harder one, and the one worth keeping. I summed `r.get("reviews_completed", 0)`. That key
does not exist in `results/model_invariance.json`:

```
$ python3 -c "import json; print(sorted({k for r in json.load(open('results/model_invariance.json'))['rows'] for k in r}))"
['cases', 'changed_fields', 'crash_example', 'crashed', 'decision_surface_changed', ...]
```

The `.get` default meant it did not raise. It computed `0 of 0` and reported a failure against a claim
the text stated correctly. **A checker with a default can pass while reading nothing**, which is worse
than a missing check because it looks like evidence. Rewritten as `r["cases"] - r["crashed"]`,
subscripted, so a renamed field is a `KeyError` and not a zero.

**M3.** Found by re-reading the description rather than the code: my first draft never audited the
36/48 -> 13/48 -> 0/48 provenance progression or the 0-of-60 model-written headlines. Those are the
v5 finding and the foundation of the hot take, and the checker walked past them because they are
prose rather than a list. Added, with a guard that all three narrator modes still see the same
hostile review count - a progression over three unequal denominators is not a comparison:

```
$ python3 -c "..."
structural hostile reviews 48 misleading printed 0
pattern    hostile reviews 48 misleading printed 13
off        hostile reviews 48 misleading printed 36
shipped mode model-written headlines: 0 of 60
```

**M4.** I widened `check_docs.py`'s `LIVE_DOCS` to include `README.md` and immediately broke the
distinction it was drawn to protect:

```
$ python3 tools/check_docs.py
FAIL  no stale claim count in a current-state document
        README.md:424 says 13/13 claims, the audit asserts 27
```

`README.md:424` is a row in the Improvement Changelog: "13/13 claims at that iteration (23/23
today)". An older count there is the honest record of an older run. v7 drew that list narrowly on
purpose and I widened it without reading why. Reverted; the README is in the new test-count list only,
with the reasoning in a comment.

## Step 4 - prove the audit is load-bearing, not decorative

Ran the finished checker against the text **as originally submitted**:

```
$ python3 tools/check_submission_text.py
        3752 of 10000 characters, 6248 spare
PASS  the pasted description fits the form's plain-text field
PASS  it is plain text: no markdown, no smart punctuation
PASS  every headline figure matches results/evaluation.json
FAIL  every ablation figure matches results/ablation.json
        the pasted text no longer states the 'All five components' ablation row
PASS  every hostile-model figure matches results/model_invariance.json
FAIL  no load-bearing claim was lost in flattening
        missing the verification lede, in the first 1200 characters - reproducibility is 15% and the second tie-break; ...
        missing the explicit baseline-and-advanced framing - the challenge requires an entry to present both ...
        missing what byte-identical is over - an enumerated invariance claim is checkable; 'byte-identical throughout' is not
        missing the pointer to the in-product agent trajectories - deliverable 04 is the runtime trajectories ...
        missing the video-versus-repo authority notice - the submitted video is older than the repository; ...
4/6 submission-text checks hold - 2 failed
```

Then against the corrected text:

```
$ python3 tools/check_submission_text.py
        9422 of 10000 characters, 578 spare
PASS  the pasted description fits the form's plain-text field
        no markdown, no smart punctuation, 7-bit ASCII throughout
PASS  it is plain text: no markdown, no smart punctuation
        9 headline rows match results/evaluation.json arm for arm
PASS  every headline figure matches results/evaluation.json
        4 ablation rows and the 108-review arithmetic match results/ablation.json
PASS  every ablation figure matches results/ablation.json
        invariance arithmetic, 0/168 decision surface, the 12 declared crashes, the provenance progression and 0/60 model-written headlines all match results/model_invariance.json
PASS  every hostile-model figure matches results/model_invariance.json
        all 7 load-bearing sentences survived the flattening, in position
PASS  no load-bearing claim was lost in flattening

6/6 submission-text checks hold: the description in the form is the description this repository can back
```

## Step 5 - pin it, so it cannot rot

Five tests added, 33 -> 38. The load-bearing one iterates `REQUIRED_CLAIMS`, deletes each matched
sentence in turn and asserts the audit fails every time - a required claim whose removal the audit
tolerates is a regex nobody is defending. Another reproduces the actual defect, which was a
*demotion* rather than a deletion: it moves the verification lede to the end of the text and asserts
the position check catches it.

```
$ python3 -m unittest discover -s tests
Ran 38 tests in 1.03s
OK
```

## Step 6 - final state, all green, offline

```
$ python3 -m unittest discover -s tests   ->  Ran 38 tests ... OK          1.03 s
$ python3 eval/run_eval.py --ablations    ->  108 reviews, tables identical  0.95 s
$ python3 eval/model_invariance.py        ->  180 reviews, 0/168 changed     1.87 s
$ python3 tools/check_results.py          ->  27/27 claims hold             0.06 s
$ python3 tools/check_docs.py             ->  6/6 checks, 193 files         1.81 s
$ python3 tools/check_submission_text.py  ->  6/6 checks                    0.09 s
$ python3 eval/time_sensitivity.py        ->  6 constant sets, 2 reversing  0.11 s
$ python3 tools/test_browser_driver.py    ->  12/12 packets reproduce       0.30 s
```

## Human checkpoints in this session

* the operator confirmed the form text as pasted, which is the only source for the diff in step 2 -
  it cannot be read out of the repository;
* the decision to keep the human flattening and audit it, rather than generate the description from
  a template. Both alternatives are written up and rejected in `docs/SUPERVISOR_LOG_V8.md` §4;
* the seven `REQUIRED_CLAIMS` are a human judgement about which sentences are load-bearing under a
  lossy transform. The checker enforces them; it did not choose them. Each carries its reason in the
  source so a future deletion has to argue with the reason rather than delete a regex;
* nothing in `sentinel/`, `eval/cases/`, `eval/scoring.py`, `memory/` or `results/` was touched, and
  `tools/check_results.py` is unchanged, so "27/27" still means in v8 what it means in the video.
