# Migration review: Backfill invoices.currency and make it NOT NULL

**NOT CLEARED - coverage gap on an affected object**

Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 2 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-case_09_unbatched_backfill` · case `case_09_unbatched_backfill` · owning service `billing-api` · 8.3 ms · model scripted-v1 (4 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

> **Not cleared on coverage.** The hazards found here are not blocking, but 1 object(s) this migration touches sit inside a blind spot of the review. The verdict is capped rather than clean: no hazard has been invented, and nothing has been certified either. See *Coverage ledger* below.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **HIGH** | NOT NULL added without a usable default | `invoices.currency` | static |
| 2 | **HIGH** | Backfill runs as one unbounded statement | `invoices` | static |

### 1. [HIGH] NOT NULL added without a usable default

SET NOT NULL on invoices.currency validates every row under a lock

- evidence: statement 1: `ALTER TABLE invoices ALTER COLUMN currency SET NOT NULL`

### 2. [HIGH] Backfill runs as one unbounded statement

backfill on invoices runs as one statement over 48,000,000 rows

- evidence: statement 0: `UPDATE invoices SET currency = 'usd' WHERE currency IS NULL`

## Blast radius

- statements in the corpus that touch the changed objects: 5 (weighted score 16)
- shadow replay: 16/16 statements passed before, 16/16 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
-- repeat until zero rows are affected (batch size 5000):
UPDATE invoices SET currency = 'usd' WHERE currency IS NULL AND "id" IN (SELECT "id" FROM "invoices" WHERE currency IS NULL LIMIT 5000);
```

### Human decisions required (the tool will not decide these)

- statement 1 (set_not_null) is outside the tool's model and needs manual review: ALTER TABLE invoices ALTER COLUMN currency SET NOT NULL
- IRREVERSIBLE - coverage gap on `invoices.currency` (value_class_erased): a reviewer confirms no consumer treats invoices.currency IS NULL as meaningful, and that the pre-backfill values are captured somewhere restorable

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the accepted risk for NOT_NULL_NO_DEFAULT?
- What batch size and pause has this table tolerated before?

## Coverage ledger

1 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `invoices.currency` **(irreversible)** | a value class is erased and the rollback does not restore it | the backfill removes every NULL from invoices.currency and the following SET NOT NULL makes NULL unreachable; any consumer that reads NULL as a distinct state changes behaviour silently, and the supplied rollback restores the column's nullability but not the values | a reviewer confirms no consumer treats invoices.currency IS NULL as meaningful, and that the pre-backfill values are captured somewhere restorable |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_09_unbatched_backfill.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 2 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
