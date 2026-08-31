# Supervisor log, v16: the plan is an artefact too

Every honesty layer in this repository points at the migration a human wrote. The rule
inventory partitions the statement kinds the parser can emit **from the input file**. The
parse audit reconciles the op list against **the input file**. The coverage ledger names what
the review could not see **about the input**. The narrator provenance stops the model writing
the headline **about the input**.

This pipeline also writes SQL. Three scripts of it, on every run: phase 1, phase 2, a
rollback. Until v16 exactly one was checked, by exactly one of the two halves of the design:
`agents/verifier.py` replayed today's corpus against phase 1. Phase 2 and the rollback were
text, printed in the packet under a heading that said *safe to run now*.

## Critique layer: three assumptions, all wrong

**A1. "Verified" meant the plan was safe.** It meant phase 1 broke no statement in today's
corpus. `12/12 verified expand/contract plans` - the strongest row in the headline table - was
a claim about one third of each plan, under the half of the design this repository's own
ablation calls the weaker one on its own (`results/ablation.md`, since v2: replay-only 2 unsafe
approvals, rules-only 1, because a lock hazard produces no failing query). The argument against
replay-only review was never applied to our own output.

**A2. "The generator is careful, so it needs no review."** It is careful: `DROP INDEX
CONCURRENTLY`, keyset-batched backfills, `NOT VALID` split from `VALIDATE`. Careful *by
construction*, which is the category of claim this project refuses everywhere else. Measured,
on 21 labelled cases already in the repository: 6 defects, every one under a printed
`plan verified: true`.

**A3. "A hazard in a plan would show up as a hazard."** It cannot. Hazards come from rules that
run over the input before the Rollout Engineer writes a line. Nothing was mis-scored. Nothing
was scored.

## Variation operator: two routes considered

1. **Treat generated statements as ordinary input and re-run the hazard rules over them.**
   Rejected. The hazard list is the thing the ground truth labels describe, so a finding about
   our own SQL entering it corrupts every recall, precision and severity number in `results/`,
   and the honest comparison against v15 becomes impossible in the same commit that earns it.
2. **A separate audit whose findings cap the verdict and become human gates.** Shipped. It is
   where v2 put a declared coverage gap, for the same reason: a packet must not certify what it
   did not review, and it must not invent a hazard to say so.

## What it found

| defect | where | v15 behaviour |
|---|---|---|
| `ROLLBACK_WINDOW_UNSTATED` | 4 of 21 labelled cases | rollback drops a column a code step in the same packet asks the team to start writing; no order stated. Replay of that rollback breaks **0** corpus statements, which is why execution could never find it |
| `CONTRACT_STEP_UNGATED` | 2 of 21 | generated `VALIDATE CONSTRAINT` on 48M and 21M rows with no human gate, four versions after `rulebook.py` wrote down that nothing prices it |
| `GENERATED_TEXT_UNPARSED` | `rt2_03` | the input has an unterminated literal, the pipeline correctly refuses to certify it, and the engineer then built a batched `UPDATE` out of the mangled parse and printed it under *Phase 1 - safe to run now* |

The third was written as a hypothesis - the engineer is a text producer and this repository has
already been wrong once about a text producer - and it fired on a case written for round 2.

## The parity number, first

`no_plan_audit` reproduces v15 exactly. Across all **34** labelled cases in `eval/cases`,
`eval/holdout`, `eval/redteam` and `eval/redteam2`, `full` and `no_plan_audit` are identical on
every input verdict, hazard code, severity and coverage-gap count: **0 cases moved**. That is by
construction, and the construction is the argument.

## The unflattering half

- One ablation arm got better for a reason nobody designed. Replay-only drops from 2 unsafe
  approvals to 1, on `case_10`: no rule priced the 48M-row validation, and the plan written for
  the migration the arm had not understood carried an ungated `VALIDATE CONSTRAINT`, so the
  verdict was capped instead of cleared. A real safety gain and a bad diagnosis - the reviewer
  is told a generated step has no gate; nobody says *48 million rows*. So the v2 sentence is
  corrected rather than kept: **execution alone is not sufficient**, and the old arithmetic now
  needs `plan_audit=False` to reproduce.
- It costs reviewer minutes: 9.2 to 10.0 in sample, 10.7 to 11.7 held out, all of it in named
  sign-offs.
- The gate matcher reads names, not questions. A gate that names the object and asks the wrong
  thing passes, and every time this audit trusted a sentence the packet says so
  (`audit_gate_text_only`, counted per run).
- The fix not made: the engineer still generates a plan from a parse the pipeline has already
  declared unreliable. Refusing to plan at all is the right answer and it is a behaviour change
  to the arm under measurement, so it is written down rather than shipped in the last hour.

## Hot take, updated

v14 said: enumerate what your tool can parse, subtract what any part of it inspects, publish the
remainder. v16 says the subtraction has a second column nobody had filled in. **Your tool's
output is an artefact too.** Four adversarial passes aimed at the input found three holes; the
first one aimed at the output found three more, in code that had been shipping since v2, and no
metric in the repository could have moved because the labels only describe the input. If your
agent writes something a human will run, review it with the same machinery you point at the
thing the human gave you - and ask at least one question about a property of two artefacts
rather than of one.

Commands: `make redteam3`, `results/redteam3.md`, `sentinel/plan_audit.py`.
