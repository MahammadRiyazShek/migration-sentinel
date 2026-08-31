# Session 10: supervisor pass over the v11 archive (cross-interpreter, run ids, self-description)

**Agent:** Claude Opus 5, conversational, separate context. **Given:** the v11 source archive as
submitted, the challenge brief and rubric. **Environment:** sandboxed shell, Python 3.12.13 and
3.11.2, **no network**. **Instruction:** critique the approach, generate radically different
alternatives, write the findings down before executing, then execute and do not hand the work back.

Full reasoning: [`docs/SUPERVISOR_LOG_V12.md`](../docs/SUPERVISOR_LOG_V12.md).

## Step 1 - reproduce before reading

```
$ python3 -m unittest discover -s tests -q          -> Ran 69 tests OK
$ make verify                                       -> 44/44 claims, 7/7 docs, 7/7 form text,
                                                       144 files compared, 0 decision differences
$ /usr/bin/python3.11 ... same four commands        -> identical results on CPython 3.11.2
```

Everything the suite can see was green on the first attempt, on both interpreters. So the target
became the sentences the suite cannot see.

## Step 2 - the tool response that started the session

Comparing the two interpreters' `results/` trees by hand, before any tool existed to do it:

```
identical (ignoring clock): 87
json diffs: results/case_05...json, results/evaluation.json, ...
-> every diff was /tool_calls[N]/ms, /wall_ms, /wall_ms_per_case
```

Decisions identical, timings not. That is a claim worth an exit code, and
`tools/check_cross_version.py` is that exit code. It also became the second, unflattering claim:
the published millisecond figures are the one thing in this repository that does not travel.

## Step 3 - the failure the documentation caused

Running the entry point's own suggested first command, then its flagship reproducibility command:

```
$ python3 -m sentinel review --case eval/cases/case_12_release_train.json --print-report
$ python3 tools/check_determinism.py
FAIL  1 file(s) differ beyond wall-clock: a decision is not deterministic
        case_12_release_train.json
          committed: "run_id": "run-5dd02ef1"
          rerun    : "run_id": "eval-case_12_release_train"
```

The review had overwritten a committed packet with its own run id. Human checkpoint here: the clean
fix is in `sentinel/cli.py`, which is inside the frozen decision tree, and touching it would turn
the held-out attestation's "three files changed since the freeze" into four. Rejected. Fixed in
`tools/check_determinism.py` (a preflight that names the cause and both fixes) and in the two
documents that suggest the command.

Verified afterwards that the packet was otherwise identical, so the diagnosis is true:

```
run ids: eval-case_12_release_train vs run-250f5ec4
identical ignoring run_id + clock: True     markdown identical: True
```

## Step 4 - the audits, pointed at themselves

```
tools/check_docs.py docstring          "Six checks"    while running 7
tools/check_submission_text.py         "Eight checks"  while running 7
tools/check_docs.py                    a dead, shadowed second _current_claim_count
JUDGE_START_HERE.md, SUBMISSION_*, docs/VIDEO_ADDENDUM.md   "the repository is v10", at v11
```

## Step 5 - the retry that matters

First draft of the version check reused `_is_dated`:

```
PASS  no live document declares an older release than the newest one   (0 statements)
```

Zero. The check passed on all four instances of the defect, because the defective sentence is *"The
submitted video was recorded against v2. The repository is v10"* - it dates itself with the version
of the video. Rewrote the exemption to cover quoted citations only, and fed the regression test that
exact sentence:

```
PASS -> FAIL  JUDGE_START_HERE.md:133 says 'repository is v10' ... (4 statements)
```

Then, one command later, the widened audit caught the supervisor's own prose: a sentence added to
`REPRODUCTION.md` in this session said `six checks` undated, and the audit flagged it. Corrected by
dating it. A check that catches its own author on the same afternoon is the only kind worth adding.

## Step 6 - close out

```
$ make verify
82 tests OK | 46/46 claims hold | 9/9 documentation checks | 7/7 submission-text checks
146 files compared, 0 decision differences | PASS on CPython 3.11.2 and 3.12.13
```

No file under `sentinel/` was touched. Every decision number re-asserted after the edits, not
before: none moved.
