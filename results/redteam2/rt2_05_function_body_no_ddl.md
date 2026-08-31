# Migration review: Add a dunning audit trigger function and the column it stamps

**NOT CLEARED - coverage gap on an affected object**

Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-rt2_05_function_body_no_ddl` · case `rt2_05_function_body_no_ddl` · owning service `platform` · 8.3 ms · model scripted-v1 (2 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

> **Not cleared on coverage.** The hazards found here are not blocking, but 1 object(s) this migration touches sit inside a blind spot of the review. The verdict is capped rather than clean: no hazard has been invented, and nothing has been certified either. See *Coverage ledger* below.

## Hazards

No hazards found by execution or by the static rules.

## Blast radius

- statements in the corpus that touch the changed objects: 8 (weighted score 25)
- shadow replay: 19/19 statements passed before, 19/19 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
ALTER TABLE "invoices" ADD COLUMN "dunning_stamped_at" TIMESTAMPTZ;
```

### Rollback for phase 1

```sql
ALTER TABLE "invoices" DROP COLUMN "dunning_stamped_at";
```

### Human decisions required (the tool will not decide these)

- statement 1 (procedural_block) is outside the tool's model and needs manual review: CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dunning_stamp
- coverage gap on `$fn$ body at statement 1` (procedural_body): a reviewer reads the $fn$ body of statement 1 in full, including every branch, before phase 1

## Coverage ledger

1 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `$fn$ body at statement 1` | procedural_body | the body holds 3 scanned statement(s) and nothing in this pipeline models a procedural block: the census below is a keyword scan, not a parse, so the packet knows that DDL is in there and not what the block does with it (branches, loops, exception handlers, dynamic SQL) | a reviewer reads the $fn$ body of statement 1 in full, including every branch, before phase 1 |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.
- unmodelled statement: op 1 (procedural_block) not modelled structurally: CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger A

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/rt2_05_function_body_no_ddl.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
