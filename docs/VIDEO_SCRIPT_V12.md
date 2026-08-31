# Solution video, single take, v12 numbers

Every figure below is the current one, and every command is copy-pasteable into a terminal sitting
at the repository root. Target 4:40 of a 5:00 limit. One take, no editing: two windows (terminal and
editor/browser), 1080p, terminal font at 16pt or larger so a judge on a laptop can read a row.

**Before recording:** `make eval && make holdout && python3 tools/check_results.py` (expect
`46/46 claims hold`). Then leave the terminal at the repository root with a clear screen. Every
review below writes to `/tmp/desk`, on purpose, so the recording never touches the committed
evidence - and that is worth one spoken sentence, because it is the trap the reproduction guide
warns about.

---

## 0:00 - 0:25 | The problem, and whose problem it is

> "A two-line `ALTER TABLE` is either free or an outage, and the diff does not tell you which. This
> is for the platform engineer on the schema-migration review rota: one Postgres primary, a dozen
> services and a BI layer on it, migration PRs from teams that own the feature but not the database.
> A real review has to answer what the diff does not contain - which live statements touch this
> column, what reads `SELECT *` off the affected view, whether this lock survives 48 million rows.
> That is twenty to forty minutes of work on a five-minute budget, so review degrades into pattern
> matching on diff text. It catches the obvious `DROP COLUMN` and misses the `DROP VIEW` a worker
> reads every minute."

**On screen:** `eval/cases/case_11_swap_view_used_by_worker.json`, scrolled to the migration and
then to the query corpus.

## 0:25 - 0:55 | The simple baseline, run live

```bash
python3 baseline/baseline_review.py --case eval/cases/case_11_swap_view_used_by_worker.json \
    --variant prompt_with_schema --print-review
```

> "Baseline A is one model call on the diff. Baseline B is the same prompt plus the full DDL and the
> row counts - the obvious next move, and the stronger of the two. It writes confident prose. Not
> one sentence in it is backed by a query that ran, it produces no rollout plan I can execute, and
> across twelve cases the two baselines approve one migration that breaks production."

## 0:55 - 2:10 | One realistic execution, start to finish

```bash
python3 -m sentinel review --case eval/cases/case_11_swap_view_used_by_worker.json \
    --out /tmp/desk --trace-dir /tmp/desk --print-report
```

> "Five agents, fixed order. Cartographer parses the migration into an exact change set. Blast
> Radius materialises the pre and post schema in an in-memory SQLite sandbox and runs the real query
> corpus against both. Risk Officer applies the static rules, checks incident memory, and opens the
> coverage ledger. Rollout Engineer writes the expand/contract plan as executable SQL. Verifier
> replays the plan the Rollout Engineer just wrote - that is where the agency is, an agent checking
> another agent's work with a tool - and tightens the policy between attempts."

Scroll the packet in this order, naming what a reviewer gets:

1. **the hazards**, each with the statement that failed and the service that owns it: "this is not
   an opinion about a diff, it is a query that ran and broke";
2. **the coverage ledger**: "here is what the review structurally could not see. Any open gap caps
   the verdict at `NEEDS_COVERAGE_SIGNOFF` - not an approval, not executable, and it invents no
   hazard to get there";
3. **the phase-1 SQL and its verification**: "written by one agent, replayed by another, zero broken
   statements";
4. **the model commentary block, labelled "unverified prose, not evidence"**: "the headline above is
   rendered from tool output. The model explains; it never decides."

Then the human gate, live:

```bash
python3 -m sentinel execute --report /tmp/desk/case_11_swap_view_used_by_worker.json \
    --case eval/cases/case_11_swap_view_used_by_worker.json
# -> REFUSED: phase 1 execution requires --i-approve and --reviewer "name".
```

> "Review never touches a database. Execution runs in a sandbox copy and refuses without a named
> approving reviewer, refuses on a `BLOCK`, and refuses on an open coverage gap. Three gates, three
> exit codes."

## 2:10 - 2:50 | The comparison, same cases both sides

**On screen:** `results/comparison.md`.

> "Same twelve cases, same hazard vocabulary, same scorer, same temperature. Only the scaffolding
> changes. Unsafe approvals, the primary metric: one out of twelve for both baselines, zero for the
> pipeline. Hazard recall goes from 0.545 and 0.606 to 0.970, precision from 0.690 to 0.970.
> Findings backed by machine evidence: zero of nineteen and zero of twenty-nine, against thirty-five
> of thirty-five. Verified rollout plans: zero, zero, twelve of twelve. Modelled reviewer minutes:
> 29.7 and 34.7 against 9.2 - and modelled is the word, from four stated constants, which is why
> `eval/time_sensitivity.py` republishes every arm under six constant sets including the two where
> the saving reverses sign."

## 2:50 - 3:25 | What each component buys, and the one that made things worse

**On screen:** `results/ablation.md`.

> "Nine arms, 108 reviews, one component removed at a time. The result that shaped the design:
> replay alone is *worse* than rules alone, two unsafe approvals against one, because a lock hazard
> produces no failing query - replay-only waves through the 48-million-row index build. Execution is
> necessary, not sufficient. And the coverage gate is the only component whose removal makes a
> published number look *better*: 8.5 minutes against 9.2. It buys no detection metric at all. I
> kept it, because out of sample its removal costs an unsafe approval and lets three of seven
> blocking migrations reach a clean verdict."

> "The experiment I removed: drift alerts on additive column sets. The first version flagged any
> change to a `SELECT *` result set, additions included, so it fired on every `ADD COLUMN` case with
> no ground-truth hazard behind it. A reviewer who gets a HIGH for every added column stops reading
> the tool, and then its recall is zero whatever the table says."

## 3:25 - 4:00 | The held-out world

```bash
python3 eval/run_holdout.py --ablations
```

> "Twelve cases on one billing schema, where I wrote both the rules and the labels, is a number
> about me. So the decision tree was hashed before the held-out cases existed, and only then was a
> second world written: a freight schema, its own corpus, composite natural keys, no incident
> history. Nine cases, labelled from Postgres semantics, run once, no rule edits. Unsafe approvals:
> one of nine, one of nine, zero. Recall 0.52, 0.56, 0.96 - and 1.0 once you exclude the one label
> that sits outside the shared vocabulary on purpose, so no arm can name it."

> "Two things did not transfer, and both are in the repository. First contact called a
> `numeric(12,2)` to `numeric(8,2)` narrowing on 9.4 million invoices shippable, because the value
> scan ran over five seeded rows and refused nothing. And a `CREATE TRIGGER` outside the parser
> filed its coverage gap against the string `unknown`, in the component whose whole job is naming
> the object. Both fixed, both named, and those two cases are no longer held out - the other seven
> are."

## 4:00 - 4:25 | The models are not trying to help

```bash
python3 eval/model_invariance.py
```

> "Twelve cases, five models, three narrator modes: 180 reviews, four of the models hostile - a
> sycophant, an injector, a dead endpoint, and one written specifically to beat my own earlier fix.
> The decision surface changes in zero of 168 completed reviews. The prose did not hold: unguarded,
> the sycophant printed "safe to ship" under a `BLOCK` badge on eleven of twelve cases. I shipped a
> blocklist, then noticed the audit shared its regexes with the guard - so I wrote the attacker for
> that gap, and it walked straight through. The fix is provenance, not a longer list: misleading
> headlines reaching the reviewer went 36 of 48, to 13 of 48, to zero of 48, with zero headlines
> model-written."

## 4:25 - 4:40 | The one command, and the hot take

```bash
python3 tools/check_results.py      # -> 46/46 claims hold
```

> "Every number I just said is re-asserted from raw JSON by that one command, on a clean clone, in
> under a second, no key and no network - including five claims that make this pipeline look worse.
> Verification is a sensor with a specific blind spot, not a synonym for correctness. Every honesty
> layer has a perimeter drawn by the examples you had when you wrote it: my ledger knew the corpus
> was a sample of the consumers, and had never once thought about the fixture being a sample of the
> data. Ablations only remove what you already built - so change the world instead. Hash your rules,
> write a second schema, run it on a second interpreter, and publish what falls out."

---

## Notes for the recording

* If a command is slower than the script implies, that is the copy in
  `tools/check_determinism.py` or `tools/check_cross_version.py`; everything else is sub-second.
* Do not run `python3 -m sentinel review` without `--out` while recording: it rewrites a committed
  packet, and the determinism check will tell you so afterwards.
* If you have 20 spare seconds, spend them on `python3 tools/check_cross_version.py`: 146 files, 0
  decision differences across CPython 3.11 and 3.12, with the wall-clock delta published as the
  thing that is not portable. It lands better than another metric.
* The addendum in [`VIDEO_ADDENDUM.md`](VIDEO_ADDENDUM.md) stays authoritative until this script has
  actually been recorded and the submitted URL replaced.
