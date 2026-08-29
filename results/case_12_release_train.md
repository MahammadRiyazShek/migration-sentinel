# Migration review: Release train: six changes in one migration

**BLOCK - do not merge**

Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 3 blocker, 4 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

`run eval-case_12_release_train` · case `case_12_release_train` · owning service `billing-api` · 8.6 ms · model scripted-v1 (10 calls, $0.0000)

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_billing_tax` | replay |
| 2 | **BLOCKER** | Index built without CONCURRENTLY on a large table | `usage_events` | static |
| 3 | **BLOCKER** | Uniqueness conflicts with data already in the table | `subscriptions.customer_id` | replay |
| 4 | **HIGH** | Destructive change shipped in a single step | `invoices.tax_rate` | static |
| 5 | **HIGH** | Index built without CONCURRENTLY on a large table | `subscriptions` | static |
| 6 | **HIGH** | Data-integrity constraint removed | `subscriptions` | static |
| 7 | **HIGH** | Backfill runs as one unbounded statement | `invoices` | static |
| 8 | **MEDIUM** | No rollback path supplied | `-` | static |

### 1. [BLOCKER] Live query breaks after migration

q_billing_tax fails after the migration: OperationalError: no such column: tax_rate

- evidence: shadow replay: `SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1` -> OperationalError: no such column: tax_rate
- services affected: billing-api

### 2. [BLOCKER] Index built without CONCURRENTLY on a large table

index idx_usage_events_name is built without CONCURRENTLY on usage_events (900,000,000 rows, very large)

- evidence: statement 3: `CREATE INDEX idx_usage_events_name ON usage_events (event_name)`
- evidence: declared row estimate for usage_events: 900,000,000
- prior incidents: INC-2024-07

### 3. [BLOCKER] Uniqueness conflicts with data already in the table

Uniqueness on subscriptions.customer_id is violated by rows already in the table

- evidence: shadow backfill: backfill subscriptions: UNIQUE constraint failed: subscriptions.customer_id (row={'id': 2, 'customer_id': 1, 'status': 'canceled', 'seats': 3, 'price_cents': 9900, 'started_on': '2023-02-01', 'cancele
- prior incidents: INC-2025-04

### 4. [HIGH] Destructive change shipped in a single step

drop column on invoices.tax_rate lands in a single deploy

- evidence: statement 2: `ALTER TABLE invoices DROP COLUMN tax_rate`
- prior incidents: INC-2023-09

### 5. [HIGH] Index built without CONCURRENTLY on a large table

index idx_subscriptions_customer is built without CONCURRENTLY on subscriptions (2,600,000 rows, large)

- evidence: statement 1: `CREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id)`
- evidence: declared row estimate for subscriptions: 2,600,000
- prior incidents: INC-2024-07

### 6. [HIGH] Data-integrity constraint removed

subscriptions_seats_chk (check) is dropped from subscriptions; no query breaks today, invalid rows become possible tomorrow

- evidence: statement 4: `ALTER TABLE subscriptions DROP CONSTRAINT subscriptions_seats_chk`
- evidence: constraint text: (seats > 0)

### 7. [HIGH] Backfill runs as one unbounded statement

backfill on invoices runs as one statement over 48,000,000 rows

- evidence: statement 5: `UPDATE invoices SET status = 'open' WHERE status = 'draft'`

### 8. [MEDIUM] No rollback path supplied

the change ships without a rollback script

- evidence: case field `rollback_sql` is empty

## Blast radius

- statements in the corpus that touch the changed objects: 7 (weighted score 21)
- shadow replay: 16/16 statements passed before, 15/16 after
- reproduced failures: 1 · silent column changes: 0 · data-migration failures: 1

| statement | service | engine error |
|---|---|---|
| `q_billing_tax` | billing-api | OperationalError: no such column: tax_rate |

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
ALTER TABLE "subscriptions" ADD COLUMN "billing_interval" TEXT DEFAULT 'monthly';
CREATE INDEX CONCURRENTLY "idx_subscriptions_customer_tmp_nonunique" ON "subscriptions" ("customer_id");
CREATE INDEX CONCURRENTLY "idx_usage_events_name" ON "usage_events" ("event_name");
-- repeat until zero rows are affected (batch size 5000):
UPDATE invoices SET status = 'open' WHERE status = 'draft' AND "id" IN (SELECT "id" FROM "invoices" WHERE status = 'draft' LIMIT 5000);
```

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE "subscriptions" ALTER COLUMN "billing_interval" SET NOT NULL;
CREATE UNIQUE INDEX CONCURRENTLY "idx_subscriptions_customer" ON "subscriptions" ("customer_id");
ALTER TABLE "invoices" DROP COLUMN "tax_rate";
ALTER TABLE subscriptions DROP CONSTRAINT subscriptions_seats_chk;
```

### Rollback for phase 1

```sql
ALTER TABLE "subscriptions" DROP COLUMN "billing_interval";
DROP INDEX CONCURRENTLY "idx_subscriptions_customer_tmp_nonunique";
DROP INDEX CONCURRENTLY "idx_usage_events_name";
```

### Application changes required between the phases

1. deploy code that always writes subscriptions.billing_interval
2. remove every read and write of invoices.tax_rate, then wait one full deploy cycle

### Human decisions required (the tool will not decide these)

- duplicates already exist for subscriptions ("customer_id"); a human must decide the dedupe rule - phase 2 promotes the index to UNIQUE only after that
- confirm invoices.tax_rate has had zero reads for the agreed observation window before phase 2
- dropping subscriptions_seats_chk removes an invariant: the data owner must sign off and a monitoring check should replace it
- statement 6 (unsupported) is outside the tool's model and needs manual review: CLUSTER invoices USING idx_invoices_customer

### Questions for the reviewer

- Which deploy lands first: the query change or the schema change?
- What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
- What is the acceptable write-stall window for this table?
- What enforces this invariant once the constraint is gone?
- What is the accepted risk for MISSING_ROLLBACK?
- What batch size and pause has this table tolerated before?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.
- unmodelled statement: op 6 (unsupported) not modelled structurally: CLUSTER invoices USING idx_invoices_customer

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_12_release_train.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________
