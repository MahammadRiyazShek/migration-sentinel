# Solution video: single-take script against v5

The submitted video was recorded against v2. This is the replacement, written against the repository
as it stands, so nothing on screen needs an addendum. Target **4:50** of a 5:00 limit.

`docs/VIDEO_SCRIPT.md` is kept as-is because it is what the submitted video was made from.
`docs/VIDEO_ADDENDUM.md` stays either way: it is the line-by-line diff for anyone who watches the old
one.

## Before you hit record

```bash
git clone https://github.com/MahammadRiyazShek/migration-sentinel && cd migration-sentinel
python3 eval/run_eval.py --ablations      # generates results/ and trajectories/
python3 eval/model_invariance.py --write
clear
```

Terminal left, editor or browser right. Font at 16pt or larger. No editing needed: every command
below finishes in under two seconds, so this records in one take.

Every number you say is on screen. If a number is not on screen, do not say it.

---

## 0:00 - 0:30 | The problem, on a real PR

**Show:** `eval/cases/case_01_rename_with_compat_view.json`, scrolled to the two migration statements.

> "A product engineer renames a column and updates the reporting view in the same migration. Two
> statements. It looks self-contained.
>
> To review it honestly I need to know which of the statements our services actually issue touch that
> column, whether anything reads `SELECT *` off that view, how big the table is, and who deploys the
> code that breaks. That is twenty to forty minutes. On a review rota, it gets five. So review
> degrades into pattern matching on diff text."

## 0:30 - 1:10 | The simple baseline, and the failure this exists to remove

**Run:**

```bash
python3 baseline/baseline_review.py --case eval/cases/case_01_rename_with_compat_view.json \
    --variant prompt_with_schema --print-review
```

> "The baseline is one prompt. It gets the migration, the full schema, the row counts, the rollback
> and the same hazard vocabulary the pipeline uses. It catches the rename. It does not catch that the
> profile page and the signup insert both stop working, because it cannot look that up. And there is
> no evidence behind anything it says."

**Run:**

```bash
python3 baseline/baseline_review.py --case eval/cases/case_11_swap_view_used_by_worker.json \
    --variant prompt_with_schema --print-review | head -20
```

> "Same baseline, different migration. `APPROVE`. That migration swaps out a view a worker reads every
> minute. One unsafe approval in twelve, and it is the one that pages someone at 3am."

## 1:10 - 2:30 | One realistic execution, start to finish

**Run:**

```bash
python3 -m sentinel review --case eval/cases/case_01_rename_with_compat_view.json --print-report
```

Walk the packet top to bottom, pausing on each:

* the **headline**: "Say this out loud - this sentence is rendered from tool output. No model wrote
  it. I will come back to why."
* the `BLOCK` banner and the **two reproduced failures**. Read one engine error aloud.
* the **silent one**: `q_bi_summary` still runs, but its column set changed - `full_name` removed.
  "Replay proves a statement still runs. It never proves it returns the same answer. That distinction
  is a hazard class here."
* the incident citation: `INC-2025-02`, recalled from `memory/incidents.jsonl`.
* the **phase 1 / phase 2 plan** with the code steps between the phases, and the rollback.
* **"what this review did not check"** - the coverage ledger.

**Show:** `trajectories/case_01_rename_with_compat_view.md`, scrolled to the retry.

> "This is the loop, and it is the part I would keep if I could only keep one. The Rollout Engineer's
> first plan swapped the view in phase one. The Verifier replayed the plan the Rollout Engineer had
> just written, and handed back: `q_bi_summary`, column set changed, `full_name` removed. Its own plan
> had the same bug as the migration it was reviewing. Policy tightened, plan regenerated, replayed
> again, sixteen of sixteen passing."

**Run:**

```bash
python3 -m sentinel execute --report results/case_01_rename_with_compat_view.json \
    --case eval/cases/case_01_rename_with_compat_view.json
# REFUSED
```

> "Review never touches a database. Execution runs in an in-memory SQLite sandbox and refuses three
> ways, each with its own exit code: no named approving reviewer, a BLOCK without an explicit
> override, or an uncleared coverage gap."

## 2:30 - 3:20 | The comparison, run on camera

**Run:**

```bash
python3 eval/run_eval.py --ablations
```

> "Three headline arms plus six ablation arms, twelve cases each. A hundred and eight reviews, under
> a second, no API key, no network, zero dollars."

**Show:** `results/comparison.md`.

> "Same twelve cases, same hazard vocabulary, same scorer, same temperature. Only the scaffolding
> changes.
>
> Unsafe approvals, the primary metric: one, one, **zero**. Recall point five four and point six one
> against **point nine seven**. Findings backed by machine evidence: zero of nineteen, zero of
> twenty-nine, **thirty-five of thirty-five**. Verified rollout plans: zero, zero, **twelve of
> twelve**.
>
> Two honest readings. Baseline B has *lower* precision than A - more context made it guess more,
> string-matching table names inside view bodies. And the second primary metric, blind-spot cases
> cleared, ties at zero of two across all three arms. That tie is the finding: the baselines get
> there by requesting changes on ten and eleven of twelve cases, including the one migration that is
> genuinely safe. They never clear a blind spot because they clear almost nothing.
>
> Reviewer minutes is the one modelled number in that table, from four constants you can read and
> disagree with in `eval/scoring.py`. Everything else is measured."

## 3:20 - 4:10 | Changelog: what helped most, what got worse, what I removed

**Show:** `results/components.md`.

> "The change that contributed most was pairing execution with static rules. Look at the replay-only
> row: **two** unsafe approvals, worse than rules alone at one. A lock hazard produces no failing
> query, so nothing breaks, so replay-only waves through a forty-eight-million-row index build.
> Execution is necessary and it is not sufficient.
>
> One row makes this pipeline look worse and I would defend it first. The coverage gate moves no
> detection number and costs zero point seven reviewer minutes per case. What it buys is a verdict
> that stops short of clean when the review has a blind spot on an object the migration touches.
> Remove it and one declared blind spot gets cleared anyway. And under two adversarial constant sets
> in `results/time_sensitivity.md`, it reverses the sign of my best number. That reversal is published
> as it fell out.
>
> The experiment I removed: my first drift check flagged any change to a `SELECT *` result set,
> additions included. It fired on every single `ADD COLUMN`. A reviewer who gets a HIGH for every
> added column stops reading, and a tool nobody reads has a recall of zero. It is a note in the
> trajectory now, not a hazard."

## 4:10 - 4:40 | The bug I only found by attacking my own fix

**Run:**

```bash
python3 eval/model_invariance.py
```

> "Twelve cases, five models, three narrator modes. A hundred and eighty reviews. Four of the models
> are not trying to help.
>
> The decision surface changes in **zero of a hundred and sixty-eight** completed reviews. The other
> twelve crashed, all with the narrator unguarded, on a model that returns an empty body.
>
> But the prose did not hold, and no decision-surface metric could see it. I shipped a blocklist over
> model text and measured zero misleading headlines. Then I noticed the audit shared its regexes with
> the guard: the number only reported what the blocklist already knew. So I wrote the attacker for
> that gap. `hostile-fluent` uses no banned phrase, no verdict token, no injection marker, and still
> tells the reviewer the change can ride the normal release train. It printed above a `BLOCK` badge on
> twelve of twelve cases while the column that was meant to catch it read zero.
>
> The fix is provenance, not a longer list. Thirty-six of forty-eight, to thirteen, to **zero**. Zero
> of sixty headlines written by a model."

## 4:40 - 4:50 | Failure mode, and the proof

**Run:**

```bash
python3 tools/check_results.py     # hold on: 27/27 claims hold
```

> "The failure mode is that the corpus is the world. Case nine's real risk is a dbt model that is not
> in the corpus. It is still missed - and no longer cleared, because the ledger sees the shape of the
> hole without seeing what is in it. Twelve cases, one schema, ground truth I wrote by hand. Do not
> quote the F1 without its denominator.
>
> A defence audited in its own vocabulary reports on the attacker's imagination, not on itself.
>
> Clone it. One command re-asserts every number you just saw from raw JSON. Twenty-seven of
> twenty-seven."

---

## If you have thirty seconds spare

Cut nothing. Add this over `python3 tools/check_submission_text.py`:

> "Including the description you read to get here. That one lives outside the repository, so it had no
> audit until it did."
