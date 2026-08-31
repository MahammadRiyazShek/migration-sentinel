# Migration review: Make country_code nullable again

**NOT CLEARED - coverage gap on an affected object**

Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches, or a defect in the plan it generated. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-rt_05_relax_country_not_null` · case `rt_05_relax_country_not_null` · owning service `billing-api` · 8.2 ms · model scripted-v1 (2 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

> **Not cleared on coverage.** The hazards found here are not blocking, but 1 object(s) this migration touches sit inside a blind spot of the review. The verdict is capped rather than clean: no hazard has been invented, and nothing has been certified either. See *Coverage ledger* below.

## Hazards

No hazards found by execution or by the static rules.

## Blast radius

- statements in the corpus that touch the changed objects: 6 (weighted score 17)
- shadow replay: 19/19 statements passed before, 19/19 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Human decisions required (the tool will not decide these)

- statement 0 (drop_not_null) is outside the tool's model and needs manual review: ALTER TABLE customers ALTER COLUMN country_code DROP NOT NULL
- coverage gap on `customers:drop_not_null` (unruled_statement): a reviewer decides by hand what statement 0 changes for future writes and who depends on the current behaviour

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 0 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.


## Coverage ledger

1 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `customers:drop_not_null` | unruled_statement | no static rule inspects `drop_not_null` and shadow replay cannot see its consequence: relaxing nullability breaks readers that assume non-null, and every one of those readers is in application code rather than in the SQL corpus | a reviewer decides by hand what statement 0 changes for future writes and who depends on the current behaviour |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/rt_05_relax_country_not_null.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
