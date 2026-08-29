# Design log

Written before the implementation, kept as the running record. The critique and the two rejected
architectures below are what the final design is a reaction to.

## Persistent memory log (the version that guided the build)

1. Correctness in migration review comes from **execution and lookup**, not from a better prompt.
   Any component whose output is a fact must be a tool.
2. Execution has a specific blind spot: hazards that fail nothing (locks, volume, removed
   invariants). A second, differently-shaped layer is required, and it must be labelled as rules
   rather than dressed up as measurement.
3. The evaluation has to be runnable with no key, no network and no spend, and it has to return the
   same numbers every time, or nobody will rerun it. That constraint decides the model layer.
4. The deliverable a reviewer wants is not a hazard list, it is a plan they can execute plus the
   list of decisions the tool refuses to make for them.
5. Never let an unparsed statement become "safe". Unknowns must be visible in the same document as
   the green checks.
6. Ground truth is written before the first run, and it keeps two hazards the pipeline cannot find.

## Critique layer (supervisor's pass over the first plan)

The first plan was: "an agent reads the migration, the schema and the query corpus, and reports
hazards". Three hidden assumptions in it:

1. **That reading is equivalent to knowing.** The plan assumed a model given the schema and the
   corpus would correctly derive which statements break. It will not: the derivation depends on
   resolution rules (view binding, column sets, constraint semantics, data contents) that a model
   approximates and a database engine computes exactly. Confirmed later by measurement: giving the
   baseline the schema raised family recall from 0.64 to 0.86 but dropped strict precision from 0.95
   to 0.69. More context, more guessing.
2. **That "did it break?" is the whole question.** The plan had no way to represent a hazard that
   breaks nothing: a 48M-row index build, a dropped CHECK constraint. The replay-only ablation
   scored *worse* than rules-only on unsafe approvals (2 vs 1) precisely because of this.
3. **That the reviewer's bottleneck is detection.** It is not. The bottleneck is the 20 minutes of
   writing a staged rollout after detection. A tool that only finds problems hands the work back.
   This is why the Rollout Engineer and Verifier exist, and why reviewer minutes fell by two thirds
   while detection metrics did not move.

Two further flaws that shaped implementation details: an LLM-driven control flow would have made the
same review non-reproducible across runs (fixed by a deterministic pipeline with one bounded feedback
loop), and a project depending on a hosted model for its headline numbers is not reproducible by a
judge without a key (fixed by the documented scripted stand-in plus optional cassettes).

## Variation operator (two architectures considered and rejected)

**Variation 1: a single autonomous agent with a shell.** Give one agent a container, a real
PostgreSQL instance, the repo, and let it decide what to run: restore a dump, apply the migration,
grep the codebase, run the test suite. Strictly more capable, and genuinely tempting for coverage
(it would have caught the `CLUSTER` statement the parser cannot model).

Rejected because the output stops being reviewable. Two runs take different paths, so a reviewer
cannot tell whether "no hazards" means "checked and clean" or "did not look there", and the audit
trail becomes a shell history. For a step that gates a production deploy, a fixed pipeline where every
claim maps to a named tool call beats a smarter process nobody can re-derive. Partially adopted: the
production version should replay against a real PostgreSQL container, but through the same fixed tool
interface.

**Variation 2: pure static analysis, no agents at all.** A linter over the migration AST plus a
dependency graph built from the corpus. Deterministic, fast, no model.

Rejected as a whole, adopted in part. It is the `no_replay` ablation arm, and it scores precision
1.000 with recall 0.545: it cannot know that `customer_billing_summary` loses a column, or that two
customers already share an email, because both require running something against data. It also cannot
write the expand/contract plan or the questions a reviewer should ask a sibling team. The lesson kept
from it: the static layer should be explicit rules, small and readable, not a model pretending to be
rules.

## Self-review (three things wrong with the first draft of this project, and what I changed)

1. **The comparison was unfair in the baseline's favour.** The first baseline prompt did not receive
   the rollback script, so it flagged `MISSING_ROLLBACK` on every case, including the six that ship
   one. Fixed: the baseline now sees the rollback and the fabricated false positives disappeared.
   A rigged baseline makes the whole report worthless, even when the real gap is large.
2. **The pipeline was scoring its own homework in two places.** Purely additive column-set changes
   were counted as hazards (fired on every `ADD COLUMN`, matched nothing in ground truth), and view
   probes emitted duplicates of hazards already reported against the corpus statement that reads the
   view. Both removed; strict precision went 0.939 -> 0.969. Related discipline: when the pipeline
   flagged a cross-service hazard on case_04 that my ground truth had forgotten, I left it counted as
   a false positive instead of editing the target after seeing the answer.
3. **"Verified" was doing unearned work.** The first plan generator emitted a plan and the report
   called it safe. It was never replayed, and on case_01 the phase-1 view swap did remove a column a
   live consumer reads. Fixed by making the Verifier re-parse and replay the generated SQL, feed
   failures back, and escalate after three attempts rather than shipping something unproven. The word
   "verified" now has a test behind it: `tests/test_all.py::TestPipeline`.
