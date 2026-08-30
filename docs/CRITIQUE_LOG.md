# Critique log: what a hostile reviewer said about v1, and what I did about it

> This is the working log that drove v2. It is placed first on purpose: every change in the
> v2 rows of the README's Improvement Changelog traces back to a numbered entry here, and the
> entries that produced no change say so.

Method: a fresh session with no memory of building the project was pointed at the finished v1
repository with one instruction - *find the assumptions this submission does not know it is
making, and try to make the headline numbers false*. Then the findings were triaged by whether
they could be settled with a measurement rather than an argument.

---

## Layer 1 - three hidden assumptions in v1

### C1. "Unsafe approvals = 0" was partly protected by the shape of the verdict vocabulary

`eval/scoring.py` counted an approval as `verdict in {"APPROVE", "SAFE"}`. `SAFE_WITH_PLAN`
therefore scored as *not* an approval. But `SAFE_WITH_PLAN` renders in the packet as
**"SHIP AS PLAN - not as written"**, and a reviewer treats that as permission to ship.

On `case_09` the pipeline returned `SAFE_WITH_PLAN` directly above a declared coverage gap, and
scored a clean 0 on the primary metric while missing a real ground-truth hazard. The v1
submission described that as a limitation in prose. It is not a prose problem: **the metric could
not see the gap because the verdict ladder had no rung for "I did not see enough to say".**

The assumption underneath: *that the verdict vocabulary is a faithful proxy for what a human does
next.* It was not.

**Settled by measurement.** v2 adds a coverage ledger and a verdict cap
(`sentinel/coverage.py`), a new metric that is a property of the *case* rather than of the arm
(`gap_cases_cleared_without_signoff`), and a `no_coverage` ablation arm that reproduces the v1
behaviour exactly. v1 clears 1 of 2 gap cases; v2 clears 0. This is the largest change in v2.

### C2. "The primary metric is invariant to the model by construction" is a boast and an indictment

v1 says, correctly, that hazards and severities come from tools and never from the model, so the
primary metric cannot move when you change the model. Read the other way round: **if no published
number can be changed by swapping the model, then no published number is evidence about a model.**
A judge who reads `--provider scripted` as the default can reasonably ask whether this is an
agentic system at all, or a deterministic linter with a narrator attached.

I still think the design is right - a review that gates a deploy should not have a nondeterministic
verdict - but v1 sold determinism as a pure virtue and never priced what it costs in claim strength.

**Not settled by measurement, settled by scope.** v2 states the boundary in one place instead of
implying a stronger claim: the *facts* are deterministic, the *agency* is in the orchestration -
tool selection per agent, the verifier's feedback loop, the policy tightening between attempts,
the retry budget, and the escalation when the budget runs out. That loop is what is evaluated by
the ablations, and it is the only thing the ablations can evaluate. The prose layer is a narrator
and is labelled as one. See `README.md` -> *Where the agency actually is*.

### C3. Recall of 0.97 is agreement with my own taxonomy, in a closed world of one schema

Twelve cases, one schema, one 14-statement corpus, 33 ground-truth hazards, all written by the
person who also wrote the hazard vocabulary and the rules. Precision and recall measure
self-consistency at least as much as they measure coverage of real migration hazards.

The tell was already in v1 and to its credit it was published: on `case_04` the pipeline emits a
`CROSS_SERVICE_UNCOORDINATED` that the scorer counts against it and that is arguably correct - which
means the ground truth is under-specified, in the one direction I would notice least.

**Not settled.** It cannot be settled inside a three-day sprint with synthetic data. v2's response
is to stop quoting F1 without its denominator, to keep `case_04`'s false positive unedited, and to
say plainly that the corpus size is the ceiling on every detection number in the submission.

### C4 (raised, folded into C3). The reviewer-minute model's largest term is a definitional artifact

`verify_unevidenced_claim_minutes` charges 4 minutes per finding without an evidence list. Pipeline
findings all carry evidence by construction; baseline findings never do. So the biggest term in the
time model is decided by a structural property of the arms, not by reviewer behaviour.
`eval/time_sensitivity.py` already existed to bound this, and the v2 numbers make it worse rather
than better - see M3 below.

---

## Layer 2 - two radically different designs, and why they are not this submission

Both of these attack the failure mode v1 named as its main one (*the corpus is the world*) more
directly than a coverage ledger does. Both were rejected on reproducibility grounds, which is a
constraint of the competition and not a claim about engineering.

### V1. Counterexample search instead of review

Stop reviewing the migration and start attacking it. Given the pre-migration schema and the
migration, search for a *witness*: a row set plus a statement that is valid before and fails after.
Property-based generation over column types, nullability and constraints; shrink each witness to a
minimal reproduction; report `here is a query and a row that this migration breaks` instead of
`here is a hazard code`.

Why it is genuinely better: it never needs a declared consumer. The tool invents the consumer, so
the corpus stops being the world.

Why it is not this submission: a witness that *could* exist is a much weaker artifact for a
reviewer than a failure in a statement their service actually issues, so it changes the primary
metric from "unsafe approvals" to "counterexamples found", and there is no fair baseline for that.
It also needs a real PostgreSQL to be meaningful, which breaks the from-a-clean-clone-with-no-API-key
reproduction. **Kept as the design I would build next with a fortnight and a real database.**

### V2. No review at all - a deploy-time interceptor

Delete the judgment layer. Wrap the migration runner instead: every statement executes with
`lock_timeout` and `statement_timeout` set, inside a transaction, against a branched copy of
production first, with live traffic sampled from `pg_stat_statements` replayed against the branch.
The output is not a verdict, it is a migration that physically cannot hold a lock for longer than
N milliseconds.

Why it is genuinely better: it removes the human from the loop where the human adds nothing (lock
duration is a machine-checkable property) and it uses *real* traffic, which is the only complete
consumer corpus that exists.

Why it is not this submission: it needs production access and a branchable database, it cannot be
compared against a prompt on equal terms, and a judge cannot reproduce it in a clean environment.
It also does not help with the hazards that break nothing today - dropping a `CHECK` constraint
sails straight through a lock-timeout interceptor. **Kept as the argument that migration review is
partly a workaround for deploy tooling that does not exist yet.**

---

## Layer 3 - what shipped, and three mistakes caught in the first version of it

Three changes shipped from this log: the coverage ledger and verdict cap (C1), the
whole-relation maintenance rule (a `case_12` miss that was never about coverage), and the honesty
edits (C2, C3). Everything else stayed as a documented limit.

**M1. The cap was one design decision away from being a false-alarm machine.** A coverage-gap class
for "no corpus statement references this column" is obviously right for a column being dropped and
obviously wrong for a column being added - nothing can reference a column that does not exist yet.
Left unrestricted it would have capped every `ADD COLUMN` case, which is the exact behaviour v1
deleted from the drift checker in the changelog's *Removed* row. `PREEXISTING_TOUCH_KINDS` in
`sentinel/coverage.py` restricts it by construction, and the measured result is that gaps are empty
on 10 of 12 cases including the clean one. Pinned by
`tests/test_all.py::TestCoverageLedger::test_cap_does_not_fire_on_the_clean_case`.

**M2. Naming `CLUSTER` nearly bought a hazard by selling a gap.** Teaching the parser about
whole-relation maintenance commands closes the `case_12` `TABLE_REWRITE_LOCK` miss. The tempting
implementation gives the statement a real op kind, which quietly removes it from the unmodelled
list - trading a truthfully reported blind spot for a detection point. `maintenance_rewrite` is
therefore a member of `UNMODELLED_KINDS`: the hazard is reported *and* the statement still appears
in the coverage ledger, because being able to name a statement is not the same as being able to
model it. Pinned by `test_maintenance_rewrite_is_named_but_still_unmodelled`.

**M3. The instinct on the time claim was to reprice the gate. The correct action was to publish the
reversal.** The cap adds a human gate, so modelled reviewer minutes went 8.5 -> 9.2 per case, and in
`results/time_sensitivity.md` the two adversarial ratio sets that merely *collapsed* the v1
advantage to about 1% now **reverse its sign** (-12% and -5%). Repricing `decide_human_gate_minutes`
would have hidden that, from the same file whose entire purpose is to stop me hiding it. The number
is published as it fell out, and `tools/check_results.py` now asserts that the coverage gate *costs*
reviewer minutes rather than saving them, so the trade cannot be quietly reversed later.
