# Migration review: Backfill invoices.currency and make it NOT NULL

**SHIP AS PLAN - not as written**

Shippable, but only as the staged plan below. 0 blocker, 2 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

`run eval-case_09_unbatched_backfill` · case `case_09_unbatched_backfill` · owning service `billing-api` · 5.9 ms · model scripted-v1 (4 calls, $0.0000)

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

### Questions for the reviewer

- What is the accepted risk for NOT_NULL_NO_DEFAULT?
- What batch size and pause has this table tolerated before?

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
