# Session 07 - supervisor pass on the v6 submission: attack the page before the numbers

**Interface:** separate context, no memory of building v1-v6. Given the v6 source archive, the
submission form text (title, description, video URL, uploaded source) and the challenge brief.
Sandboxed Python shell, **no network access**, no credentials, no `pip install`.
**Instruction given:** find the assumptions this submission does not know it is making, try to make its
claims false, then fix what breaks. Produce ready-to-use files, not a list of homework.
**Constraint given:** do not touch the twelve cases, the ground truth, the hazard vocabulary, the
scorer, the reviewer-minute constants or either primary metric. Any change that moves a detection
number is a bug in this pass.

Findings and reasoning: [`docs/SUPERVISOR_LOG_V7.md`](../docs/SUPERVISOR_LOG_V7.md). This file is the
working record: what was run, what came back, and what changed because of it.

---

## 1. Establish the baseline before touching anything

```
$ python3 --version
Python 3.12.13
$ python3 -m unittest discover -s tests -v | tail -3
Ran 33 tests in 0.259s
OK
$ time python3 eval/run_eval.py --ablations
... 9 arms x 12 cases = 108 reviews
real 0m0.732s
$ time python3 eval/model_invariance.py
... 12 cases x 5 models x 3 narrator modes = 180 reviews
real 0m1.624s
$ python3 tools/check_results.py | tail -1
27/27 claims hold
```

Every published number reproduced from the archive on the first attempt, including
*"every recorded packet in results/ matches a fresh reference run: 12/12"*. The `sentinel execute`
refusals fired as documented (no reviewer, `BLOCK` without override, uncleared coverage gap). So the
measurements are not the seam. Which raises the question the rest of this session is about: **what in
this submission has never been audited by anything?**

## 2. Look for claims that live outside `results/`

```
$ grep -rln "Â\|â€" --include=*.md .
./docs/SUPERVISOR_LOG_V6.md
./JUDGE_START_HERE.md
```

Four mis-decoded section signs, three of them in the rubric-map table of the page the submission text
tells judges to open first. 33 tests and 27 audited claims, and nothing in the repository reads prose.

```
$ ls *START_HERE*.md
JUDGE_START_HERE.md      JUDGES_START_HERE.md
$ grep -c "" JUDGE_START_HERE.md JUDGES_START_HERE.md
JUDGE_START_HERE.md:158
JUDGES_START_HERE.md:53
$ grep -rn "JUDGES\?_START_HERE" --include=*.md . | grep -v "^./JUDGE"
./docs/SUPERVISOR_LOG_V6.md:31: **Fix: `JUDGE_START_HERE.md`, four commands and a rubric-row map ...
```

Two pages titled "Judges start here", different command lists, different runtime claims ("under a
second" against "under 10 seconds", and "~4 s" for a harness measured at 1.6 s). Nothing references the
older one. The form text names the newer one.

```
$ python3 - <<'PY'   # every backticked path in every .md, does it exist
... MISSING: SUBMISSION_DESCRIPTION.md
PY
$ grep -n "SUBMISSION_DESCRIPTION" docs/SUPERVISOR_LOG_V6.md
101:**Files added:** `JUDGE_START_HERE.md`, `SUBMISSION_DESCRIPTION.md` (paste-ready form text),
```

A log announcing a file the archive does not contain. Same failure class as an index claiming a trace
that is not on disk, which `tools/collect_agent_traces.py` already refuses to do.

## 3. The generated document that argues with its own table

```
$ grep -n "reverses" results/time_sensitivity.md
16:| adversarial: cheap plan, dear gate | ... | -1.4 | -12% **(claim reverses)** |
17:| adversarial: reading dominates | ... | -1.4 | -5% **(claim reverses)** |
31:The reduction ... The sign never reverses, except in the flagged row, but that is the weaker claim ...
$ grep -n "never reverses" eval/time_sensitivity.py
181:        f"{len(rows_out)} constant sets. The sign never reverses"
```

The conditional was written when one set reversed. Session six's constants made it two and left the
sentence singular, so the worst number in the repository is reported by a paragraph that hedges about
it. Patched the generator to state the count and the consequence, then:

```
$ python3 eval/time_sensitivity.py --write && sed -n '31p' results/time_sensitivity.md
The reduction against the *better* baseline ranges from **-12%** to **69%** across 6 constant sets.
The sign reverses in **2 of 6 sets** (flagged in the table): under those constants a baseline is
*faster* than the pipeline, and the claim as written is false. And sign is the weaker test anyway ...
```

## 4. The fix: an audit with an exit code, pointed at prose

`tools/check_docs.py`, standard library, five checks. First run, against the repository as shipped (the
fifth check was added after step 5 below found a stale count by hand):

```
$ python3 tools/check_docs.py; echo "exit=$?"
PASS  no mis-decoded characters in authored text
FAIL  every path-shaped file reference resolves
        DEPLOY.md:12 references missing data/bundle.json
        docs/AGENT_TRAJECTORIES.md:18 references missing prompts/cartographer.md
        ... 9 total
PASS  exactly one judge entry point at the root
FAIL  paste-ready description exists and fits the form
        SUBMISSION_DESCRIPTION.md is referenced by docs/SUPERVISOR_LOG_V6.md but absent
exit=1
```

Eight of those nine reference failures are the checker's fault, not the documentation's: docs write
`prompts/cartographer.md` under a heading that already named `sentinel/agents/prompts/`. **Human
checkpoint here** - an audit that cries wolf gets ignored, which is worse than no audit. Resolver
loosened to accept a suffix match anywhere in the tree; the one genuinely unresolvable reference was
expanded in `docs/SUPERVISOR_LOG_V6.md` rather than excused in the checker.

```
$ python3 tools/check_docs.py; echo "exit=$?"
PASS  no mis-decoded characters in authored text
FAIL  every path-shaped file reference resolves
        SUBMISSION_DESCRIPTION.md:6 references missing docs/SUPERVISOR_LOG_V7.md
PASS  exactly one judge entry point at the root
        paste-ready description: 9587 of 10,000 characters
PASS  paste-ready description exists and fits the form
exit=1
```

It caught a forward reference in the file it was written to check, one minute after being written. Then
it caught its own author twice more: a non-English token in the paste-ready description, and a
slash-collapsed path inside `docs/SUPERVISOR_LOG_V7.md` itself.

```
$ python3 tools/check_docs.py | tail -2
4/4 documentation checks hold across 190 authored files
```

## 5. Regression pass after every edit

```
$ python3 -m unittest discover -s tests | tail -2
Ran 33 tests in 0.26s  OK
$ python3 eval/run_eval.py --ablations >/dev/null && python3 eval/model_invariance.py >/dev/null
$ python3 tools/check_results.py | tail -1
27/27 claims hold
$ python3 tools/check_docs.py | tail -1
4/4 documentation checks hold across 190 authored files
$ git status --short | wc -l   # nothing under sentinel/, eval/cases/, or the scorer
```

No detection metric moved, because nothing this session touched can move one. Files added:
`tools/check_docs.py`, `SUBMISSION_DESCRIPTION.md`, `docs/SUPERVISOR_LOG_V7.md`, this trace. Files
changed: `eval/time_sensitivity.py` (one generated sentence), `results/time_sensitivity.md`
(regenerated), `JUDGE_START_HERE.md` and `docs/SUPERVISOR_LOG_V6.md` (glyphs, one path, new commands),
`AGENT_USE.md`, `Makefile`, `REPRODUCTION.md`. File deleted: `JUDGES_START_HERE.md`, superseded and
referenced by nothing.
