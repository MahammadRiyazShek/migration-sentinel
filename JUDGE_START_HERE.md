# Judges start here

Migration Sentinel is a schema-migration review pipeline: five agents replay a migration against a
shadow copy of the schema and a real query corpus, write an expand/contract rollout plan, replay the
plan they just wrote, declare what they structurally could not observe, and render the verdict from
tool output so no model can write it.

**Zero pip dependencies. No API key. No network. Python 3.11+ (3.11 and 3.12 verified).
Whole evaluation is under a second and costs $0.00.**

---

## Sixty seconds, four commands

```bash
git clone https://github.com/MahammadRiyazShek/migration-sentinel && cd migration-sentinel
python3 -m unittest discover -s tests   # 52 tests, ~0.3 s
python3 eval/run_eval.py --ablations    # 108 reviews (12 cases x 9 arms), < 1 s
python3 eval/model_invariance.py        # 180 reviews, 5 models x 3 narrator modes, < 1 s
python3 tools/check_results.py          # 27/27 published claims re-asserted from raw JSON
python3 tools/check_docs.py             # 6 checks on what the docs claim about the repo
python3 tools/check_submission_text.py  # 6 checks on the description in the submission form
```

The fourth command is the one to run if you only run one. It reads `results/*.json` and re-asserts
every number in this repository, including the three that make the pipeline look worse.

---

## What each rubric row can be checked against

| rubric row | where it lives | the check |
|---|---|---|
| Problem & user value (15%) | `README.md` §Who has this problem, §The bottleneck | the user is one named person on a review rota, and the bottleneck is 20-40 min per PR against five PRs |
| Agent solution & engineering (30%) | `sentinel/agents/`, prompts in `sentinel/agents/prompts/`, `sentinel/orchestrator.py` | `results/ablation.md`: 9 arms, one component removed at a time. Replay alone is **worse** than rules alone (2 unsafe vs 1) |
| End to end quality (20%) | `results/case_12_release_train.md`, live desk below | `python3 -m sentinel review --case eval/cases/case_12_release_train.json --print-report` produces the packet a reviewer actually reads |
| Measured improvement (15%) | `results/comparison.md`, `README.md` §Improvement Changelog | 10 kept iterations, 3 removed experiments, 4 rejected designs, each row tied to an arm in `results/*.json` |
| Reproducibility (15%) | `REPRODUCTION.md` | clean clone to main result in four commands, no key, no network. `tools/check_docs.py` audits the documentation itself: no dangling file reference, no stale claim or test count, one entry point. `tools/check_submission_text.py` audits the description in the submission form, which is the one artefact that lives outside this repository |
| Hot take / insights (5%) | `README.md` §Hot take, `results/model_invariance.md` | the failure mode was found by writing an attacker against my own fix, not by removing a component |

---

## The headline numbers

| metric | Baseline A (one prompt) | Baseline B (prompt + schema) | Migration Sentinel |
|---|---|---|---|
| **Unsafe approvals** (primary) | 1/12 | 1/12 | **0/12** |
| **Blind-spot cases cleared without sign-off** (primary) | 0/2 | 0/2 | **0/2** |
| Hazard recall / precision | 0.545 / 0.947 | 0.606 / 0.690 | **0.970 / 0.970** |
| Severity agreement | 0.611 | 0.550 | **0.969** |
| Findings backed by machine evidence | 0/19 | 0/29 | **35/35** |
| Verified expand/contract plans | 0/12 | 0/12 | **12/12** |
| Misleading headline reaching the reviewer | n/a | n/a | **0/48** hostile reviews |
| Modelled reviewer minutes per case | 29.7 | 34.7 | **9.2** |

Same 12 cases, same hazard vocabulary, same scorer, same temperature on both sides. Only the
scaffolding changes.

Reviewer minutes is the **one modelled number** in that table, from four stated constants in
`eval/scoring.py`. It is published as a band instead of a point: `python3 eval/time_sensitivity.py`
recomputes every arm under six constant sets, three of them written to break the claim. The saving
holds at 69% under uniform rescaling and **reverses sign** under two adversarial sets. That reversal
is the coverage gate's bill and it is published as it fell out.

---

## Two things to read carefully rather than generously

**One number in this repo got worse on purpose.** The coverage gate costs +0.7 modelled reviewer
minutes per case (8.5 -> 9.2) and improves no detection metric. It is the only component whose
removal makes a published number look better, and `tools/check_results.py` asserts that fact rather
than hiding it. Every blind spot the ledger opens becomes a human gate, and a human gate costs time.

**Two ground-truth hazards are still missed, on purpose.** `case_09` hides the risky consumer in a
dbt model outside the query corpus. The pipeline still misses it, and no longer *clears* it: the
coverage ledger sees the shape of the hole without seeing what is in it, so the verdict caps at
`NEEDS_COVERAGE_SIGNOFF`. Twelve cases, one schema, ground truth I wrote by hand. Do not quote the
F1 without its denominator.

---

## The description in the form is committed here too

The form's Description field is plain text, so the verified `SUBMISSION_DESCRIPTION.md` - which
leads with a markdown table - cannot be pasted into it as written. That flattening is the one
edit in this submission that happens outside the repository, which means it was the one edit no
checker could see. So the exact text submitted to the form is committed verbatim as
[`SUBMISSION_FORM_TEXT.txt`](SUBMISSION_FORM_TEXT.txt) and audited:

```bash
python3 tools/check_submission_text.py
```

Seven checks: it fits 9,000 characters on both counts (as authored and CRLF-normalised), it is 7-bit ASCII with no markdown a plain-text field
would render literally, every headline / ablation / hostile-model figure in it is read back out
of `results/*.json` arm for arm, and nine named load-bearing sentences are still present and
still in position. `tests/test_all.py::TestSubmissionText` deletes each of those nine in turn
and asserts the audit fails, so none of them is a regex nobody is defending.

The first version of that text lost four of them, including the one command that proves every
number in the submission: [`docs/SUPERVISOR_LOG_V8.md`](docs/SUPERVISOR_LOG_V8.md). The next
version was 9,536 characters against a 9,000-character field, so the failure mode and the hot
take were past the edge of the form while this audit printed `FAIL` and nothing was required to
read it: [`docs/SUPERVISOR_LOG_V10.md`](docs/SUPERVISOR_LOG_V10.md).

---

## The video is older than the repo

The submitted video was recorded against v2. The repository is v10. The problem, architecture,
baseline comparison and walkthrough all still match; some on-screen numbers are stale and three
components (the coverage gate, the structural narrator and the held-out world) did not exist yet.

**Where the video and the repository disagree, `results/comparison.md` and
`results/model_invariance.md` are authoritative.** An exhaustive, line-by-line correction table is in
[`docs/VIDEO_ADDENDUM.md`](docs/VIDEO_ADDENDUM.md) - every stale number, what it moved to, and why.
A single-take script written against v5, for the re-record, is in
[`docs/VIDEO_SCRIPT_V5.md`](docs/VIDEO_SCRIPT_V5.md); the original v2 shot list is kept in
[`docs/VIDEO_SCRIPT.md`](docs/VIDEO_SCRIPT.md) because it is what the submitted video was made from.

---

## Human approval gates, on purpose

Review never touches a database. Execution runs in an in-memory SQLite sandbox and refuses:

```bash
python3 -m sentinel execute --case eval/cases/case_12_release_train.json --phase 1
# -> REFUSED: phase 1 execution requires --i-approve and --reviewer "name".
#    This is the human approval gate; the agent will not run DDL on its own authority.
```

It also refuses on a `BLOCK` without an explicit override, and on any uncleared coverage gap, each
with its own exit code. Three separate gates, all testable from the command line.

---

## Live review desk

<https://migration-sentinel-frvo.vercel.app/>

Every recorded packet, plus a button that boots the real Python package on WebAssembly CPython in
your tab and runs it on your own SQL. Nothing is uploaded. The page diffs itself against the recorded
packets at runtime rather than asserting it matches them.

---

## Where the agent instructions are

Five agents, fixed order, one prompt file each in `sentinel/agents/prompts/`:

| agent | job | prompt |
|---|---|---|
| Cartographer | parse the migration into an exact change set | `cartographer.md` |
| Blast Radius | execute the corpus against shadow pre/post schemas | `blast_radius.md` |
| Risk Officer | static rules, incident memory, coverage ledger, verdict | `risk_officer.md` |
| Rollout Engineer | write the expand/contract plan as executable SQL | `rollout_engineer.md` |
| Verifier | replay the plan, tighten policy, retry, escalate at 3 | `verifier.md` |

Development-agent trajectories are in `agent_traces/` with an index at `agent_traces/INDEX.md`;
per-case runtime trajectories are in `trajectories/`. Disclosure of which coding agents built what is
in `AGENT_USE.md`.
