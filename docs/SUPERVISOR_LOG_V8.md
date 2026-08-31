# Supervisor log v8: the artefact outside the repository

**Session:** eighth, supervisor role. Fresh context, given the v7 source archive
(`migration-sentinel-source.zip`), the challenge brief, the rubric, and the text as actually pasted
into the micro1 submission form. Sandboxed Python 3.12.13, **no network access, no `pip install`**.

**Instruction:** the same one every supervisor session gets - find the assumptions this submission
does not know it is making and try to make a published number false - plus "then fix what breaks",
and "do not hand the work back".

**Result:** could not make a number false. Found the drift instead, one layer further out than any
previous session had looked, and shipped the audit for it.

---

## 1. Re-run from the archive, before touching anything

| command | result | wall |
|---|---|---|
| `python3 -m unittest discover -s tests` | `Ran 33 tests ... OK` | 1.34 s |
| `python3 eval/run_eval.py --ablations` | 108 reviews, tables identical to the committed ones | 0.95 s |
| `python3 eval/model_invariance.py` | 180 reviews, 0/168 decision surface changed | 1.87 s |
| `python3 tools/check_results.py` | **27/27 claims hold** | 0.06 s |
| `python3 tools/check_docs.py` | **5/5 documentation checks hold** across 191 files | 1.81 s |
| `python3 eval/time_sensitivity.py` | six constant sets, two still reversing sign | 0.11 s |
| `python3 tools/test_browser_driver.py` | **12/12** packets reproduce through the browser driver | 0.30 s |

Offline, no key, $0.00. Nothing to report. Seven sessions have now audited the numbers, the prose in
the packet, and the documentation's claims about the repository. So the question stopped being
"which number is wrong" and became **"which artefact has nobody pointed a checker at"**.

---

## 2. The finding: the first thing a judge reads is not in the repository

`tools/check_results.py` audits the numbers. `tools/check_docs.py` audits what the documentation
claims about the repository. Both stop at the repository boundary. On the other side of that
boundary sits the artefact that is read **first and by every judge**, before any file is opened:

> the Description field of the micro1 submission form.

That field is capped at 10,000 characters and specifies **plain text only**. `SUBMISSION_DESCRIPTION.md`
- the text v7 verified line by line - leads with a nine-row markdown table. It cannot be pasted into
a plain-text field as written. So it was flattened by hand, and the flattening was the one edit in
this submission that no tool in the repository could see.

Diffing the text as actually submitted against the verified source, four load-bearing things were
gone and one had been demoted:

| what was lost | why it costs a rubric row |
|---|---|
| **the verification lede.** `python tools/check_results.py -> 27/27 claims hold` was the second sentence. In the pasted text it sat mid-paragraph, behind the nine results it exists to guarantee | Reproducibility is 15% of the score and the second tie-break. The single strongest sentence in the submission was reading as a footnote to the numbers instead of the licence to trust them |
| **the explicit baseline-and-advanced framing.** "**Baseline vs advanced.** A: one model call on the diff. B: ... Sentinel: five agents over ..." collapsed to "Arms: A, B, Sentinel" | The rules require every valid entry to *present* both a baseline and an advanced solution. A judge ticking that box wants the sentence, not an inference from a metrics table |
| **the enumeration behind "byte-identical".** "byte-identical on verdict, hazards, severities, evidence, ledger, generated SQL and verification" became "byte-identical throughout" | The enumeration is the claim. "Throughout" is an assertion a judge has no way to size |
| **the pointer to `trajectories/`.** The pasted text cited `agent_traces/` alone | `agent_traces/` holds the *development* sessions. Deliverable 04 is the runtime trajectories of the five in-product agents, and those live in `trajectories/`. The submission was pointing the trace check at the wrong directory |
| **"An agent that grades its own work has graded itself."** | The one sentence that makes the never-delegated list mean something |

None of that moves a metric. All of it is read before any metric is. Which is v7's lesson exactly,
one layer out: v7 audited the pages a judge reads before reaching a number; **v8 found the page a
judge reads before reaching the repository.**

A second, smaller defect in the same text: "9 arms x 12 cases = 108 reviews, one component removed
at a time". Three of those nine arms are the headline arms and have no component removed. The
arithmetic is right and the sentence describing it is not, which is the kind of thing that costs
more credibility than it saves characters.

---

## 3. Critique layer: three hidden assumptions in my own first approach

My first instinct was to rewrite the description and hand it back. Acting as external supervisor on
that plan:

**A1. It assumes the defect is this text, when the defect is that the text is unaudited.**
A rewritten description is correct exactly once, until the next revision before the deadline. Every
previous session shipped a *checker* for the layer it attacked, and that is why "27/27" still means
in v8 what it meant in v5. Shipping prose here would have been the first session to break that
pattern, on the artefact with the widest reach and the shortest review time.

**A2. It assumes the form is downstream of the repository, when the rubric reads it as upstream.**
The internal model was: repository is the truth, the form is a summary of it. Every judge's actual
order is the reverse - form first, repository second, and only if the form earns it. Treating the
form as a derived artefact is precisely why it had no owner and no audit.

**A3. It assumes a plain-text constraint is a formatting problem.** It is a *lossy transform*, and
nothing in the repository declared which parts of the text were load-bearing under it. Length was
checked (`check_docs.py` asserts 10,000 characters). Content was not. So the transform was free to
drop the verification lede and pass every gate in the repository.

A fourth, kept for the record because it nearly shipped: I assumed the flattening was careless. It
was not. It was a sensible response to a real constraint, made without any statement of what had to
survive. **The fix is to write that statement down, not to be more careful.**

---

## 4. Variation operator: two radically different ways to solve it

**Variation 1 - generate the form text from the repository, never author it.**
Add a `build_submission_text` tool under `tools/` (never written, see below): read `results/*.json`, render the plain-text description from a
template, print it. The form text becomes build output, like `results/comparison.md`. Drift becomes
structurally impossible rather than detected.

*Rejected.* The generator becomes the only writer of the most persuasive 10,000 characters in the
submission, and this project's entire hot take is that a template rendering prose about its own
results is the failure mode, not the fix. It also inverts the honest dependency: the description
makes arguments (which metric is primary and why, what the tie at 0/2 means, which component is
defended first) that no template can hold. Named here rather than shipped, and the reasoning is the
same reasoning that kept `render_headline` a pure function of tool output while leaving the
per-hazard explanations to a model: **generate what is a fact, author what is a judgement.**

**Variation 2 - delete the flattening. Submit the markdown and let the field mangle it.**
Zero transform, zero drift. The verified text is the submitted text, byte for byte.

*Rejected, and it is the closest call.* A judge reading `| **Unsafe approvals** (primary) | 1/12 |`
as literal pipes and asterisks in the first screen of a submission about engineering quality has
already been told something. End-to-end quality is 20%. Trading a real presentation cost for a
tooling convenience is the wrong direction, and it makes the same mistake as A3 in the other
direction: treating the constraint as someone else's problem.

**What shipped is neither, and it is the third option the first two made visible:** keep the human
flattening, commit its output verbatim, and audit the transform. `SUBMISSION_FORM_TEXT.txt` is the
exact text in the form. `tools/check_submission_text.py` re-reads every figure in it out of
`results/*.json` and asserts that seven named sentences survived, in position. The judgement stays
human; the loss becomes checkable.

---

## 5. What shipped

| artefact | what it is |
|---|---|
| `SUBMISSION_FORM_TEXT.txt` | the exact text in the form's Description field, committed verbatim so it is auditable at all. 9,4xx of 10,000 characters, 7-bit ASCII, no markdown |
| `tools/check_submission_text.py` | six checks with an exit code. Fits the field; is plain ASCII with no markdown a plain-text field would render literally; every headline figure matches `results/evaluation.json` arm for arm; every ablation figure matches `results/ablation.json`; the invariance arithmetic, the 0/168 decision surface, the 12 declared crashes, the 36/13/0 provenance progression and the 0-of-60 model-written headlines match `results/model_invariance.json`; and seven named load-bearing sentences are present, with the verification lede inside the first 1,200 characters |
| `tests/test_all.py::TestSubmissionText` | five tests, 33 -> 38. The load-bearing one deletes each of the seven required sentences in turn and asserts the audit fails every time, so none of them is a regex nobody is defending. Another moves the verification lede to the end of the text - a demotion, not a deletion, which is what actually happened - and asserts the position check catches it |
| `tools/check_docs.py`, sixth check | the test count had no audit. A stale claim count survived two releases before v7 caught it; "33 tests" sat in six current-state documents with nothing reading it. Same defect class, same fix |
| the corrected form text | verification lede restored to the second paragraph; explicit baseline-and-advanced sentence restored; the byte-identical enumeration restored; `trajectories/` cited alongside `agent_traces/`; "an agent that grades its own work has graded itself" restored; the review-count arithmetic corrected to "3 headline arms plus 6 ablation arms ... = 108 reviews", which the audit now reads out of `results/ablation.json` rather than trusting |
| `docs/VIDEO_SCRIPT_V5.md` | a single-take script against v5, because the submitted video is v2 and the existing shot list is the v2 one with a v2 addendum bolted on |

**Evidence that the audit is load-bearing rather than decorative:** run it against the text as
originally submitted and it fails 2 of 6 checks and names all five losses. Run it against the
corrected text and it is 6/6. Both runs are in `agent_traces/session-08-supervisor-form-text-audit.md`.

---

## 6. My own mistakes, four of them

The v7 session logged that its first checker's failures were mostly false. Mine repeated it.

**M1. The ablation regex swallowed the full stop.** `([0-9/., ]+)` captured `9.2.` at the end of a
sentence, so the normaliser produced `9.2.` against `9.2` and **all four ablation rows failed on
values the text stated correctly**. Four false failures on the first run. Fixed by stripping the
sentence-final period, with the reason in the code: a row ends a sentence and the full stop is not a
digit. This is the exact failure mode v7 warned about, and I walked into it having read the warning.

**M2. I invented a JSON key.** The invariance check summed `r.get("reviews_completed", 0)`. That key
does not exist in `results/model_invariance.json`; the rows carry `cases` and `crashed`, and
completed has to be derived. `.get(..., 0)` meant it did not raise - it silently computed `0 of 0`
and reported a failure against a claim the text made correctly. **A checker with a default is a
checker that can pass while reading nothing**, and that is worse than a missing check, because it
looks like evidence. Fixed to `r["cases"] - r["crashed"]`, subscripted so a renamed field is a
`KeyError` rather than a zero.

**M3. My first draft did not read the sharpest claim in the description at all.** The
36/48 -> 13/48 -> 0/48 provenance progression and the 0-of-60 model-written headlines are the v5
finding, the thing the whole hot take rests on, and the checker walked straight past them. I had
audited the paragraphs that looked like tables and skipped the paragraph that carried the argument.
Both are now read out of `results/model_invariance.json`, including a guard that the three narrator
modes still see the same hostile review count - because a progression across three unequal
denominators is not a comparison.

**M4. I widened `check_docs.py`'s current-state list to include `README.md` and broke the
distinction it was drawn to protect.** The claim-count audit immediately fired on
`README.md:424`, "13/13 claims at that iteration (23/23 today)" - a row in the Improvement
Changelog, where an older count is the honest record of an older run. v7 drew `LIVE_DOCS` narrowly
on purpose and I widened it without reading why. Reverted: the README stays out of the claim-count
list and is in the test-count list, because no changelog row phrases a count as "N tests", and the
comment in the code now says so.

M2 is the one worth keeping. M1 and M4 produced loud false failures and cost ten minutes. M2 was
silent, and a silent checker is the thing this whole repository exists to argue against.

---

## 7. What this session did not touch

No pipeline code. No case, no ground-truth label, no hazard, no severity, no scorer, no
reviewer-minute constant, no primary metric, no narrator, no prompt.

`results/` is byte-identical to the archive, and that is checked rather than asserted. Re-running
`eval/run_eval.py --ablations` in this sandbox regenerated it, so every leaf of every regenerated file
was diffed against the archive: **20 differing leaves across the 12 packets, all of them `ms` or
`wall_ms`** - wall clock on a slower machine, nothing else. The archive's `results/` and
`trajectories/` were then restored, so the shipped evidence is the evidence the video and the
documentation quote, down to the 7.9 ms in `results/comparison.md`. Regenerating them on your own
machine will move those timings and nothing else.

**Every detection number is unchanged**: unsafe
approvals 0/12, strict recall 0.970, precision 0.970, severity agreement 0.969, verified plans
12/12, gap cases cleared 0/2, evidenced findings 35/35, 9.2 modelled reviewer minutes per case.
`tools/check_results.py` still reports 27/27 after every edit above, and it is unchanged - the new
checks live in a separate tool for the same reason v7 kept `check_docs.py` separate: so "27/27"
keeps meaning what it means in the video.

Counts that did move, and they are all counts of audits rather than of results: tests 33 -> 38,
documentation checks 5 -> 6, and a new file of 6 submission-text checks.

---

## 8. Hot take, v8

Seven sessions audited the artefacts inside the boundary they could see. The submission's weakest
link was a hand transform on the way out of it, performed for a good reason, with nothing declaring
what had to survive.

**Every lossy transform on the way to your user needs a statement of what has to survive it, or the
transform will decide for you and every gate upstream will still be green.** The repository was
27/27, 5/5 and 12/12 while the first paragraph a judge would read had lost the sentence that makes
all three worth anything.

The generalisation for anyone building agent systems: the pipeline is not finished at the last
component you wrote. It finishes at the last edit before a human reads it, and that edit is usually
a person reformatting something under a constraint your tests have never heard of. Audit the artefact
your user actually receives - not the one your last stage emitted.
