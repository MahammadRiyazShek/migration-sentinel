# Session 09 - supervisor: audit the auditor, and prove the rerun

**Agent:** Claude Opus 5, ClickUp Brain agentic assistant. Fresh context, supervisor role.
**Given:** the v10 source archive as submitted (`migration-sentinel-source.zip`), the challenge
brief, the rubric and the submission form text.
**Tools:** one sandboxed Python 3.12.13 shell. **No network access. No `pip install`.**
**Instruction:** critique the approach, generate radically different alternatives, write the
findings down before executing, then execute. Do not hand the work back.

Full reasoning, the critique layer, the rejected variations and the self-review are in
[`docs/SUPERVISOR_LOG_V11.md`](../docs/SUPERVISOR_LOG_V11.md). This file is the trace.

---

## Step 1 - reproduce everything from the archive before touching it

```
$ python3 --version
Python 3.12.13

$ python3 -m unittest discover -s tests
Ran 52 tests in 1.738s
OK

$ python3 tools/check_results.py
44/44 claims hold

$ python3 tools/check_docs.py
6/6 documentation checks hold across 292 authored files

$ python3 tools/check_submission_text.py
7/7 submission-text checks hold

$ time python3 eval/run_eval.py --ablations
real 0m0.699s
```

**Feedback that shaped the next step.** Everything green, first attempt, offline, in under a
second. A green suite is therefore the *starting condition* of this session, not its result. Ten
sessions have audited the numbers, the packet prose, the documentation's claims and the form text.
So the question became: what does this repository assert that none of its five audits can read?

## Step 2 - the rerun, which is the first thing a judge does after reproducing

```
$ cp -r results /tmp/shipped && python3 eval/run_eval.py --ablations
$ diff -rq /tmp/shipped results | wc -l
80
```

Eighty files differ, in a submission whose pitch is that its numbers are re-derivable. Normalising
timestamps did not close it, so the diff was read field by field:

```
$ diff <(json_sorted /tmp/shipped/case_03...json) <(json_sorted results/case_03...json)
235c235
<    "ms": 0.68,
---
>    "ms": 0.64,
```

**Feedback.** Wall clock, all of it, and `check_results.py` is right to compare decisions instead.
But the only thing standing between a judge and that conclusion was my word for it. Logged as F7.

## Step 3 - read the docs as a judge, not as their author

`JUDGE_START_HERE.md` line 13 says "Sixty seconds, four commands" over a block of six. Line 20:

```
python3 tools/check_results.py          # 27/27 published claims re-asserted from raw JSON
```

The command prints `44/44`. And `check_docs.py` had passed:

```
$ python3 tools/check_docs.py | grep claim
PASS  no stale claim count in a current-state document
```

```
$ grep -n "CLAIM_COUNT = " tools/check_docs.py
161: CLAIM_COUNT = re.compile(r"\b(\d+)/(\d+) claims\b")
```

**Feedback, and the turn of the session.** The guard requires the noun immediately after the
fraction. `27/27 published claims` inserts one adjective and walks through. That is not a new
defect class - it is v5's, published in this repository's own hot take, reproduced inside the tool
written to apply it. The fix therefore could not be "correct line 20".

## Step 4 - widen the pattern, and let it report

First pass, loosened pattern, still per-file exemptions:

```
FAIL  no stale claim count in a current-state document
        JUDGE_START_HERE.md:20 says '27/27 published claims', the audit asserts 44
        README.md:549 says '27 claims', the audit asserts 44
        README.md:550 says '6 claims', the audit asserts 44
        README.md:552 says '6 claims', the audit asserts 44
```

**Feedback.** Rows 3 and 4 are not false positives and not claim counts either: the README calls
the two documentation audits' checks "claims", and one of them had drifted (6 against a tool that
prints 7). So a fourth quantity - the size of an audit - had no audit at all, and had already gone
stale inside one document: `6 checks` on line 22 against `Seven checks:` on line 94.

Second pass added owner resolution, by noun first and filename second:

```
$ python3 -c "...stale_counts_in_line(...)"
'# 27/27 published claims re-asserted'      -> [('27/27 published claims', 27, 44, 'check_results.py')]
'check_results.py (27 claims about the ...' -> [('27 claims', 27, 44, 'check_results.py')]
'check_submission_text.py  # 6 checks ...'  -> [('6 checks', 6, 7, 'check_submission_text.py')]
'claims 23/23 -> 27/27'                     -> []
'Seven checks: it fits 9,000 characters'    -> []
```

**Human checkpoint.** The dated-line exemption was proposed by the agent and accepted by the
operator over the alternative it replaced, an allow-list of line numbers. Allow-lists rot. The
last line above is a perimeter accepted on purpose and written into the log rather than papered
over.

## Step 5 - the defect no test could read

```
$ python3 - <<'EOF'   # headings that render inside a fence
REPRODUCTION.md:264 (fence opened 255): ### Step 7b: audit the description in the submission form
```

One missing ``` at line 263. From section 5a to the end of the file, headings render as code and
commands render as prose. **First draft of the check flagged 19 sites**, 18 of them shell comments
(`# -> REFUSED`) and one an intentional quoted `###` inside an untagged fence.

**Feedback.** 1 signal in 19 is a check that gets switched off by whoever owns it. Narrowed to
`##`-level headings inside *language-tagged* fences: 1 in 1.

## Step 6 - answer F7 with a command instead of a sentence

`tools/check_determinism.py`, first run:

```
FAIL  6 file(s) differ beyond wall-clock: a decision is not deterministic
        ablation.json
          committed: "wall_ms_per_case": 7.8,
          rerun    : "wall_ms_per_case": 9.8,
```

**Feedback.** The tool caught two wall-clock fields its own permission list did not name -
`wall_ms_per_case`, and a markdown table row labelled `(ms, measured)`. Both named explicitly
rather than absorbed by a wildcard, because a normaliser that blurs whatever annoys it will
eventually blur a verdict. Second run:

```
PASS  every decision byte in results/ survives a rerun; only wall-clock fields move
      144 files compared, 0 decision differences
```

`tests/test_all.py::TestDeterminism` then asserts the normaliser does *not* blur a verdict, a
recall figure or the modelled reviewer minutes.

## Step 7 - the form text pushed back

```
FAIL  the pasted description fits the form's plain-text field
        9012 characters once the browser normalises 49 line breaks to CRLF, over the form's
        9000 limit by 12: it fits the counter in the page and not the POST body
```

**Feedback.** Session 08's audit refused session 09's edit, on the stricter of the two counts,
for 12 characters. The sentence was shortened rather than the check relaxed. Final: 8990
CRLF-normalised, 10 spare.

## Step 8 - re-assert everything, after the edits rather than before

```
$ make verify
Ran 69 tests in 1.597s ... OK
44/44 claims hold
7/7 documentation checks hold across 294 authored files
7/7 submission-text checks hold
PASS  every decision byte in results/ survives a rerun; 144 files, 0 decision differences
```

Unsafe approvals 0/12 and 0/9, recall 0.970 and 0.96, plans 12/12 and 9/9, 9.2 and 10.7 modelled
minutes, decision surface 0/180 and 0/126. No decision metric moved, which is the claim this
session had to earn rather than assume.

## Retries and what they cost

| # | attempt | why it failed | what replaced it |
|---|---|---|---|
| 1 | correct the three stale numbers | leaves the guard that missed them exactly as blind - the v3-blocklist mistake verbatim | move the pattern, not the instances |
| 2 | audit the README wholesale | fails on the Improvement Changelog, where `claims 23/23 -> 27/27` is an honest record | exempt by the line's own tense, not by filename |
| 3 | per-file allow-list for changelogs | allow-lists rot, and this one would have needed an entry per release | the `DATED` rule |
| 4 | flag any heading inside any fence | 18 false positives out of 19 | language-tagged fences, `##`-level headings |
| 5 | normalise "any number next to a unit" | would have blurred a decision eventually | each wall-clock field named in a list a human can read |
| 6 | add the new tool to the form description | +12 characters over the CRLF limit | shorter sentence, check unchanged |

## Human checkpoints

1. **Before any edit**: findings F1-F7 written to `docs/SUPERVISOR_LOG_V11.md` and reviewed, so
   the execution followed a log rather than a mood.
2. **On the exemption rule**: dated-line tense accepted over a line-number allow-list.
3. **On scope**: the video is not re-recorded three hours before the deadline;
   `docs/VIDEO_ADDENDUM.md` remains the correction table, and that decision is published in the
   log next to the ones that were fixed.
4. **No secrets, no network, no live database** touched at any point. The sandbox had no network
   access to touch one with.
