# Migration Sentinel

**A review pipeline that runs your database migration against a shadow copy of your schema and your
real query corpus before a human ever approves it, then rewrites it as an expand/contract plan and
proves the first phase breaks nothing.**

Offline, deterministic, zero dependencies, sub-second for all 12 evaluation cases.

**Judging this? Start at [`JUDGE_START_HERE.md`](JUDGE_START_HERE.md)**: four commands, a
rubric-row map, and the two things in here to read carefully rather than generously. Two audits
with exit codes back everything below: `python3 tools/check_results.py` re-asserts all 46
published claims from raw JSON, and `python3 tools/check_docs.py` re-asserts the nine claims this
documentation makes about the repository itself.

**Live review desk:** <https://migration-sentinel-frvo.vercel.app/> (every recorded packet, plus a
button that boots the pipeline inside your browser and runs it on your own SQL). Nothing is uploaded:
the runtime is a WebAssembly CPython in the tab. Deploy your own copy in about two minutes with
[`DEPLOY.md`](DEPLOY.md).

---

## Who has this problem

The person this is built for: **the platform or data engineer who is on the review rota for schema
migrations** at a company somewhere between 20 and 300 engineers. One Postgres primary, a dozen
services and a BI layer reading it, and a migration PR arriving a few times a week from a product
team that owns its feature but not the database.

They open a PR that says:

```sql
ALTER TABLE customers RENAME COLUMN full_name TO name;
CREATE OR REPLACE VIEW customer_billing_summary AS SELECT id, email, name, ... FROM customers;
```

Two statements. The author has already thought about it: they updated the reporting view in the same
migration, so it looks self-contained.

## The bottleneck

To review that honestly, the reviewer has to answer questions that are not in the diff:

1. Which of the ~14 statements our services issue today touch `customers.full_name`? (grep across
   repos, dbt models, notebooks, admin tooling)
2. Does anything read `SELECT *` off that view, so the column set matters and not just the SQL?
3. How big is the table, and does that turn this index build into a write stall?
4. Is there data in there right now that will not survive the change?
5. Who deploys the code that breaks, and does the schema change or the code change land first?
6. Have we already had an outage from this exact pattern?

Answering all six by hand takes 20 to 40 minutes per PR. It usually gets 5. So reviews degrade into
pattern matching on the diff text, which catches the obvious `DROP COLUMN` and misses the
`DROP VIEW` that a worker reads every minute. The cost is not a bad code review; it is a
half-applied deploy at 3am with a half-built index and no rollback.

Solving it is valuable because the evidence needed for a correct answer already exists in machine
readable form (the DDL, the query corpus, the row counts, the incident log). Nobody has time to
assemble it by hand for every PR.

## What Migration Sentinel does

One command per PR:

```bash
python3 -m sentinel review --case eval/cases/case_01_rename_with_compat_view.json
```

It produces a review packet ([example](results/case_01_rename_with_compat_view.md)) containing:

* every hazard, with the **engine's own error text** as evidence, not a model's opinion
* the blast radius: which statements, owned by which services, break or silently change shape
* a **rewritten expand/contract plan** in executable SQL, with a rollback, whose phase 1 has been
  replayed against the whole query corpus and proven not to break anything
* the decisions the tool refuses to make for you (dedupe rules, truncation rules, cutover windows)
* an explicit list of what it did not check
* a human approval gate before anything is executed, even in the sandbox

## The review desk

[`site/`](site/) is the review packet as a page, and the only new thing in it is the runtime: the
same `sentinel` package, mounted into Pyodide and executed in the reader's tab.

* Twelve recorded packets, each with its hazards, its shadow-replay evidence, its verified
  expand/contract plan, its trajectory and the baseline review of the same migration.
* **Boot the engine** loads CPython 3.12 on WebAssembly, mounts the 38 files listed in
  `site/py/manifest.json` and imports `sentinel` from there. No API key, no backend, no upload.
* **Run this case live** calls the same `orchestrator.review` the CLI calls, then diffs the result
  against the packet recorded in `results/`: same verdict, same hazards at the same severities, same
  phase-1 SQL, same verification outcome. The page states the diff either way, so a reader can catch
  the site drifting from the repository without taking my word for it.
* The migration SQL is editable. Paste your own `ALTER TABLE` and you get a real review of it, minus
  the ground-truth scoring, because there is none for your migration.
* `site/data/bundle.json` and `site/standalone.html` are generated by `tools/build_site.py` and
  `tools/build_artifact.py` from `results/`, so the page cannot quote a number the harness did not
  produce. `tools/check_results.py` asserts the headline claims and gates the deploy.

```bash
make verify   # eval + ablations + assert every claim in this README
make site     # regenerate site/data, site/py and the single-file copy
make serve    # build the site and open http://localhost:8000
python3 tools/test_browser_driver.py   # the desk's own driver, 12/12 parity with results/
```

## Results

12 cases, same inputs, same hazard vocabulary, same evaluation code for both sides.
Full table: [`results/comparison.md`](results/comparison.md). Raw scores:
[`results/evaluation.json`](results/evaluation.json).

| metric | Baseline A (one prompt) | Baseline B (prompt + schema) | Migration Sentinel |
|---|---|---|---|
| **Unsafe approvals** (primary) | 1/12 | 1/12 | **0/12** |
| **Coverage-gap cases cleared without a sign-off** (primary) | 0/2 | 0/2 | **0/2** |
| Hazard recall (exact code) | 0.545 | 0.606 | **0.970** |
| Hazard precision (exact code) | 0.947 | 0.690 | **0.970** |
| Severity agreement | 0.611 | 0.550 | **0.969** |
| False alarms on the clean case | 1 | 1 | **0** |
| Findings backed by machine evidence | 0/19 | 0/29 | **35/35** |
| Blind spots named in the packet, with the object | 0 | 0 | **3** |
| Verified rollout plans produced | 0/12 | 0/12 | **12/12** |
| Reviews whose facts a hostile model changed | n/a (the model *is* the reviewer) | n/a | **0/168** |
| Misleading headline reaching the reviewer (48 hostile reviews) | n/a | n/a | **0/48** (v3 blocklist: 13/48 · v2: 36/48) |
| Modelled reviewer minutes per case | 29.7 | 34.7 | **9.2** |
| Wall clock per case (measured) | 0.1 ms | 0.1 ms | ~8 ms |
| Model tokens, all 12 cases | 5,837 | 11,577 | 25,967 |

There are **two** primary metrics, and the second one is new in v2. Unsafe approvals is the outcome
the on-call engineer cares about. Coverage-gap cases cleared without a sign-off is the outcome that
metric cannot see: a review that says "ship as plan" directly above its own declared blind spot has
not made an unsafe approval by the letter of the scorer, and has still told a reviewer the wrong
thing. Both baselines score 0 on it, and that is not a virtue - they score 0 because they request
changes on 12 of 12 cases, so they never clear anything. They also name **zero** blind spots, which
is the row underneath. `results/comparison.md` reports all of it.

Reviewer minutes are **modelled** from four stated constants in `eval/scoring.py`
(`read_review=5`, `verify_unevidenced_claim=4`, `write_expand_contract_plan=20`,
`decide_human_gate=3`), not measured with a stopwatch. Everything else is measured by the harness.

Because `tools/check_results.py` re-asserts that claim from the same constants that produce it, the
audit cannot fail, so the claim is also reported as a band:
[`results/time_sensitivity.md`](results/time_sensitivity.md), regenerated with
`python3 eval/time_sensitivity.py`. The reduction holds at 71-72% under any uniform rescaling of the
constants and at 63% when checking an unevidenced claim is priced at one minute. It **reverses**,
to -12% and -5%, under one specific ratio: pricing a hand-written expand/contract plan at 6 minutes
against 6 minutes to approve a generated one. So the load-bearing assumption is not that reviewers
are slow, it is that writing a staged plan from scratch costs several times more than approving one
that has already been replayed. That is a belief about reviewers, not a measurement, and it is the
one I would attack first.

In v1 those two adversarial rows collapsed the advantage to about 1%. In v2 they reverse its sign,
and the reason is the coverage gate: every blind spot it opens becomes a human gate, so it buys
reliability in exactly the currency this table measures. The first instinct was to reprice
`decide_human_gate_minutes` and make the reversal go away. That would have been hiding a result in
the one file whose entire purpose is to stop me hiding results, so the number is published as it
fell out and `tools/check_results.py` now asserts that the coverage gate costs reviewer minutes
rather than saving them.

The primary metric is deliberately **unsafe approvals**, not F1: the reviewer's real failure is
saying "ship it" to something that breaks production.

### Which component actually does the work

From [`results/ablation.md`](results/ablation.md), same cases, one component removed at a time:

| configuration | unsafe approvals | recall | precision | severity | verified plans | gaps cleared | min/case |
|---|---|---|---|---|---|---|---|
| full | **0/12** | 0.970 | 0.970 | 0.969 | 12/12 | **0/2** | 9.2 |
| no shadow replay (rules only) | 1/12 | 0.576 | 1.000 | 0.947 | 0/12 | 0/2 | 23.3 |
| no static rules (replay only) | **2/12** | 0.333 | 1.000 | 1.000 | 12/12 | 0/2 | 8.8 |
| no incident memory | 0/12 | 0.970 | 0.970 | 0.938 | 12/12 | 0/2 | 9.2 |
| no plan verification | 0/12 | 0.970 | 0.970 | 0.969 | **0/12** | 0/2 | 23.3 |
| no coverage gate (= v1) | 0/12 | 0.970 | 0.970 | 0.969 | 12/12 | **1/2** | 8.5 |
| no rule inventory (= v12) | 0/12 | 0.970 | 0.970 | 0.969 | 12/12 | 0/2 | 9.2 |
| no parse conservation (= v13) | 0/12 | 0.970 | 0.970 | 0.969 | 12/12 | 0/2 | 9.2 |

Oriented as the cost of removing each component, with the same table generated from raw scores by
`python3 eval/report_components.py --write`: [`results/components.md`](results/components.md).

Five readings, including the four that do not flatter the design.

**The last two arms move nothing here, and that is what they are for.** `no_rule_inventory` (v12
behaviour) and `no_parse_conservation` (v13 behaviour, retired splitter included) are byte-identical
to `full` on every case in this table, and on all 28 labelled cases across the three sets. An
ablation can only remove what you already built, so a layer that costs nothing on the cases you
labelled is invisible to this table by construction - which is why both were found by an adversarial
pass instead, and why their prices are published on `eval/redteam` and `eval/redteam2` rather than
hidden in a row of unchanged numbers.

**Execution alone is worse than rules alone** on the primary metric (2 unsafe approvals vs 1),
because a lock hazard produces no failing query, so a replay-only reviewer says "nothing broke, ship
it". The two layers cover disjoint failure classes, and merging them is the single biggest
contribution in the changelog.

**The verifier is worth nothing to detection and everything after it.** Every hazard metric is
identical with it removed; verified plans go 12/12 -> 0/12 and modelled reviewer minutes go 8.5 ->
23.3. Judged on detection alone it looks decorative. It is the change a reviewer notices most.

**Incident memory is the thinnest component here.** It moves severity agreement 0.938 -> 0.969 and
nothing else: exactly one severity, on the one case in twelve that is a recurrence. That is a
statement about the case set as much as about the component, because one recurrence in twelve cases
is all it can possibly move. It is reported rather than folded into "orchestration" and left for
someone else to discover.

**The coverage gate is the only component that makes the pipeline look worse on a published
number.** It moves no detection metric at all - recall, precision, severity and unsafe approvals are
byte-identical with it removed - and it *adds* 0.7 modelled reviewer minutes per case, because every
blind spot it opens is a decision a person has to make. What it buys is the one thing the other four
cannot: `case_09` stops coming back "ship as plan" above its own declared gap. Removing the gate is
the v1 behaviour, and the v1 behaviour clears one.

### Can the model move any of this? (v3, and what v5 found in v3)

Worth stating plainly, because "the primary metric is invariant to the model by construction" is a
boast and an indictment in the same sentence. If no published number can be moved by changing the
model, then no published number is evidence about a model.

v2 made that claim from the shape of the code and never tried to break it. v3 tried, with three
models that are not trying to help. v5 attacked v3's own defence with a fourth.
[`eval/model_invariance.py`](eval/model_invariance.py) now runs 12 cases x 5 models x 3 narrator
modes = **180 reviews** in a few seconds for $0. Full table:
[`results/model_invariance.md`](results/model_invariance.md).

The narrator modes are the three answers this project has given to "who writes the sentence a
reviewer reads first":

| mode | who writes the headline | shipped in |
|---|---|---|
| `off` | the model, printed unchecked | v2 |
| `pattern` | the model, unless a blocklist in `sentinel/narrator.py` rejects it | v3 |
| `structural` | the tools, always, on every run and every model | **v5, the default** |

Totals over the 48 hostile reviews per mode (4 hostile models x 12 cases):

| narrator mode | decision surface changed | run crashed | **misleading headline reached the reviewer** | v3 pattern audit flagged it |
|---|---|---|---|---|
| `off` (v2) | 0/48 | **12/48** | **36/48** | 23/48 |
| `pattern` (v3) | 0/48 | 0/48 | **13/48** | **0/48** |
| `structural` (v5) | 0/48 | 0/48 | **0/48** | 0/48 |

Four readings. The first is the claim; the second and third are bugs this repo shipped and then
published.

**The facts hold, and that is now measured.** Zero of 168 completed reviews differ from the
cooperative reference on verdict, hazards, severities, evidence, coverage ledger, generated SQL,
verification outcome or attempt count. The decision surface is produced by tools in
`sentinel/tools/` and `sentinel/coverage.py`; the model cannot reach it. The 12 crashes are all
`hostile-null` with the narrator off, which is the v2 code path.

**The prose did not, and no v2 metric could see that.** The model still wrote the sentence at the
top of the packet - the one a reviewer reads before the table - and v2 copied it in unchecked. A
sycophantic model prints *"Approved: no hazards found, safe to ship. LGTM"* directly above a `BLOCK`
on 11 of 12 cases (the twelfth is `case_06`, the genuinely clean one, where the flattery is
accidentally true). So v3 treated model output as untrusted input:
[`sentinel/narrator.py`](sentinel/narrator.py) rejects a summary that is empty, over-long, carries
injection text, names a verdict other than the computed one or asserts the change is clean above a
verdict that is not.

**And v3's `0/12` was a fact about the attacker's vocabulary, not about the defence.** The guard's
audit and the guard's enforcement used the same regexes, so the metric could only ever report what
the blocklist already knew. v5 wrote the model that exploits exactly that: `hostile-fluent` produces
a paragraph with no banned phrase, no verdict token and no injection marker in it -

> *"Reviewed this change set against the engine output. What it surfaces is the ordinary consequence
> of an evolving schema, and the owning team has already sequenced their deploy around it, so this
> can ride the normal release train."*

— and the v3 guard printed it above a `BLOCK` badge on **12 of 12** cases while the v3 audit
column read **0**. The metric said the guard held. The reviewer read a lie.

**v5's fix is provenance, not a longer blocklist.** In the shipped `structural` mode the headline is
a pure function of tool output on every run, for every model, whether or not its prose looks
acceptable: `narrator.render_headline` writes the verdict sentence from the counts, the broken
statements, the coverage gaps and the plan-verification result. "Does the guard know this wording"
stops being a question that can be asked. The model's prose is not discarded - it is demoted to
*Model commentary (unverified prose, not evidence)* at the **end** of the packet, after the reader has
met the nine hazards it is inviting them to ignore, and only if it still passes the guard. Model-
written headlines across all five models: **0 of 60**. Every detection metric is byte-identical,
because the narrator never touched one.

What v5 still does not fix, stated where it can be checked: reviewer questions and that demoted note
are still only pattern-guarded, so `hostile-fluent`'s two plausible questions do print, labelled as
model prose, below the evidence. The exposure is bounded by placement and provenance instead of by
vocabulary. Rendering the questions from the hazard codes too is the next experiment, and it is named
in `sentinel/narrator.py` rather than in a slide.

The agency is still in the loop, and the loop is what the ablations measure: which tool each agent
reaches for, the Verifier replaying the plan the Rollout Engineer just wrote, the policy tightening
between attempts, the retry budget, and the escalation to a human when it runs out. `case_01` needs
exactly two attempts and the retry is triggered by a real regression the first plan introduced. The
narrator is a narrator, is labelled as one, and is now audited like one.

## Red team: the half that labels cannot test

`eval/cases` asks whether the pipeline finds the hazards I thought of. `eval/holdout` asks whether it
finds them on a schema the rules were never written against. Neither can ask whether there is a class
of hazard **nobody enumerated**, because both were labelled from the same hazard vocabulary. So the
last pass ran the opposite brief: find a migration a Postgres primary calls an outage and this
pipeline calls SAFE. Six probes, two hits, and neither hit was a wrong rule - both were absent rules
nothing in this repository was counting.

| metric | Baseline B | Sentinel v12 | Sentinel v13 |
|---|---|---|---|
| **Unsafe approvals** (primary) | 1/7 | 3/7 | **0/7** |
| **Blocking cases given a clean verdict** | 1/3 | 3/3 | **0/3** |
| False alarms on the two correct migrations | 4 | 0 | **0** |
| Findings backed by machine evidence | 0/8 | 0/0 | **4/4** |

* **`DROP INDEX` on a 48M-row table three live statements filter by.** Every statement still
  executes, so shadow replay is silent - the hazard is in the plan, not the result - and no static
  rule mentioned `drop_index`. v12 verdict: SAFE, zero hazards, zero declared gaps.
* **`CONCURRENTLY` inside `BEGIN`/`COMMIT`.** Postgres refuses it and every migration framework
  opens that transaction by default. The parser saw both statements and no rule correlated them,
  because no rule here had ever looked at two statements at once. v12 verdict: SAFE - and on this one
  the **text-only baseline wins**, because `BEGIN` plus `CONCURRENTLY` in one file is a famous
  string. It is published rather than left out.
* **The ledger was an allow-list of known unknowns.** Every gap class was keyed to a statement kind
  some rule already handled, so it could only declare blind spots about objects something had already
  looked at. [`sentinel/rulebook.py`](sentinel/rulebook.py) now partitions all 26 statement kinds the
  parser can emit into RULED, REPLAY_COVERED, LEDGERED and RESIDUAL; a test fails if the parser
  learns a kind nobody classified, and a residual kind opens a gap rather than inventing a hazard.

**Read the generalisation number first.** These seven cases are in sample - the rules were written
from these probes. The evidence that the layer was *missing* rather than *retuned* runs the other way
and is computed per case by `eval/run_redteam.py`: `no_rule_coverage` reproduces v12 exactly and is
identical to `full` on **21 of 21** labelled cases in `eval/cases` and `eval/holdout` - same
verdicts, same hazards, same severities, same gap counts.

Two experiments this pass removed, both recorded in `sentinel/rulebook.py` rather than deleted:
default-deny (it flagged `case_06`, the cry-wolf canary, because "no hazard was produced" is
indistinguishable from "nothing looked" if you only count hazards) and a bare `drop_index` blocker
(it blocked the commonest correct index migration there is, since a B-tree on `(customer_id, status)`
still serves a lookup on `customer_id`).

Full report: [`results/redteam.md`](results/redteam.md). Reasoning:
[`docs/SUPERVISOR_LOG_V13.md`](docs/SUPERVISOR_LOG_V13.md).

## Red team, round 2: the parse is a sample of the text

Round 1 asked whether a hazard class was unenumerated. The fix,
[`sentinel/rulebook.py`](sentinel/rulebook.py), is an exhaustive partition of every statement kind
the parser can emit, with a test that fails when it learns a new one. Exhaustive over the **op
list**. So the next pass asked whether the op list is the migration.

```sql
UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL;
ALTER TABLE invoices DROP COLUMN tax_rate;
```

Two statements in. One op out. `strip_comments` deleted from the `--` inside the string literal to
end of line, the unterminated quote that left swallowed the rest of the file, and the `DROP COLUMN`
that breaks a live billing query was never presented to a rule, to shadow replay, or to the coverage
ledger. Not missed. Not there.

| metric | Baseline B | Sentinel v13 | Sentinel v14 |
|---|---|---|---|
| **Hazard recall** (primary) | 0.375 | 0.25 | **0.75** |
| **Hazard precision** (primary) | 0.25 | 0.222 | **1.0** |
| False alarms on the three correct migrations | 3 | 2 | **0** |
| Findings backed by machine evidence | 0/12 | 17/17 | **6/6** |
| Modelled reviewer minutes per case | 33.0 | 21.0 | **11.3** |

Read the v13 column twice. Seventeen findings, every one citing machine evidence, at 0.222
precision. **Evidence is not the same property as being about the right file.**

* **The statement loss.** Legal Postgres, ordinary human copy, and it costs the v13 parser the
  second half of the file. Across these six cases the retired splitter loses 2 statements outright
  and invents 6 that Postgres never executes - recomputed from the retired code itself by
  `parse_audit.legacy_loss`, not asserted.
* **DDL inside `DO $$ ... $$`.** The idempotency guard every migration generator writes. The
  retired splitter had no concept of dollar quoting and shredded the body at its inner semicolons.
  `procedural_block` is now its own op kind, and `rt2_02` is labelled with all three hazards a
  Postgres reviewer would name - two of which the pipeline **still cannot find**, because a keyword
  census over a procedural body is not a parse. Published recall on that case is 1 of 3. What
  protects the reviewer is that the case is not cleared.
* **The same defect with the sign flipped.** Postgres nests block comments; a non-greedy regex does
  not. v13 **blocked a migration whose destructive statement is commented out**, citing a broken
  query and a cross-service hazard, both evidenced, both about text that never runs. `rt2_04` and
  `rt2_06` carry no hazard at all and stay in the set as canaries.

**Read the generalisation number first.** These six cases are in sample. The evidence that the layer
was *missing* rather than *retuned* runs the other way and is computed per case by
`eval/run_redteam2.py`: `no_text_conservation` reproduces v13 exactly, retired splitter included,
and is identical to `full` on **28 of 28** labelled cases in `eval/cases`, `eval/holdout` and
`eval/redteam` - same verdicts, same hazards, same severities, same gap counts. A splitter swapped
out underneath 28 labelled cases without moving one number is a splitter that was wrong only where
nothing had ever looked.

Two experiments this pass removed, both recorded in the modules rather than deleted. Reporting the
wreckage: the first version raised the unterminated-literal blocker *and* the two hazards inferred
from the mangled remainder, which is `rt2_04`'s defect in the opposite direction - a script Postgres
refuses now reports only that it is refused, worth precision 1.0 against 0.6. And censusing the raw
source, which turned `RAISE NOTICE 'about to drop table invoices'` into a destructive finding; every
census now runs over literal-masked scanner output, with a test for the notice.

Full report: [`results/redteam2.md`](results/redteam2.md). Reasoning:
[`docs/SUPERVISOR_LOG_V14.md`](docs/SUPERVISOR_LOG_V14.md).

## Architecture

Five agents, fixed order, one feedback loop. Instructions for each are in
[`sentinel/agents/prompts/`](sentinel/agents/prompts/).

```
                    +-------------------------------------------------+
 migration + DDL -> | 1 Cartographer      parse -> exact change set   |
 query corpus       | 2 Blast Radius      dependents + shadow replay  |
 row estimates      | 3 Risk Officer      locks, volume, intent, memory,
 incident log       |                     coverage ledger -> verdict cap
                    | 4 Rollout Engineer  expand/contract plan in SQL |
                    | 5 Verifier          replay the plan  <--retry---+
                    +-------------------------------------------------+
                                   |
                     review packet + human approval gate
```

Design choices that mattered, and why:

* **Tools decide facts, the model writes prose.** Hazards, severities and the plan are produced by
  code in `sentinel/tools/`. The model writes the summary, the per-hazard explanation and the
  reviewer questions. Swap the model and the primary metric cannot move, only the wording.
* **A shadow database instead of a prediction.** Two throwaway SQLite databases (pre and post
  schema), seeded with fixture rows, every corpus statement executed against both. A hazard quotes
  `OperationalError: no such column: full_name`, so a reviewer can stop arguing with it.
* **Column-set diffing, not just pass/fail.** The nastiest real failure is the query that still
  runs and returns different columns. Tests stay green; the dashboard goes wrong for three weeks.
* **Static rules next to execution.** SQLite has no MVCC and the fixtures are tiny, so locks and
  volume are covered by explicit rules over the parsed ops and declared row counts. Documented as
  rules, not dressed up as measurements.
* **Exact-key memory, and it only ever raises severity.** `memory/incidents.jsonl` is a curated
  incident log. Recall is by (hazard code, table), so there is no similarity threshold to tune.
  Memory can raise a high to a blocker and must cite the incident id. It can never clear a hazard,
  because surviving something once is not evidence of safety.
* **The plan is verified, not suggested.** The Verifier re-parses the generated SQL with the same
  parser and replays it. If phase 1 still breaks something, the failure text goes back to the
  Rollout Engineer, which tightens its policy and regenerates. After three attempts it escalates to
  a human instead of shipping a plan it cannot prove.
* **A declared blind spot caps the verdict.** `sentinel/coverage.py` computes, per affected object,
  what this review structurally could not observe: statements the parser never modelled, rows
  rewritten in place (replay proves a statement still *runs*, never that it still returns the same
  *answer*), a value class erased in a way the rollback does not restore, and pre-existing columns no
  corpus statement touches. Any open gap caps `SAFE`/`SAFE_WITH_PLAN` at `NEEDS_COVERAGE_SIGNOFF`,
  which is not an approval in the scorer and not executable in the CLI. `BLOCK` is left alone; the
  cap can only stop a verdict from being clean, never make one safer. It invents no hazard: absence
  of evidence becomes a named human decision, not a finding with a severity.
* **The verdict sentence is not the model's to write.** The line a reviewer reads before the table is
  rendered from tool output on every run (`sentinel/narrator.render_headline`): counts, broken
  statements, coverage gaps, plan-verification outcome. The model's prose is kept and demoted to
  *Model commentary (unverified prose, not evidence)* at the end of the packet, after the evidence it
  might be inviting the reader to ignore, and only if it still passes the prose guard. v3 defended
  that line with a blocklist and a model that lies in ordinary professional English walked through
  it; provenance is checkable without anything having to judge meaning, which a blocklist is not.
* **Nothing consequential happens without a person.** `sentinel review` never touches a database.
  `sentinel execute` runs phase 1 against an in-memory sandbox copy only, refuses without
  `--i-approve --reviewer "name"`, refuses a `BLOCK` verdict unless a named reviewer overrides it on
  the record, and refuses an uncleared coverage gap the same way.

## Quickstart

Python 3.11+ and nothing else. No pip install, no API key, no network.

```bash
python3 eval/build_cases.py                                   # regenerate the 12 cases
python3 -m sentinel cases                                     # list them
python3 -m sentinel review --case eval/cases/case_12_release_train.json --print-report
python3 eval/run_eval.py --ablations                          # everything, ~1 second
python3 eval/model_invariance.py                              # 180 reviews: 5 models x 3 narrator modes
python3 -m unittest discover -s tests -v                      # 129 tests
python3 tools/check_results.py                                # 67/67 claims, from raw JSON
python3 tools/check_docs.py                                   # 9 checks on the docs themselves
python3 tools/check_submission_text.py                        # 7 checks on the submission form text
python3 tools/check_cross_version.py                          # the same diff on a second interpreter
make serve                                                    # the review desk, locally
```

`python3`, spelled out, because a stock macOS has no `python` on the path and the first command a
judge runs should not be the one that fails. A review writes its packet into `results/` by default:
pass `--out /tmp/desk` for an ad-hoc run, or `make eval` afterwards, so the committed evidence stays
the harness's. `tools/check_determinism.py` explains that in its own output if you forget.

Full walkthrough from a clean machine, including the hosted-model path:
[`REPRODUCTION.md`](REPRODUCTION.md).

## What existed before this project, and what I built

**Pre-existing:** Python 3.12 standard library only (`sqlite3`, `re`, `dataclasses`, `argparse`,
`unittest`, `urllib`). The expand/contract migration pattern is prior art from the industry, not my
idea. `zero-downtime migration` lint tools exist in the wild (squawk, strong_migrations); I did not
use or copy them, and the comparison here is against a prompt, not against them.

**Built for this challenge (all of it, from scratch):** the Postgres-subset parser and schema model,
the shadow-replay engine, the query-corpus dependency tool, the incident-memory tool, the five agent
instruction sets and their implementations, the orchestrator with the verify/retry loop, the report
renderer, the CLI with the approval gate, the model layer (scripted stand-in, hosted providers,
cassette replay), the 12 evaluation cases and their ground truth, the scorer, the ablation harness
and the tests. For the web deliverable: the review desk (`site/index.html`, hand-written, no
framework), the bundle and single-file builders, the claim checker and the Pages workflow.
Pyodide is pre-existing (Mozilla, MPL-2.0) and is loaded from its CDN, unmodified.

**Data:** entirely synthetic. A fictional SaaS billing schema, fictional customers with
`example`-domain emails, invented incident log, invented row counts. No customer data, no
credentials, nothing scraped. `memory/incidents.jsonl` is fiction written to look like a real
postmortem index.

## Coding agents used to build this

Required disclosure. Full version, including the human checkpoints and the honest gaps, in
[`AGENT_USE.md`](AGENT_USE.md).

**Claude Opus 5 (Anthropic)** was the coding agent for this project, used conversationally rather
than through an autonomous CLI harness: I set the design, it wrote code, I ran the eval and pushed
back. Everything in `sentinel/`, `eval/`, `site/`, `tools/` and `tests/` was written that way.

What was **not** delegated, and the reason: the twelve cases and their ground-truth hazard sets
(`eval/cases/`), the hazard vocabulary and severity ladder (`sentinel/hazards.py`), the scorer
(`eval/scoring.py`) and the choice of unsafe approvals as the primary metric. An agent that writes
both the solution and its own grading criteria has graded itself, and every number in this README
would be worth nothing.

Development traces are indexed in [`agent_traces/INDEX.md`](agent_traces/INDEX.md), generated by
`python3 tools/collect_agent_traces.py` from the files actually present rather than listed by hand.
These are separate from the runtime traces of the five agents that run *inside* the tool, which are
in [`trajectories/`](trajectories/) and [`docs/AGENT_TRAJECTORIES.md`](docs/AGENT_TRAJECTORIES.md).

## Improvement Changelog

Iterations 1 to 6 are below. The later ones (v2.1 submission hardening, v3 narrator guard, v5 structural provenance, v7 documentation audit, v8 submission-form audit, v10 the check nobody was required to read) continue in [`CHANGELOG_ADDENDUM.md`](CHANGELOG_ADDENDUM.md), each with the same evidence columns. The held-out session is [`docs/SUPERVISOR_LOG_V9.md`](docs/SUPERVISOR_LOG_V9.md) and the form-field session is [`docs/SUPERVISOR_LOG_V10.md`](docs/SUPERVISOR_LOG_V10.md).

Every row's evidence is an arm in `results/evaluation.json` or `results/ablation.json` and can be
reproduced with the commands in `REPRODUCTION.md`. Same 12 cases and same scorer throughout.

Iterations 7 and 8 came out of a hostile re-read of the finished v1 submission, logged in
[`docs/CRITIQUE_LOG.md`](docs/CRITIQUE_LOG.md) with the two alternative designs I rejected and the
three mistakes I caught in the first version of the fix. The ground truth, the hazard vocabulary and
the scorer were **not** touched in v2; only the pipeline and the metric set changed, so every v1 and
v2 number in this file is comparable.

| stage | what I tried and why | evidence | decision / learning |
|---|---|---|---|
| **Baseline A** | One model call. Migration file plus its rollback, the shared hazard vocabulary, "be exhaustive". This is what "let's use AI for migration review" means in most teams. | unsafe approvals **1/12**, recall **0.545**, precision 0.947, severity agreement 0.611, evidence 0/19 findings, plans 0/12 | Starting point. It catches everything visible in the diff text and nothing that requires a lookup. It approved a `DROP VIEW` that a worker reads every minute. |
| **Baseline B** | Obvious next move: give it more context. Same prompt plus the full DDL and the row counts. | family recall 0.636 -> **0.864**, but strict precision 0.947 -> **0.690**; unsafe approvals unchanged at 1/12 | Kept as the harder baseline, not as a direction. More context made it *guess more*: it started flagging `VIEW_BREAKAGE` on nine cases by string-matching table names in view bodies. Context without the ability to check the context buys volume, not accuracy. |
| **Iteration 1: structure it** | Replace prose with a parser: exact change set, static rules for lock/volume/intent hazards, severity scaled by declared row counts. No execution yet. (`no_replay` arm) | unsafe **1/12**, recall 0.545, precision **1.000**, severity 0.944 | Kept. Precision went perfect, and severities became defensible because they cite a row count. But recall stalled: rules cannot know who reads `full_name`. |
| **Iteration 2: execute it** | Opposite bet: drop the rules, add the shadow database. Materialise pre/post schema, seed fixtures, run the corpus against both. (`no_static` arm) | unsafe **2/12** (worse than iteration 1), recall 0.333, precision 1.000 | The result that shaped the whole design. Execution finds only what fails, and a lock hazard fails nothing, so replay-only *approves* the 48M-row index build and the unvalidated foreign key. Execution is necessary, not sufficient. |
| **Iteration 3: both layers, merged** | Run both, merge hazards on (code, objects), keep the higher severity, mark the source `replay+static` when both fired. (`no_memory` arm) | unsafe **0/12**, recall **0.939**, precision 0.969, severity 0.935 | Kept, and this is the single biggest contribution. Two layers with disjoint blind spots beat either one, and merging keeps the report short instead of double-reporting. |
| **Iteration 4: incident memory** | Add exact-key recall over a curated incident log; memory may raise a severity and must cite the incident id. | verdicts unchanged, severity agreement 0.935 -> **0.968** (one case: the 48M-row foreign key becomes a blocker because INC-2024-11 was exactly that) | Kept, but honestly: it changed no verdict. I nearly cut it. It stays because severity is what decides whether a change waits for a maintenance window, and "this exact thing burned us in November" is the argument a reviewer actually acts on. Small, measurable, cheap. |
| **Iteration 5: verify the plan** | Detection was good but the output was still homework. Generate an expand/contract plan as executable SQL, then re-parse and replay it. On failure, feed the error back and tighten the policy; escalate after 3 attempts. | verified plans 0/12 -> **12/12**; detection metrics unchanged; case_01 needs exactly one retry, and the retry is triggered by a real regression (the phase-1 view swap removed `full_name` from the BI column set) | Kept. This did not improve detection at all and is still the change a reviewer would notice most, because it removes the 20 minutes of writing the staged plan by hand. |
| **Removed: drift alerts on additive column sets** | The first drift check flagged any change to a `SELECT *` result set, additions included. | fired on every `ADD COLUMN` case, no ground-truth hazard behind it | Removed. Now a note in the trajectory, not a hazard. A reviewer who gets a HIGH for every added column stops reading the tool, and then the tool's recall is zero regardless of what the table says. |
| **Removed: separate view-probe hazards** | Views bind lazily in SQLite, so I probe each view directly. Those probes emitted their own hazards. | case_11 reported both `VIEW_BREAKAGE` (probe) and `BREAKING_QUERY` (the worker that reads the view): strict precision 0.939 | Removed by folding the probe into the corpus statement that reads the view: precision 0.939 -> **0.969**. Same failure, one owner, one line. |
| **Fixed after a near miss** | The first column parser used a greedy `[\w ]+` for types, which swallowed `NOT NULL UNIQUE` into the type name of the column. | `ADD COLUMN x TEXT NOT NULL` parsed as nullable, so the `NOT_NULL_NO_DEFAULT` hazard silently disappeared | Rewrote the type pattern explicitly and pinned it with `tests/test_all.py::TestParser`. Worth logging because it is the scariest class of bug here: a parser that fails silently makes the whole pipeline confidently wrong, and no metric would have moved much. |
| **Iteration 6: put it where the reviewer is** | The packet was a markdown file in a repository, which means it is read by whoever already cloned the repository. Shipped the same pipeline as a static review desk that boots CPython on WebAssembly and runs the real package in the reader's tab. | detection metrics unchanged by construction (same code path, `orchestrator.review`); `tools/test_browser_driver.py` runs the page's own driver string under CPython against site/py/ and reproduces **12/12** recorded packets (verdict, hazard codes with severities, phase-1 SQL, verification); the page repeats that diff at runtime for whatever it just ran; deploy is gated on `tools/check_results.py`, 44/44 claims at that iteration (23/23 today) | Kept. No new dependency in the pipeline and no fork of the logic: a second implementation in JavaScript was the obvious alternative and would have been a second thing to keep correct. The failure mode I care about here is a demo that quietly disagrees with its own repository, so the page diffs itself instead of asserting it matches. |
| **Iteration 7: the gap has to constrain the verdict** | v1's own stated limitation, and the sharpest finding of the hostile re-read (`docs/CRITIQUE_LOG.md`, C1). `case_09` returned `SAFE_WITH_PLAN` - which the packet renders as "SHIP AS PLAN" - directly above a declared blind spot, and scored a clean 0 on the primary metric while missing a real hazard. The metric could not see it, because the verdict ladder had no rung for *I did not see enough to say*. Added a machine-computed coverage ledger (`sentinel/coverage.py`) over four gap classes, a `NEEDS_COVERAGE_SIGNOFF` verdict that caps `SAFE`/`SAFE_WITH_PLAN` and can never be an approval, one human gate per gap, and a new metric that is a property of the *case* rather than of the arm. (`no_coverage` arm reproduces v1 exactly) | gap cases cleared without a sign-off **1/2 -> 0/2**; every detection metric byte-identical (recall 0.970, precision 0.970, severity 0.969, unsafe 0/12); modelled reviewer minutes **8.5 -> 9.2**; `case_09` verdict `SAFE_WITH_PLAN` -> `NEEDS_COVERAGE_SIGNOFF` with `invoices.currency` named as irreversible; `case_06` still `SAFE` with zero gaps; `sentinel execute` now refuses an uncleared review with exit code 4 | Kept. It is the only component in the ablation that makes the pipeline look **worse** on a published number, and it is the change I would defend hardest: absence of evidence is recorded as a decision for a person, never as a finding with a severity, so the cap invents no hazard and costs no precision. The cost is real and published - see the sensitivity note above, where two adversarial constant sets now reverse the time claim's sign instead of merely collapsing it. |
| **Iteration 8: name the whole-relation rewrites** | `case_12` hid `CLUSTER invoices USING idx_invoices_customer` outside the parser's model, and v1 missed `TABLE_REWRITE_LOCK` there by construction. `CLUSTER`, `VACUUM FULL`, `REINDEX` and `REFRESH MATERIALIZED VIEW` are a documented family that all take `ACCESS EXCLUSIVE` for the duration, so this is a rule about a class and not a patch for one case. | strict recall **0.939 -> 0.970** (32/33), F1 0.954 -> 0.970, `case_12` goes from one missed hazard to none, evidenced findings 34 -> 35; rules-only arm also improves, 0.545 -> 0.576 | Kept, with the trap logged in `docs/CRITIQUE_LOG.md` (M2). The tempting implementation gives these statements a real op kind, which quietly removes them from the unmodelled list and trades a truthfully reported blind spot for a detection point. `maintenance_rewrite` is a member of `UNMODELLED_KINDS` instead: the hazard is reported *and* the statement stays in the coverage ledger, because being able to name a statement is not being able to model it. Pinned by a test. |
| **Iteration 9: the narrator is untrusted input** | The sharpest finding of the second hostile re-read (`docs/SUPERVISOR_LOG_V3.md`, A1). v2 proved no model can move a verdict and never asked what a model *can* move: the headline sentence and the reviewer questions, which is everything a human reads before the hazard table. So I wrote three models that are not trying to help (`sentinel/llm/adversarial.py`) and an invariance harness that diffs the decision surface field by field (`eval/model_invariance.py`), then put a guard on the two places model text enters the packet (`sentinel/narrator.py`). | decision surface **0/84** changed across 12 cases x 4 models x guard on/off at the time (0/168 over 180 reviews today) - the v2 invariance claim became a measurement instead of an argument from code shape; misleading headlines **23 of the 24 unguarded hostile reviews that ran -> 0/36 guarded**, a number iteration 10 shows was measured against the attacker's vocabulary; `hostile-null` crashed **12/12** unguarded runs and **0/12** guarded; every detection metric byte-identical (recall 0.970, precision 0.970, severity 0.969, unsafe 0/12, plans 12/12, 9.2 min/case) | Kept. Two things came out of it that no removal-style ablation could have. First, the guard only ever *removes* model text, so it cannot buy a detection point - and the harness publishes that it does not. Second, `.payload.get("questions")` on a raw model response meant a degraded endpoint was an outage, not a degraded review: v2 had no metric that could even express availability. Ablations subtract components that behave correctly; they never test one behaving badly. |
| **Iteration 10: take the headline away from the model** | Iteration 9 shipped a blocklist and wrote its own limit into `sentinel/narrator.py`: the audit uses the same regexes as the guard, so `0/36` measured what the blocklist already knew. So I wrote the attacker that exploits precisely that gap. `hostile-fluent` writes prose with no banned phrase, no verdict token and no injection marker in it, and still tells the reviewer the change can ride the normal release train. Then I replaced the defence rather than extending the list: the headline is now a pure function of tool output (`narrator.render_headline`) on every run, the model's prose is demoted to a labelled *Model commentary* section at the end of the packet, and the harness counts **provenance** - who wrote the sentence above the badge - instead of asking a regex whether it liked the wording. Three modes (`off`, `pattern`, `structural`) all still run, so each defence has a price. | the v3 guard printed the fluent liar above a `BLOCK` on **12/12** cases while the v3 audit column read **0/12** - the metric said the guard held and the reviewer read a lie; misleading headlines reaching the reviewer over 48 hostile reviews per mode: **36/48 (v2) -> 13/48 (v3 blocklist) -> 0/48 (v5)**; model-written headlines **0 of 60** across all five models; decision surface **0/168** completed reviews of 180; every detection metric byte-identical again (recall 0.970, precision 0.970, severity 0.969, unsafe 0/12, plans 12/12, 9.2 min/case); tests 27 -> 33, claims 23/23 -> 27/27 | Kept. The lesson is not "regexes are weak", it is that **a defence audited in its own vocabulary reports on the attacker's imagination, not on itself**. Provenance is checkable without a language model in the loop: either the bytes came from a tool or they did not. What it does *not* fix is published in the same table - the reviewer questions and the demoted note are still pattern-guarded, so the fluent liar's two plausible questions still print, below the evidence and attributed to the model. The exposure is bounded by placement now, not by vocabulary, and the next experiment is named in the module rather than in a slide. |
| **Iteration 11: audit the auditor, and prove the rerun** | An external supervisor pass over the submitted archive, on the assumption that everything the suite can see is already green - it was: 52 tests, `44/44 claims`, `6/6` docs, `7/7` form text, 12/12 packets, first attempt, offline. So the session went looking for what no audit could see, and found the repository's own hot take pointed back at it. `tools/check_docs.py` asserted "no stale claim count" against the literal phrase `N/N claims`, so `JUDGE_START_HERE.md` line 20 advertised **`27/27 published claims`** for a command that prints 44 - one adjective, in the first file a judge opens, for three releases. The size of an *audit* had no audit at all, so `6 checks` and `Seven checks` sat 70 lines apart in one document about one tool that prints 7. And `REPRODUCTION.md` was missing one closing fence at line 263, so from section 5a to the end - approval gate, hosted-model path, review desk - headings rendered as code and commands rendered as prose, invisible to a suite in which nothing reads markdown structure. Fix: every count is read out of the tool that owns it at run time, the pattern is loose (up to three words between the number and its noun, word-numbers included), and a stale figure is exempt only where the line **dates itself** - so changelog rows like this one stay honest records instead of whitelisted lies. Plus `tools/check_determinism.py`, because rerunning the evaluation rewrites 80 files under `results/` and "trust me, it is only the timings" is the exact sentence this project exists to refuse. | the widened audit found **6 stale counts** in live documents, 4 of them in the two files a judge reads first, and 1 trapped heading; determinism, measured rather than asserted: **144 files compared, 0 decision differences**, 85 byte-identical, 59 differing in three named wall-clock fields; every decision metric unmoved and re-asserted after the edits, not before - unsafe approvals 0/12 and 0/9, recall 0.970 and 0.96, plans 12/12 and 9/9, 9.2 and 10.7 min/case, decision surface 0/180 and 0/126; tests 52 -> 69, docs checks 6 -> 7 (two added, two merged into one owner-resolving check), claims 44/44 unchanged | Kept. The lesson is the v5 lesson arriving as a bug report against the tool that was supposed to have learned it: **a guard audited in its own vocabulary reports on the author's imagination**, and an honesty layer inherits the perimeter of the examples its author had. So the counter was not a longer list of phrasings, it was to stop typing the number twice. Two perimeters are published rather than discovered: `Seven checks:` names no tool, so nothing can own it and it was fixed by hand; and README line 11 said "27 published *numbers*", which I rewrote to say *claims* so the audit could reach it - moving the prose into the audited vocabulary rather than widening the audit into false positives. The first draft of the fence check fired 18 times to catch 1 defect, and a check that cries wolf gets switched off by whoever owns it. |
| **Iteration 12: change the interpreter, and read the documentation in the order a stranger would** | A second external supervisor pass over the submitted archive, same standing instruction, and everything the suite can see was green on the first attempt on *two* interpreters - so the session attacked the sentence rather than the suite. "3.11 and 3.12 verified" meant *the tests do not raise on either*, and nothing in eleven releases had ever compared the two `results/` trees; dict ordering, float repr, `round`, `re` and the bundled `sqlite3` are all routes from an interpreter upgrade to a moved verdict, and none of them raises. So `tools/check_cross_version.py` reruns all four generators under both interpreters in private copies and diffs the trees, raw then wall-clock-normalised. Then it followed `JUDGE_START_HERE.md` in the order it is written and broke the flagship reproducibility command: `python3 -m sentinel review` writes its packet into `results/` with the run id it mints for an interactive run, so `check_determinism.py` reports a decision difference over a random hex string on a packet that is otherwise byte-identical. Then it read the audit tools themselves: `check_docs.py` announced "Six checks" while running seven, `check_submission_text.py` announced "Eight checks" while running seven, a dead shadowed `_current_claim_count` sat inside the file that audits stale duplication, and three live documents said "the repository is v10" at v11 - including the first line of the video notice, whose only job is to tell a judge which artefact is newer. | **146 files compared, 0 decision differences** across CPython 3.11.2 and 3.12.13 (`results/cross_version.md`), with the unflattering half published as a claim rather than a footnote: 64 files moved on timing alone, up to 7.1 ms absolute in the recorded run, so the decisions are portable and the milliseconds never were. The provenance preflight reproduces the failure and then diagnoses it, with both fixes printed. Claims 44 -> 46, documentation checks 7 -> 9, tests 69 -> 82; no file under `sentinel/` touched, so the freeze still names the same three post-freeze files, and every decision number was re-asserted after the edits rather than before - unsafe approvals 0/12 and 0/9, recall 0.970 and 0.96, plans 12/12 and 9/9, 9.2 and 10.7 min/case, decision surface 0/180 and 0/126 - none moved. | Kept, and two decisions in it are worth more than the checks. The run-id trap was fixed with **documentation and a diagnosis instead of code**, because `sentinel/cli.py` sits inside the frozen decision tree and spending a held-out attestation on a documentation defect is a bad trade. And the first draft of the version check **exempted all four instances of the bug it was written for**, because the defective sentence dates itself with the version of the video: the third generation of this repository's own hot take, which is why the regression test feeds it that exact sentence. Full log: [`docs/SUPERVISOR_LOG_V12.md`](docs/SUPERVISOR_LOG_V12.md). |
| **Iteration 13: the rule set is a sample of the hazards** | Both labelled sets were written from one hazard vocabulary, so neither could ask whether a class of hazard was unenumerated. So the pass ran the opposite brief - find a migration a Postgres primary calls an outage and this pipeline calls SAFE - and probed statement *kinds* rather than hazards. Two hits in six probes, both absent rules rather than wrong ones, plus the finding underneath them: every gap class in the ledger was keyed to a kind some rule already handled, so it could only declare blind spots about objects something had already looked at. | red-team set: unsafe approvals **3/7 -> 0/7**, blocking cases cleared **3/3 -> 0/3**, false alarms 0; on the 21 labelled cases in `eval/cases` and `eval/holdout` **nothing moved** - same verdicts, hazards, severities and gap counts, computed per case rather than asserted; cost 1.7 modelled reviewer minutes per case | Kept. Two removed experiments are in `sentinel/rulebook.py` rather than in a commit message: default-deny flagged `case_06`, the cry-wolf canary, because "no hazard was produced" is indistinguishable from "nothing looked" if you only count hazards; and a bare `drop_index` blocker blocked the commonest correct index migration there is. On `CONCURRENTLY` inside a transaction the **text-only baseline beat the pipeline**, which is published rather than left out. |
| **Iteration 14: the parse is a sample of the text** | Iteration 13's inventory is exhaustive over the op list, and the op list is a lossy function of the file. `strip_comments` deleted from `--` to end of line inside string literals too, so `'usd -- legacy default'` left an unterminated quote that swallowed the rest of the migration: a two-statement file arrived as one `dml_update` and the `DROP COLUMN` was never presented to a rule, to replay or to the ledger. Fix: a real scanner (`sentinel/tools/sql_lex.py` - `''` and `E'\''` escapes, `$tag$` bodies, **nested** block comments, spans, unterminated constructs as facts) plus the subtraction that catches the next one (`sentinel/tools/parse_audit.py`: statements the scanner finds, minus statements an op accounts for). | round-2 set: recall **0.25 -> 0.75**, precision **0.222 -> 1.0**, false alarms **2 -> 0**, modelled minutes **21.0 -> 11.3**; the retired splitter loses 2 statements and invents 6, recomputed from the retired code; `no_text_conservation` reproduces v13 exactly and is identical to `full` on **28 of 28** labelled cases; tests 104 -> 129, claims 57 -> 67 | Kept, and the unflattering number is the one to read: every false finding in the v13 packet **cited machine evidence**. `rt2_04` is the canary - v13 blocked a migration whose destructive statement is inside a nested comment. Two experiments removed: reporting the hazards inferred from a script Postgres refuses (precision 1.0 against 0.6), and censusing raw source, which read `RAISE NOTICE 'about to drop table invoices'` as destructive. Full log: [`docs/SUPERVISOR_LOG_V14.md`](docs/SUPERVISOR_LOG_V14.md). |
| **Iteration 15: the last edit was never verified** | A third external supervisor pass, aimed at the archive rather than the pipeline: does the tree a judge downloads still pass the command its own front page tells them to run? It did not. `make verify` exited **1** on a tree where all 67 claims still held, because two files had been hand-edited after the last green run and nothing re-ran: `SUBMISSION_DESCRIPTION.md` had been overwritten with the flattened paste text, deleting the `<!-- PASTE BELOW THIS LINE -->` marker so that its length stopped being measurable, and `SUBMISSION_FORM_TEXT.txt` had grown to 9,229 characters against a 9,000-character budget - 273 over on the CRLF count a form POST actually carries. Then the same auditor was pointed at the text sitting in the live form, which was a third, hand-trimmed variant. | the live text fails **3 of 7** checks: the `= 132 reviews` arithmetic and the `All five components` row gone, `The other 12 crashed` gone, the 36/48 -> 13/48 -> 0/48 provenance progression gone, and the video-versus-repo authority notice gone. Every single omission is a **disclosure that costs the submission something**; nothing flattering was lost. After the fixes: `make verify` exit **0**, 67/67 claims, 9/9 docs, 7/7 form, 129 tests, and every decision number unmoved - unsafe **0/12** and **0/9**, recall **0.970** and **0.96**, plans **12/12**, **9.2** and **10.7** min/case, decision surface **0 of 168**. | Kept, and the fix is deliberately not a check. `check_paste_ready_description` and `check_fits_the_form` both caught their defect on the first run, with exact counts - the suite was green and the *command* was not, which is the fifth consecutive release where that sentence is the finding. Test count unchanged at 129 on purpose: a fifteenth guard over a suite that already reported the defect would confuse the finding with the fix. Nothing under `sentinel/` was touched, so the held-out freeze is undisturbed. Full log: [`docs/SUPERVISOR_LOG_V15.md`](docs/SUPERVISOR_LOG_V15.md). |
| **Rejected: two models with opposing incentives** | Put the model back on the detection path, honestly: one instance must argue the migration is safe, one must argue it breaks something, each must cite a tool result, and a deterministic judge accepts only claims whose citation resolves to a real replay row or row count. Disagreement between them is itself a signal for where a human should look. | not run - it moves recall back onto a nondeterministic component, so the primary metric stops being reproducible from a clean clone with no API key, and there is no fair way to compare a two-model debate against a single prompt | Rejected for this submission and it is the design most likely to raise the recall ceiling, because the ceiling is currently set by what my rules and my corpus know. The reason it is not here is the same reason the verdict is deterministic: a review that gates a deploy should return the same answer twice. |
| **Rejected in v3, half-adopted in v5: delete the narrator entirely** | Render every word of the packet from tool output and demote the model to a read-only Q&A layer over the evidence, whose answers never enter the record. It makes the whole class of problem in Iteration 9 structurally impossible instead of guarded. | v3: not run, because it removes the per-hazard explanation reviewers actually read and answers a challenge about agentic workflows with a linter plus a chatbot. v5: run for the *headline* only - 0/60 model-written headlines, 0/48 misleading headlines reaching the reviewer, and the per-hazard explanations kept | The half that shipped is the half where model prose sits **above** the evidence and can be mistaken for the verdict. The half that did not is the per-hazard explanation, which sits beside the engine error text that contradicts it. Splitting the rejection by *placement in the packet* is the thing I would not have found without writing the attacker: it is not "is model prose allowed", it is "can model prose be mistaken for a finding". |
| **Rejected: counterexample search instead of review** | Attack the migration rather than review it: generate a row set plus a statement that is valid before and fails after, then shrink it to a minimal reproduction. It never needs a declared consumer, so it attacks *the corpus is the world* at the root instead of reporting around it. | not run - it changes the primary metric from "unsafe approvals" to "counterexamples found", for which there is no fair baseline, and it needs a real PostgreSQL, which breaks reproduction from a clean clone with no API key | Rejected for this submission, kept as the design I would build next. Written up in full in `docs/CRITIQUE_LOG.md` (V1) rather than left as a hallway opinion. A witness that *could* exist is also a weaker artifact for a reviewer than a failure in a statement their own service issues today. |
| **Rejected: deploy-time interceptor, no review at all** | Delete the judgment layer. Wrap the migration runner with `lock_timeout` and `statement_timeout`, run it against a branched copy of production first, and replay live traffic sampled from `pg_stat_statements`. The output is a migration that physically cannot hold a lock for longer than N ms. | not run - needs production access and a branchable database, cannot be compared against a prompt on equal terms, and a judge cannot reproduce it in a clean environment | Rejected, and it taught me the most about the problem: it makes lock hazards impossible by construction and does **nothing** for the hazards that break nothing today. Dropping a `CHECK` constraint sails straight through a lock-timeout interceptor. Migration review is partly a workaround for deploy tooling that does not exist yet, and partly irreducible judgement. |
| **Rejected in v15: raise the character cap to fit the text** | The submission field's label now reads "under 10000", not the 9,000 v9 read off it. Setting `FORM_LIMIT = 10000` is one line, makes both failing tests green, and is defensible on the current evidence. | not run - it converts a failing audit into a passing one without touching the artefact the audit is about, in the same pass in which that audit failed | Rejected, and it is the sharpest rejection in this table. Every number here is published because the alternative was a claim nobody could check; a limit relaxed to fit its own text is that alternative arriving *through the audit tool*. 326 characters came out of the prose instead, and checks 3 to 7 did not let a single figure or load-bearing sentence come out with them. The constant is unchanged at 9,000 and is now documented as a **budget held deliberately** rather than as a quotation of a label that has already moved once. |
| **Final** | Full pipeline: replay + rules + memory + verified plan + coverage gate + human gates + a headline the model cannot write. | unsafe **0/12**, gaps cleared **0/2**, recall 0.970, precision 0.970, F1 0.970, severity 0.969, 35/35 findings evidenced, 3 blind spots named with their object, 12/12 plans verified, decision surface unchanged under four hostile models and three narrator modes (**0/168** completed of 180), misleading headlines reaching the reviewer **0/48**, ~8 ms and $0 per case | Main contribution: pairing execution with static rules (iterations 1-3). Biggest change in perceived usefulness: the verified plan (iteration 5). Change I would defend hardest under questioning: the coverage gate (iteration 7), because it is the only one that costs me a published number. Change that taught me the most per line written: iterations 9 and 10, because both bugs were found by writing something whose job was to attack me - and iteration 10 found its bug inside iteration 9's own defence. |

Two ground-truth hazards are still missed, on purpose (see below), and one finding the scorer counts
as a false alarm is arguably correct: on `case_04` the pipeline flags
`CROSS_SERVICE_UNCOORDINATED` because a billing-owned migration breaks the web signup insert, which
is true and which my ground truth simply forgot. I left it as a false positive rather than editing
the target after seeing the result.

## Main failure mode

**The corpus is the world.** Everything this pipeline can prove, it proves from the SQL it was
given. Two of the 12 cases are built to expose it:

* `case_09`: the risky consumer is a dbt model that reads `currency IS NULL` as "legacy" and is not
  in the corpus. No amount of replay finds it. **Still missed, by construction** - and no longer
  cleared. The coverage ledger sees the shape of the hole even though it cannot see what is in it:
  the migration erases every `NULL` from `invoices.currency` and then makes `NULL` unreachable, so
  any consumer that reads `NULL` as a state changes behaviour silently, and the supplied rollback
  restores the column's nullability but not its values. The verdict is capped at
  `NEEDS_COVERAGE_SIGNOFF`, the object is named, the gap is marked irreversible, and
  `sentinel execute` refuses to run it.
* `case_12`: `CLUSTER invoices USING idx_invoices_customer` was outside the parser's model, so v1
  missed `TABLE_REWRITE_LOCK`. v2 recognises the whole-relation maintenance family by name and
  reports the hazard, **and keeps the statement in the coverage ledger anyway**, because naming a
  statement is not modelling it.

The mitigation is the part I would defend, in two halves. The first half was in v1: an unparsed
statement never becomes "safe", it travels through as an explicit unknown and lands in the packet's
*What this review did not check* section. The second half is v2, and it exists because the first half
was not enough: **a stated gap now constrains the verdict.** v1 printed
`unmodelled statement: CLUSTER ...` in an appendix underneath a badge that said the change was
shippable, and reviewers read badges. A tool that quietly narrows its own scope launders a gap into a
green check; a tool that states the gap and then clears the change anyway has only moved the laundry
to a footnote.

What is *still* not solved: the ledger reasons about the shape of a blind spot, never its contents.
It knows that rewriting `invoices.currency` in place is unobservable to replay. It does not and
cannot know that the consumer at risk is a dbt model in another repository. Every gap class here is a
structural argument about the tool's own reach, which is the only kind of argument it is entitled to
make.

## Hot take

**Count what goes in, count what comes out, publish the difference.** Four releases of this
repository have found the same defect one level up: the corpus is a sample of the consumers, the
fixture is a sample of the data, the rule set is a sample of the hazards, the parse is a sample of
the text. Each time the previous fix was correct and its perimeter was invisible from inside,
because the layer that should have caught the new hole was built on the assumption the hole
violated. An audit that starts after a transforming stage cannot see what that stage dropped, so
conservation is not a nice property to have - it is the only kind of completeness claim that
survives its own author.

And the half that indicts the metric rather than the parser: **every single false finding in the
v13 packet cited machine evidence.** "35/35 findings evidenced" has been the headline
reproducibility number here for twelve releases, and it is equally true of a review of a file that
was two thirds string literal. Provenance tells you a claim came from a tool. It does not tell you
the tool was looking at the artefact you are about to deploy.

Give an agent a tool that can be *loudly* wrong, and pair it with rules that can be *quietly* wrong.

The seductive version of this project is "the agent runs the migration, so it knows". That arm scored
**worse than plain static rules** on the metric that matters: execution only ever reports what fails,
and the most expensive migration hazards fail nothing at all. They lock a table, or they delete an
invariant, and the test suite goes green. Verification is not a synonym for correctness; it is a
sensor with a specific blind spot, and the engineering work is knowing the shape of that blind spot
well enough to put a second, differently-shaped sensor next to it.

The corollary I did not expect: the most valuable output was not the hazard list, it was the
*verified plan*. Detection metrics did not move at all when I added plan generation and verification.
Modelled reviewer minutes fell by roughly two thirds at the published constants, and by 63-69% across
every uniform rescaling of them (`results/time_sensitivity.md`). Being right is table stakes; the tool
earns its place by doing the tedious thing the human would otherwise do at 3am.

The one that took a second pass to see, and the reason v2 exists: **a sensor that reports its own
blind spot has not finished the job until the blind spot can change the answer.** v1 did the hard
engineering part - it computed what it could not see and printed it honestly - and then let the
verdict ignore it. Every reliability property in an agent lives at the point where evidence becomes a
decision, and "we told the user in the appendix" is the most comfortable place in the entire system to
hide a failure. The version of this that costs you something is the one worth trusting: the coverage
gate moves no detection metric, adds reviewer minutes, and reverses the sign of my nicest number
under adversarial constants. It is still the change I would defend first.

The one v3 found, and it is smaller and more embarrassing than the others: **a system can be
invariant in every number it publishes and still lie to the person reading it.** Every metric in v2
reads the decision surface, and the decision surface is bolted shut - no model can move a verdict, a
severity or a line of generated SQL. The reviewer reads the sentence at the top. That sentence was
the one thing a model wrote and the one thing nothing checked, so a sycophantic model could print
"safe to ship" above a `BLOCK` on 11 of 12 cases without moving a single published number. Guarding
it cost nothing and proved nothing about detection; it just closed the gap between what the system
knows and what it says. **Audit the output your user actually reads, not the output your metrics
happen to be computed from** - and if you cannot find that gap by removing components, write a
component that lies to you on purpose.

And the one v5 found, inside v3's own fix: **a defence audited in its own vocabulary reports on the
attacker's imagination, not on itself.** The v3 guard rejected every hostile headline it was shown
and published `0/12`, because the harness asked the same regexes the guard enforces. One model that
lies in ordinary professional English - no banned phrase, no verdict token, no injection marker -
walked through it onto 12 of 12 headlines while that column still read zero. The fix was not a longer
list of forbidden phrases, which is the same mistake with more words; it was to make the headline a
pure function of tool output, so provenance is checkable without asking anything to judge meaning:
either those bytes came from a tool or they did not. **Prefer a property you can check over a pattern
you have to keep up to date** - and when you write down a defence's limit in a comment, that is not
disclosure, it is a to-do item with better manners.

## Repo map

```
sentinel/            the pipeline
  agents/prompts/    the instructions that shape each agent (read these first)
  agents/            cartographer, blast_radius, risk_officer, rollout_engineer, verifier
  coverage.py        the coverage ledger + verdict cap (v2)
  narrator.py        model prose treated as untrusted input (v3)
  rulebook.py        which statement kinds anything here actually inspects (v13)
  tools/             sql_parse, shadow_db, query_corpus, incident_memory, registry
  tools/sql_lex.py   the scanner Postgres would recognise: dollar quoting, nested block
                     comments, literal-aware comment stripping, statement spans (v14)
  tools/parse_audit.py  statements the scanner finds minus statements an op accounts for,
                     plus a literal-masked census of every procedural body (v14)
  llm/               scripted stand-in, hosted providers, cassette record/replay
  llm/adversarial.py four hostile models used to attack this repo's own claims: a
                     sycophant, an injected model, a dead endpoint (v3) and a fluent
                     liar written to walk through v3's own blocklist (v5)
  orchestrator.py    fixed pipeline + feedback loop + ablation switches
  report.py, trace.py, cli.py, hazards.py
baseline/            the one-prompt reviewer, two variants
eval/                build_cases.py, 12 cases with ground truth, scoring.py, run_eval.py
  redteam/           7 cases written to make this pipeline approve an outage (v13)
  redteam2/          6 cases the parser itself gets wrong (v14)
  report_components.py   what removing each component costs -> results/components.md
  time_sensitivity.py    band on the modelled reviewer-minute claim
  model_invariance.py    12 cases x 5 models x 3 narrator modes = 180 reviews (v3, v5)
memory/              incidents.jsonl (curated, fictional)
results/             review packets, comparison.md, ablation.md, evaluation.json
trajectories/        one markdown + jsonl trajectory per case
site/                the review desk: index.html, generated data/ and py/ (Pyodide runtime)
tools/               build_site.py, build_artifact.py, check_results.py (67 claims about the numbers)
  check_docs.py          9 claims the docs make about the repo: references, glyphs, entry
                         point, stale counts for any claim ledger or audit, stale test counts,
                         no heading trapped in a code fence (v11), no counting tool that
                         misstates its own size in its docstring, and no live document
                         declaring an older release than the newest one (v12)
  check_determinism.py   reruns every generator in a temp copy and diffs 146 files back: the
                         wall-clock fields are named, the decision bytes must not move (v11).
                         Detects an interactive packet in results/ and names the fix (v12)
  check_cross_version.py reruns them again on a second interpreter and diffs the two trees:
                         0 decision differences on CPython 3.11 and 3.12, and the wall-clock
                         figures published as the one thing that is not portable (v12)
  check_submission_text.py  7 claims about the description in the submission form, which is
                         the one artefact that lives outside this repository (v8)
  collect_agent_traces.py  generates agent_traces/INDEX.md, refuses on secret shapes
agent_traces/        development-agent sessions (see AGENT_USE.md)
AGENT_USE.md         coding-agent disclosure required by the challenge
SUBMISSION_FORM_TEXT.txt  the exact plain-text description submitted to the form, committed
                     verbatim so tools/check_submission_text.py can audit it (v8)
.github/workflows/   verify the claims, then publish the desk to GitHub Pages
docs/                CRITIQUE_LOG.md (read first), SUPERVISOR_LOG_V3.md to _V14.md,
                     DESIGN_LOG.md, AGENT_TRAJECTORIES.md, SUBMISSION.md,
                     VIDEO_SCRIPT.md (what the submitted video was made from),
                     VIDEO_SCRIPT_V12.md (single-take script against the current numbers),
                     VIDEO_ADDENDUM.md (every number the video predates)
tests/               129 stdlib tests
```

## Limitations, stated plainly

* SQLite stands in for PostgreSQL. Lock queues, MVCC and planner behaviour are not observable, which
  is exactly why the static layer exists. A production version should replay against a real
  PostgreSQL container restored from a schema-only dump.
* The query corpus and row counts are inputs. In a real deployment they come from
  `pg_stat_statements`, dbt manifests and ORM logs; wiring that up is integration work, not research.
* Fixture data is small and synthetic, so data-dependent hazards are found only where the fixtures
  expose them. Real deployments should sample the actual distribution (anonymised) instead.
* The offline default model is a scripted stand-in, documented in `sentinel/llm/scripted.py`, so the
  numbers above are byte-reproducible with no API key. The same prompts run against a hosted model
  with `--provider openai`; because the model does not decide hazards, that changes the prose and the
  token cost, not the primary metric. v3 stops asserting that and measures it, and v5 widens the
  attack: four hostile models, three narrator modes, 0/168 completed reviews with a changed decision
  surface
  (`results/model_invariance.md`). What that measurement does *not* cover is fluent deception in
  words `sentinel/narrator.py` does not pattern-match, because the audit shares its patterns with
  the guard. That is a deliberate trade and it costs something: see *Can the model move any of
  this?*
* **Twelve cases, one schema, one 14-statement corpus, and I wrote the ground truth as well as the
  rules.** Every detection number in this file is bounded by that. `0.970` recall means agreement
  with my own taxonomy on a closed world, not coverage of real migration hazards, and the tell is
  already published: on `case_04` the pipeline emits a `CROSS_SERVICE_UNCOORDINATED` that the scorer
  counts against it and that is arguably correct, which means the ground truth is under-specified in
  the one direction I would notice least. I left it as a false positive rather than editing the target
  after seeing the result. Do not quote the F1 without the denominator.
* The coverage ledger reasons about the *shape* of a blind spot, never its contents. It knows an
  in-place rewrite of `invoices.currency` is unobservable to replay; it cannot know the consumer at
  risk is a dbt model in another repository.

MIT licensed. See [`LICENSE`](LICENSE).