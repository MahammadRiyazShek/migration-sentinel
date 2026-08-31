# Supervisor log, v13: the rule set is a sample too

Twelve supervisor passes audited what this pipeline *says*. This one audited what it
*inspects*, and that turned out to be a different question with a worse answer.

## The brief

Every previous pass took the hazard vocabulary as given and asked whether the pipeline
found the hazards in it. Both evaluation sets were labelled out of that vocabulary, so
neither could ever ask the only question that matters for a safety tool: **is there a
class of hazard nobody enumerated?** So this pass ran the opposite brief - find a
migration a Postgres primary calls an outage and this pipeline calls SAFE - and probed
*statement kinds* rather than hazards.

Six probes. Two hits, and a third finding underneath both of them.

## R1: DROP INDEX on a hot table

`DROP INDEX idx_invoices_customer` on 48M rows, with three live statements filtering
`invoices.customer_id`, one of them on the checkout path. Verdict: **SAFE**, zero
hazards, zero declared gaps.

Why every layer missed it, in order:

* shadow replay executes all 16 corpus statements successfully, because SQLite has no
  planner cost and the fixtures are three rows. The hazard is in the plan, not the result,
  and every tool in `sentinel/tools/` answers questions about results;
* no static rule mentions `drop_index`. The rule set was written to cover the three things
  replay is blind to - locks, volume, intent - so it inherited the *shape* of replay's
  blind spots rather than the shape of the hazard space. All three of those are properties
  of one statement;
* the coverage ledger said nothing, which is the interesting part. See R3.

## R2: CONCURRENTLY inside a transaction block

`BEGIN; CREATE INDEX CONCURRENTLY ...; COMMIT;` Postgres refuses this outright and every
major migration framework opens that transaction by default. Verdict: **SAFE**.

The parser emits `transaction_control` and `create_index(concurrently=True)` as separate
ops and no rule correlates them, because no rule in this repository has ever looked at
two statements at once. And the **text-only baseline catches it**, since `BEGIN` plus
`CONCURRENTLY` in one file is a famous string. On this hazard class the advanced solution
scored below the thing it exists to beat. That is published in `results/redteam.md` and
in the submission description rather than left out.

## R3: the ledger was an allow-list of known unknowns

R1 and R2 were absent rules, not wrong ones. The thing that should have caught an absent
rule is the coverage ledger, whose entire job since v2 has been "declare what this review
could not see, and cap the verdict when it did not see something". It declared nothing.

Every gap class in `sentinel/coverage.py` before this pass - `unmodelled_statement`,
`in_place_data_mutation`, `value_class_erased`, `uncovered_object`,
`fixture_bounded_value_scan` - is keyed to a statement kind that some rule or some replay
*already handles*. So the ledger could only ever declare blind spots about objects
something had already looked at. v2 made a declared gap constrain the verdict; it never
asked what happens when nothing declares anything.

`sentinel/rulebook.py` is the answer: all 26 statement kinds `parse_migration` can emit,
partitioned into RULED, REPLAY_COVERED, LEDGERED and RESIDUAL, with the reason per kind.
`tests/test_all.py::TestRulebook` fails if the parser learns a kind nobody has classified,
and an unclassified kind is treated as residual at runtime, so a new parser feature makes
reviews more cautious rather than more quietly confident.

## The two experiments this pass removed

**Default deny.** The first version of the residual class opened a gap for any op no rule
fired on. It flagged `case_06` - `CREATE UNIQUE INDEX CONCURRENTLY`, the case that exists
to catch reviewers who cry wolf - because the index rule looked at it and correctly
cleared it, and "no hazard was produced" is indistinguishable from "nothing looked" if you
only count hazards. The distinction the shipped version draws is between *a rule considered
this kind* and *no rule exists for this kind*. Removed, and the reason is in the module
docstring rather than in a commit message.

**A bare `drop_index` blocker.** The first index rule raised `ACCESS_PATH_REMOVED` on
`rt_06` and `rt_07`, which are the commonest correct index migration there is: drop the
narrow index, create the composite that covers it. A B-tree on `(customer_id, status)`
serves a lookup on `customer_id`, so the access path survives. A safety tool that blocks
the correct version of a change gets switched off, and a switched-off tool has recall
zero. `replacement_index()` in `agents/risk_officer.py` is that fix, and both cases stayed
in the set as the canary.

## What shipped, and what it cost

Two rules (`ACCESS_PATH_REMOVED`, `CONCURRENT_DDL_IN_TRANSACTION`), two gap classes
(`unruled_statement`, `unused_access_path`), one tool
(`corpus.access_path_users`, which answers "what asks the planner to find rows by this
column" rather than "what mentions it"), one inventory module, seven cases, one ablation
arm (`no_rule_coverage`, which reproduces v12 exactly), 22 tests and 11 claims.

On the red-team set: unsafe approvals 3/7 -> 0/7, blocking cases given a clean verdict
3/3 -> 0/3, at a cost of 1.7 modelled reviewer minutes per case.

On the 21 labelled cases in `eval/cases` and `eval/holdout`: **nothing moved.** Same
verdicts, same hazards, same severities, same gap counts, computed per case by
`eval/run_redteam.py` rather than asserted. That is the number to read first, and it is
the whole argument that this layer was missing rather than retuned to fit what it was
shown.

## The hot take this pass earned

An allow-list of known unknowns is still an allow-list. Three releases of this repository
have now found the same defect one level up: the corpus is a sample of the consumers (v1),
the fixture is a sample of the data (v6), the rule set is a sample of the hazards (v13).
Each time, the previous fix was correct and its perimeter was invisible from inside.

The generalisable move is not another honesty layer. It is arithmetic: enumerate what your
tool can parse, subtract what any part of it actually inspects, and publish the remainder
as a named blind spot with a human gate. Ablations cannot find this, because an ablation
only removes what you already built.
