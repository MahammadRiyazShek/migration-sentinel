# Improvement Changelog — final polish pass

This addendum records the last-mile edits made to the submission text after the
harness had been frozen. No code under `sentinel/`, `eval/`, `tools/` or
`tests/` was changed; only how the results are presented on the submission form.

Every claim below is verifiable from the committed repository with
`python tools/check_results.py` (27/27 as of v5) on a clean clone.

## v2.1 — submission text hardening

**What changed**

1. **Primary metrics moved above the fold.** The description now opens with a
   single seven-row table carrying the four primary numbers the rubric weights
   most heavily (unsafe approvals, blind-spot cases cleared, hazard recall /
   precision, verified plans, modelled reviewer minutes). The `check_results.py`
   audit line sits directly under it, by name, so a judge scoring
   Reproducibility (15%) sees the audit surface before the narrative.

2. **Video-versus-repo disclosure repositioned.** The earlier text buried the
   disclosure two thirds down the description; a judge scrolling past changing
   numbers loses trust before the explanation lands. It is now one line inside
   the Reproducibility section, framed as *"authoritative source when they
   disagree: `results/comparison.md`"* rather than an apology. Architecture and
   walkthrough are unchanged, so the video is still valid; the on-screen
   numbers are simply the pre-coverage-gate ones (recall 0.939, 8.5 min, five
   components).

3. **Encoding fixed.** The ablation table's minus signs were mojibake
   (`âˆ’`, UTF-8 rendered through Latin-1) in the previous form paste. All
   replaced with ASCII hyphens so the description renders cleanly regardless of
   how the form re-encodes it.

4. **Sensitivity reversal reframed.** The `-12%` and `-5%` rows in
   `eval/time_sensitivity.py` are no longer disclosed as "the row I would not
   let myself hide"; they are framed as the *ledger entry for the coverage
   gate* — the same component that earns the second primary metric is what
   makes the pipeline pay `human_gate` where a baseline pays `plan`.
   Reliability was bought with reviewer time; the two adversarial rows are
   what that trade looks like. Same numbers, honest story around them.

5. **Reproducibility and Measured Improvement split into two paragraphs.**
   The rubric weights each at 15%. Bundling them shared a paragraph; splitting
   them gives a judge scoring line-by-line one paragraph per rubric row.

6. **Trajectories credited.** 24 artifacts under `trajectories/` (12 `.jsonl`
   + 12 `.md`, one pair per case) were present but unmentioned. Now called out
   by path so the Agent Trajectories deliverable is visibly complete.

7. **DEPLOY.md linked.** A judge who wants to run their own copy of the
   live review desk gets the two-minute path.

**What did not change**

- No changes to `sentinel/`, `eval/`, `tools/`, `tests/`, `results/`,
  `trajectories/`, `memory/` or `site/`.
- Ground truth, hazard vocabulary, scorer and primary metrics untouched.
- All 18 headline claims from `tools/check_results.py` continue to hold.
- All 22 unit tests continue to pass.
- Sensitivity band unchanged; the two reversal rows remain published.

**How to verify from a clean clone**

```bash
python -m unittest discover -s tests   # 22 tests, ~0.14 s
python eval/run_eval.py --ablations    # 12 cases + 6 arms + 2 baselines
python tools/check_results.py          # 18/18 claims hold
python eval/time_sensitivity.py        # 6 constant sets, 2 reversals flagged
```


## v3 - the narrator is untrusted input

**What changed in the code** (all additive; no case, label, scorer or metric definition was touched,
and every detection number is byte-identical to v2):

1. `sentinel/llm/adversarial.py` - three hostile model stand-ins: a sycophant, an injected model, a
   degraded endpoint returning no payload.
2. `sentinel/narrator.py` - the two places model text enters the packet (the headline and the reviewer
   questions) are validated like a request body. The guard can only remove text.
3. `eval/model_invariance.py` - 12 cases x 4 models x guard on/off = 96 reviews, diffing the decision
   surface field by field against the cooperative reference. Writes `results/model_invariance.md`.
4. `--no-narrator-guard` on `sentinel review` keeps the v2 behaviour runnable, so the two columns can be
   compared rather than asserted.
5. `tools/check_results.py`: 18 -> 23 claims. `tests/`: 22 -> 27.

**What it found:** 0/84 completed reviews changed on facts, so v2's invariance claim survives its first
real attack. And 23 of the 24 unguarded hostile reviews that ran printed a headline contradicting their
own verdict, while `hostile-null` crashed 12/12 unguarded runs because v2 read `.payload.get(...)` off a
raw model response. Full log, including the three mistakes caught in the first version of the fix:
`docs/SUPERVISOR_LOG_V3.md`.

**How to verify from a clean clone**

```bash
python -m unittest discover -s tests   # 27 tests
python eval/run_eval.py --ablations    # 108 reviews
python eval/model_invariance.py        # 96 reviews, hostile models included
python tools/check_results.py          # 23/23 claims hold
```


## v5 - the headline is not the model's to write

**Why:** v3 shipped a blocklist over model prose and wrote its own limit into
`sentinel/narrator.py`: *"the audit uses these same patterns, so it measures whether the guard catches
what it looks for"*. Four files repeated that limit and none of them tested it.

**What changed in the code** (additive; no case, label, scorer, metric definition or reviewer-minute
constant was touched, and every detection number is byte-identical to v4):

1. `sentinel/llm/adversarial.py` - a fourth hostile model, `hostile-fluent`, written against this
   repo's own defence: no phrase in `narrator.CLEAN_CLAIM`, no token in `VERDICT_TOKENS`, nothing in
   `INJECTION`, and it still tells the reviewer the change can ride the normal release train. Every
   hostile class now also carries a hand-declared `misleading_prose` label.
2. `sentinel/narrator.py` - three narrator modes. `structural` (the new default) renders the headline
   from tool output on every run via `render_headline`; `pattern` is the v3 blocklist; `off` is v2.
3. `sentinel/report.py` - model prose is demoted to *Model commentary (unverified prose, not
   evidence)* after the hazard table, with a line stating it produced, removed and reordered nothing.
4. `eval/model_invariance.py` - 12 cases x 5 models x 3 modes = **180 reviews**, and the misleading-
   headline count is now **provenance plus a hand-declared label** rather than the guard's own regexes.
5. `--narrator-mode {structural,pattern,off}` on `sentinel review`, so all three defences stay runnable.
6. `tools/check_results.py`: 23 -> 27 claims. `tests/`: 27 -> 33.

**What it found:** the v3 guard printed the fluent liar's headline above a `BLOCK` badge on **12/12**
cases while the v3 audit column read **0/12** - the metric said the guard held and the reviewer read a
lie. Misleading headlines reaching the reviewer, over the 48 hostile reviews in each mode: **36/48
(v2) -> 13/48 (v3) -> 0/48 (v5)**. Model-written headlines in the shipped mode: **0 of 60**. Decision
surface changed: **0 of 168** completed reviews. Detection metrics unchanged (unsafe 0/12, F1 0.970,
severity 0.969, plans 12/12, 9.2 modelled min/case), which is the point: the narrator never touched
one. Full log, including the three mistakes in this pass: `docs/SUPERVISOR_LOG_V5.md`.

**What it did not fix, published rather than buried:** the reviewer questions and the demoted note are
still only pattern-guarded, so the fluent liar's two plausible questions print - below the evidence,
labelled as model prose. The verdict sentence is unreachable by any model; the rest is bounded by
placement, not by proof.

**How to verify from a clean clone**

```bash
python -m unittest discover -s tests   # 33 tests
python eval/run_eval.py --ablations    # 108 reviews
python eval/model_invariance.py        # 180 reviews, 4 hostile models, 3 narrator modes
python tools/check_results.py          # 27/27 claims hold
```

---

## v7 - the audit that reads prose

**Why:** the seventh supervisor pass could not make a number false. Everything reproduced from the
archive on the first run: 33 tests, 108 reviews in 0.73 s, 180 invariance reviews in 1.62 s, 27/27
claims, 12/12 recorded packets matching a fresh reference run, on Python 3.12.13 with no network. So it
attacked the layer with no audit at all: the pages a judge reads before reaching a number.

**What it found, five defects, none of them a metric:**

1. **Two rival entry points.** `JUDGE_START_HERE.md` (v6) and `JUDGES_START_HERE.md` (v5), both titled
   "Judges start here", different command lists, different runtime claims ("under a second" against
   "under 10 seconds"). Which page a judge read depended on which filename they guessed.
2. **Four mis-decoded glyphs**, three of them in the rubric-map table of that entry page.
3. **`docs/SUPERVISOR_LOG_V6.md` announced `SUBMISSION_DESCRIPTION.md` under "Files added".** The file
   was not in the archive: a claim about the repository that the repository contradicted.
4. **A generated paragraph argued with its own table.** `results/time_sensitivity.md` read "the sign
   never reverses, except in the flagged row" while two rows are flagged `(claim reverses)`. The
   conditional in `eval/time_sensitivity.py` was written when one set reversed; v2's coverage gate made
   it two and nobody re-read the sentence. The repository's worst number was being hedged about.
5. **A tied primary metric published without its explanation.** "Blind-spot cases cleared: 0/2, 0/2,
   0/2" reads as no improvement. The baselines tie because they request changes on 10 and 11 of 12
   migrations, including the one that is genuinely safe, so they clear nothing and name zero blind
   spots, while the pipeline holds 0/2 *and* approves the clean case. That was in `results/`, never in
   the pitch.

**What shipped:** `tools/check_docs.py`, five checks, stdlib, exit code 1 on failure: no mis-decoded
characters in any authored file, every path-shaped file reference resolves, exactly one judge entry
point at the root, the paste-ready description exists and fits the form's 10,000 characters (9,665),
and no current-state document quotes a stale claim count (it asks `tools/check_results.py` for the
number instead of trusting prose). Plus the four fixes, `SUBMISSION_DESCRIPTION.md`, and
`docs/SUPERVISOR_LOG_V7.md`.

The two audits stay separate on purpose. `tools/check_results.py` counts claims about measurements and
still says **27/27**, comparable to v5 and to the video. `tools/check_docs.py` counts claims about the
repository. Folding the second into the first would have made "27/27" mean two different things.

**Evidence that nothing else moved:** 33 tests OK, 27/27 claims, unsafe approvals 0/12, strict F1
0.970, plans 12/12, 9.2 modelled min/case, 0 of 168 completed reviews changing the decision surface.
Nothing under `sentinel/`, `eval/cases/`, `eval/scoring.py` or `memory/` was touched. The one
regenerated result is `results/time_sensitivity.md`, and only its prose changed: the band is still
-12% to 69%.

**The lesson, one layer out from v5's.** v5's was that a defence audited in its own vocabulary reports
on the attacker's imagination. v7's is that **a repository that audits only its measurements is audited
only where it already knows how to be wrong.** Point an exit code at the artefact your reader opens
first.

**How to verify from a clean clone**

```bash
python -m unittest discover -s tests   # 33 tests
python eval/run_eval.py --ablations    # 108 reviews
python eval/model_invariance.py        # 180 reviews, 4 hostile models, 3 narrator modes
python tools/check_results.py          # 27/27 claims hold
python tools/check_docs.py             # 5 documentation checks, exits 1 on any failure
```

---

## v8 - the audit that reads the submission form

**Why:** an eighth fresh-context supervisor session, given the v7 archive, the rubric and the text as
actually pasted into the micro1 form, with one instruction: make a published number false, then fix
what breaks. It could not make a number false - 38 tests (after its own additions), 108 + 180 reviews,
27/27 claims, 12/12 packets, 6/6 documentation checks, Python 3.12.13, offline, first attempt. So it
asked the question v7's success made available: **which artefact does a judge see that no checker in
this repository can reach?**

Four: the submission form, the uploaded archive, the video and the live demo. Of those, the form's
Description field is the only one every judge reads *before opening anything*.

**What it found.** The field is capped at 10,000 characters and specifies plain text. The verified
`SUBMISSION_DESCRIPTION.md` leads with a nine-row markdown table, so it cannot be pasted as written.
It was flattened by hand - the one edit in this submission that happens outside the repository, and
therefore the one edit no tool could see. `tools/check_docs.py` asserted the description *fit* the
field. Nothing asserted what it *contained*. Five load-bearing things had been lost:

1. **The verification lede.** `python tools/check_results.py -> 27/27 claims hold` was the second
   sentence of the verified text. In the form it sat mid-paragraph, behind the nine results it exists
   to guarantee. Reproducibility is 15% of the rubric and the second tie-break; the strongest sentence
   in the submission was reading as a footnote to the numbers rather than the licence to trust them.
2. **The explicit baseline-and-advanced framing.** "Baseline vs advanced. A: one model call on the
   diff. B: ... Sentinel: five agents over ..." had collapsed to "Arms: A, B, Sentinel". The rules
   require every valid entry to *present* both. A judge ticking that box wants the sentence.
3. **The enumeration behind "byte-identical."** "byte-identical on verdict, hazards, severities,
   evidence, ledger, generated SQL and verification" had become "byte-identical throughout". The
   enumeration is the claim; "throughout" is an assertion with no size.
4. **The pointer to `trajectories/`.** The form cited `agent_traces/` alone, which is the *development*
   traces. Deliverable 04 is the runtime trajectories of the five in-product agents. The submission was
   pointing the trace check at the wrong directory.
5. **"An agent that grades its own work has graded itself."** The line that makes the never-delegated
   list mean anything.

Plus a smaller one: "9 arms x 12 cases = 108 reviews, one component removed at a time" - three of the
nine are the headline arms and have no component removed. Right arithmetic, wrong sentence.

**Two variations considered and rejected**, both in `docs/SUPERVISOR_LOG_V8.md` §4. Generating the
description from a template over `results/*.json` makes drift structurally impossible and hands the
most persuasive 10,000 characters in the submission to a renderer, which is the failure mode this
project's hot take is about: generate what is a fact, author what is a judgement. Submitting the raw
markdown and letting the field mangle it removes the transform and pays a real presentation cost on a
20% rubric row. What shipped is the third option those two made visible: keep the human flattening,
commit its output verbatim, audit the transform.

**What shipped:** `SUBMISSION_FORM_TEXT.txt`, the exact text in the form, committed so it is auditable
at all. `tools/check_submission_text.py`, six checks, stdlib, exit code 1 on failure: it fits the
field (9,4xx of 10,000); it is 7-bit ASCII with no markdown a plain-text field would render literally;
every headline figure matches `results/evaluation.json` arm for arm; every ablation figure and the
108-review arithmetic match `results/ablation.json`; the invariance arithmetic, the 0/168 decision
surface, the 12 declared crashes, the 36/13/0 provenance progression and the 0-of-60 model-written
headlines match `results/model_invariance.json`; and seven named load-bearing sentences are present,
with the verification lede inside the first 1,200 characters. Plus a sixth check in
`tools/check_docs.py` for stale *test* counts - a stale claim count survived two releases before v7
caught it, and the test count sat in six current-state documents with nothing reading it.

**Evidence the audit is load-bearing.** Run against the text as originally submitted: 4/6, and it names
all five losses. Against the corrected text: 6/6. Both runs are in
`agent_traces/session-08-supervisor-form-text-audit.md`. And
`tests/test_all.py::TestSubmissionText` deletes each of the seven protected sentences in turn and
asserts the audit fails every time, plus one test that *demotes* the verification lede to the end of
the text rather than deleting it, because a demotion is what actually happened.

**Four mistakes of its own**, logged in `docs/SUPERVISOR_LOG_V8.md` §6. The one worth reading is M2: the
invariance check summed a JSON key that does not exist, `.get(..., 0)` meant it did not raise, and it
computed "0 of 0" and reported a failure against a claim the text stated correctly. **A checker with a
default can pass while reading nothing**, which is worse than a missing check because it looks like
evidence. Rewritten with subscripts so a renamed field is a `KeyError`.

**Evidence that nothing else moved:** `results/` is byte-identical to the archive. 27/27 claims, unsafe
approvals 0/12, strict recall and precision 0.970, severity agreement 0.969, plans 12/12, gap cases
cleared 0/2, evidenced findings 35/35, 9.2 modelled min/case, 0 of 168 completed reviews changing the
decision surface, 12/12 packets reproducing through the browser driver. Nothing under `sentinel/`,
`eval/cases/`, `eval/scoring.py` or `memory/` was touched, and `tools/check_results.py` is unchanged,
so **"27/27" still means in v8 what it means in the video.** The counts that moved are all counts of
audits: tests 33 -> 38, documentation checks 5 -> 6, and 6 new submission-text checks.

**The lesson, one layer out from v7's.** v5: a defence audited in its own vocabulary reports on the
attacker's imagination. v7: a repository that audits only its measurements is audited only where it
already knows how to be wrong. v8: **every lossy transform on the way to your user needs a statement of
what has to survive it, or the transform decides for you and every gate upstream stays green.** The
repository was 27/27, 5/5 and 12/12 while the first paragraph a judge would read had lost the sentence
that makes all three worth anything. The pipeline does not end at the last component you wrote; it ends
at the last edit before a human reads it, and that edit is usually a person reformatting something
under a constraint your tests have never heard of.

**How to verify from a clean clone**

```bash
python -m unittest discover -s tests    # 38 tests
python eval/run_eval.py --ablations     # 108 reviews
python eval/model_invariance.py         # 180 reviews, 4 hostile models, 3 narrator modes
python tools/check_results.py           # 27/27 claims hold
python tools/check_docs.py              # 6 documentation checks, exits 1 on any failure
python tools/check_submission_text.py   # 6 checks on the description in the submission form
```

## v10 - the check nobody was required to read

**What I tried and why.** v8 committed the description a judge reads first and audited it with an exit
code. v9 read the field's own label, found the cap was 9,000 and not 10,000, and corrected it in two
files. Neither session then measured the shipped text against the number it had just corrected. The
committed description was **9,536 characters against a 9,000-character field**: the failure mode and
the hot take - the 5% rubric row, and the two paragraphs the whole project exists to earn - sat past
the edge of the field. `tools/check_submission_text.py` printed `FAIL` about it on every run, and the
one test guarding that checker asserted `6/6` while the checker ran seven checks, so a real failure and
a stale expectation cancelled into a suite that read `FAILED (failures=1)` and got scrolled past.

**What I did.** Cut the description to **8,897 characters** with every audited figure and all nine
load-bearing sentences intact, taking the length out of connective tissue and duplication rather than
out of claims. Then closed the class rather than the instance:

- the length check measures **twice** - as authored, and CRLF-normalised, because a form POST turns
  each of the 50 line breaks into two characters and the counter in the page does not. The first cut
  fitted the counter at 8,958 and would have shipped a 9,008-character POST body;
- the test stopped defending a release that no longer exists: 10,000 -> 9,000, plus the CRLF count, and
  the hardcoded `6/6` became the checker's own arithmetic;
- `docs/SUBMISSION.md` stopped being a **third** copy of the description. It held a v5-era variant,
  9,753 characters under a "10,000 limit" note, with a different title and the sentence "Twelve cases,
  one schema, ground truth I wrote" that the freight schema had made false two sessions earlier. It is
  now the submission mechanics only, pointing at the single audited copy;
- `JUDGE_START_HERE.md` and `docs/VIDEO_ADDENDUM.md` said "the repository is v5" and "33 tests, 27
  claims". Corrected to the current tree, with the held-out world added to the video correction table.

**Evidence that nothing else moved.** Unsafe approvals 0/12 in sample and 0/9 held out, strict recall
and precision 0.970, severity agreement 0.969, plans 12/12, gap cases cleared 0/2, evidenced findings
35/35, 9.2 modelled min/case, 0 of 168 completed reviews changing the decision surface, 0 of 60
headlines model-written. Nothing under `sentinel/`, `eval/cases/`, `eval/holdout/`, `eval/scoring.py`
or `memory/` was touched and `tools/check_results.py` is unchanged, so **44/44 means in v10 what it
meant in v9.** The counts that moved are counts of audits: submission-text checks 6 -> 7, and 52 tests
still pass with two of them no longer asserting the wrong numbers.

**The lesson, one layer out from v8's.** v8: every lossy transform on the way to your user needs a
statement of what has to survive it. v10: **a check whose failure nobody is required to read is a
comment, and a test that asserts your last release will hide your current one.** The transform that
truncated the most persuasive part of this submission was not lossy by design; it was a length limit,
measured in a unit no gate in this repository had ever used. Full reasoning, including the two rival
designs and the three mistakes in the first version of the fix:
[`docs/SUPERVISOR_LOG_V10.md`](docs/SUPERVISOR_LOG_V10.md).

**How to verify from a clean clone**

```bash
python -m unittest discover -s tests    # 52 tests
python eval/run_eval.py --ablations     # 108 reviews
python eval/run_holdout.py --ablations  # 9 held-out cases, three arms
python tools/check_results.py           # 44/44 claims hold
python tools/check_docs.py              # 6 documentation checks
python tools/check_submission_text.py   # 7 checks on the description in the form
```

---

## v11 - the guard that had not read this repository's own hot take

Session 09 unzipped the submitted v10 archive and could not make a number false: 52 tests, `44/44
claims hold`, `6/6` documentation checks, `7/7` submission-text checks, 12/12 packets, Python
3.12.13, offline, first attempt, 0.7 s for the whole evaluation. So a green suite was the starting
condition of the session rather than its result, and the question became what this repository
asserts that none of its five audits can read.

Three answers, and all three are the same defect class.

**1. The claim-count audit was written in its own vocabulary.** `tools/check_docs.py` matched the
literal shape `N/N claims`. `JUDGE_START_HERE.md` line 20 read:

```
python3 tools/check_results.py          # 27/27 published claims re-asserted from raw JSON
```

The command prints `44/44`. One adjective between the fraction and the noun, in the first file a
judge opens, for three releases, with a green `PASS  no stale claim count` sitting above it. This
is v5's lesson - *a defence audited in its own vocabulary reports on the attacker's imagination,
not on itself* - arriving as a bug report against the tool written to apply it. Iteration 10 fixed
the narrator with provenance and left the doc auditor holding the same bag.

**2. The size of an audit had no audit.** `6 checks on the description in the submission form` on
line 22, `Seven checks:` on line 94, one document, one tool, and the tool prints `7/7`. The README
called them "claims" instead of "checks", which is how the same drift hid from a second pattern.

**3. Nothing in 69 tests reads markdown structure.** `REPRODUCTION.md` was submitted missing one
closing fence at line 263, so from section 5a to the end - the human approval gate, the
hosted-model path, bring-your-own-migration, the review desk - every heading rendered inside a code
block and every command rendered as prose, on the document the 15% reproducibility row is scored
on.

**The fix is provenance again, not a longer list.** Every count is now read out of the tool that
owns it at run time, resolved by noun first and filename second; the pattern allows up to three
words between the number and its noun and understands word-numbers; and a stale figure is exempt
only where the line **dates itself** (`->`, `as of`, `was`, `v5`), so changelog rows and supervisor
logs stay honest records rather than whitelisted lies. Six documentation checks became seven: two
added, two merged into the one that resolves owners.

**And the rerun got a command instead of a promise.** Running the evaluation rewrites 80 files
under `results/`, which is an uncomfortable thing to hand a judge in a submission about verified
determinism. `tools/check_determinism.py` copies the repository to a temporary directory, reruns
every generator there, and diffs all 144 regenerated files back against the committed ones with
the wall-clock fields - each one named in the output - normalised: **0 decision differences**, 85
files byte-identical, 59 differing in three named fields. Its first run failed and named two
wall-clock fields its own permission list had missed, and `TestDeterminism` now asserts the
normaliser does *not* blur a verdict, a recall figure or the modelled reviewer minutes.

**Evidence that nothing else moved.** Unsafe approvals 0/12 in sample and 0/9 held out, recall
0.970 and 0.96, precision 0.970, severity agreement 0.969, plans 12/12 and 9/9, gap cases cleared
0/2, evidenced findings 35/35, 9.2 and 10.7 modelled minutes per case, 0 of 180 and 0 of 126
decision surfaces changed, 0 of 60 headlines model-written. Nothing under `sentinel/`,
`eval/cases/`, `eval/holdout/`, `eval/scoring.py` or `memory/` was touched and
`tools/check_results.py` is unchanged, so **44/44 means in v11 what it meant in v9.** The counts
that moved are counts of audits and tests: documentation checks 6 -> 7, tests 52 -> 69.

**The lesson, one layer out from v10's.** v10: a check whose failure nobody is required to read is
a comment. v11: **every honesty layer inherits the perimeter of the examples its author had when
they wrote it**, so the guard you are proudest of is the one most likely to be blind in exactly the
way you already published. The counter is not vocabulary, it is to stop typing the number twice.
Two perimeters of this fix are published rather than discovered: `Seven checks:` names no tool, so
nothing can own it and it was corrected by hand; and README line 11 said "27 published *numbers*",
which was rewritten to say *claims* so the audit could reach it - moving the prose into the audited
vocabulary rather than widening the audit into false positives. Full reasoning, the two rejected
designs and the self-review: [`docs/SUPERVISOR_LOG_V11.md`](docs/SUPERVISOR_LOG_V11.md); the trace
with all six rejected attempts:
[`agent_traces/session-09-supervisor-audit-the-auditor.md`](agent_traces/session-09-supervisor-audit-the-auditor.md).

**How to verify from a clean clone**

```bash
make verify                             # everything below, in one command
python -m unittest discover -s tests    # 69 tests
python eval/run_eval.py --ablations     # 108 reviews
python eval/run_holdout.py --ablations  # 9 held-out cases, three arms
python tools/check_results.py           # 44/44 claims hold
python tools/check_docs.py              # 7 documentation checks
python tools/check_submission_text.py   # 7 checks on the description in the form
python tools/check_determinism.py       # 144 files rerun and diffed, 0 decision differences
```

## v12 - the interpreter, the run id, and the audit's own docstring

An external supervisor pass over the v11 archive, in a separate context with no network, on the
standing instruction to critique first, propose radically different alternatives, write the findings
down, then execute. Everything the suite could see was green on the first attempt on **two**
interpreters, so the session went after the sentences instead.

| stage | what and why | evidence | decision |
|---|---|---|---|
| **F1: "3.11 and 3.12 verified" was never a claim about the numbers** | it meant the tests do not raise on either; nothing had compared the two `results/` trees, and dict ordering, float repr, `round`, `re` and the bundled `sqlite3` are all silent routes from an interpreter upgrade to a moved verdict | `tools/check_cross_version.py`: **146 files, 0 decision differences** on CPython 3.11.2 and 3.12.13; and the unflattering half as a claim - 64 files moved on timing alone, up to 7.1 ms | Kept. Two new claims, 44 -> 46 |
| **F2: the documented first command breaks the flagship reproducibility command** | `python3 -m sentinel review` writes into `results/` with an interactive run id, so a judge following the entry point in order gets a decision difference over a random hex string | reproduced, then diagnosed: the packet is byte-identical apart from its own run id | Fixed in `tools/` and the docs, not in `sentinel/cli.py`: the decision tree is frozen and a held-out attestation is worth more than a tidy fix |
| **F3: the counting tools misstated their own size** | `check_docs.py` said "Six checks" while running seven, `check_submission_text.py` said "Eight checks" while running seven, and a dead shadowed `_current_claim_count` sat in the file that audits stale duplication | 8th documentation check reads the three tools' own docstrings, with a quoted count treated as a citation | Kept, 7 -> 9 checks |
| **F4: four live statements declared v10 at v11** | including the first line of the video notice, whose only job is to say which artefact is newer | 9th check reads the version from the newest `docs/SUPERVISOR_LOG_V<N>.md` | Kept. The first draft exempted all four, because the sentence dates itself with the version of the video |

Tests 69 -> 82. No file under `sentinel/` touched; every decision number re-asserted after the
edits and none moved. Full log: [`docs/SUPERVISOR_LOG_V12.md`](docs/SUPERVISOR_LOG_V12.md).
