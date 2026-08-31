# Migration review: Release train: six changes in one migration

**BLOCK - do not merge**

Do not ship this as written. 2 coverage gap(s) need a named sign-off before this can be called safe. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 3 blocker, 5 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. 1 defect(s) in the SQL this packet generated: see the plan self-audit before running any of it. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run run-cd8ced97` · case `case_12_release_train` · owning service `billing-api` · 21.8 ms · model scripted-v1 (11 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_billing_tax` | replay |
| 2 | **BLOCKER** | Index built without CONCURRENTLY on a large table | `usage_events` | static |
| 3 | **BLOCKER** | Uniqueness conflicts with data already in the table | `subscriptions.customer_id` | replay |
| 4 | **HIGH** | Destructive change shipped in a single step | `invoices.tax_rate` | static |
| 5 | **HIGH** | Index built without CONCURRENTLY on a large table | `subscriptions` | static |
| 6 | **HIGH** | Data-integrity constraint removed | `subscriptions` | static |
| 7 | **HIGH** | Type change forces a full table rewrite | `invoices` | static |
| 8 | **HIGH** | Backfill runs as one unbounded statement | `invoices` | static |
| 9 | **MEDIUM** | No rollback path supplied | `-` | static |

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

### 7. [HIGH] Type change forces a full table rewrite

CLUSTER rewrites invoices under an ACCESS EXCLUSIVE lock (48,000,000 rows, very large)

- evidence: statement 6: `CLUSTER invoices USING idx_invoices_customer`
- evidence: declared row estimate for invoices: 48,000,000
- evidence: recognised as a whole-relation maintenance command; the statement itself is still not modelled structurally and stays in the coverage ledger

### 8. [HIGH] Backfill runs as one unbounded statement

backfill on invoices runs as one statement over 48,000,000 rows

- evidence: statement 5: `UPDATE invoices SET status = 'open' WHERE status = 'draft'`

### 9. [MEDIUM] No rollback path supplied

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

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

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
- statement 6 (maintenance_rewrite) is outside the tool's model and needs manual review: CLUSTER invoices USING idx_invoices_customer
- coverage gap on `invoices.status` (in_place_data_mutation): a reviewer confirms which consumers of invoices.status depend on the current values
- coverage gap on `invoices` (unmodelled_statement): a reviewer confirms by hand what statement 6 does to invoices and to anything reading it
- PLAN DEFECT (ROLLBACK_WINDOW_UNSTATED) in the generated rollback script: the plan states the window - roll back phase 1 only before the code step, and after it use a forward fix instead

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Which deploy lands first: the query change or the schema change?
- What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
- What is the acceptable write-stall window for this table?
- What enforces this invariant once the constraint is gone?
- What is the accepted risk for MISSING_ROLLBACK?
- What is the accepted risk for TABLE_REWRITE_LOCK?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 11 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

| # | defect | script | statement |
|---|---|---|---|
| 1 | **ROLLBACK_WINDOW_UNSTATED** | rollback | `ALTER TABLE "subscriptions" DROP COLUMN "billing_interval"` |

### 1. The rollback is only valid before a code step this same packet asks for

the rollback removes `subscriptions.billing_interval`, and a code step in this same packet asks the team to start using it; run them in the printed order and the rollback breaks the deploy the packet asked for. The corpus cannot show this: the statements that break are the ones this packet is asking someone to write.

- evidence: generated rollback statement 0: ALTER TABLE "subscriptions" DROP COLUMN "billing_interval"
- evidence: generated code step: deploy code that always writes subscriptions.billing_interval
- evidence: shadow replay of this rollback breaks 0 corpus statements, which is why replay alone reports it as safe
- closes when: the plan states the window - roll back phase 1 only before the code step, and after it use a forward fix instead

What this audit trusted rather than checked:

- `subscriptions` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `subscriptions`; this audit read the name, not the question
- `invoices.tax_rate` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `invoices.tax_rate`; this audit read the name, not the question
- `subscriptions` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `subscriptions`; this audit read the name, not the question
- `subscriptions` (audit_gate_text_only, generated rollback): this step is treated as gated because a human gate names `subscriptions`; this audit read the name, not the question

- shadow replay of the generated phase2 script against the post-phase-1 schema: 1 of 16 corpus statement(s) break (q_billing_tax) - expected for a contract step, which is what the code steps above are for; the number is printed so it can be checked rather than assumed
- shadow replay of the generated rollback script against the post-phase-1 schema: 0 of 16 corpus statement(s) break

## Coverage ledger

2 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `invoices.status` | existing rows rewritten; replay cannot see changed answers | rows that already exist in invoices are rewritten; replay proves the corpus still executes, never that it still returns the same answer | a reviewer confirms which consumers of invoices.status depend on the current values |
| `invoices` | statement not modelled by the parser | the parser produced no structural model for this statement, so no post-migration schema and no replay covers it | a reviewer confirms by hand what statement 6 does to invoices and to anything reading it |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.
- unmodelled statement: op 6 (maintenance_rewrite) not modelled structurally: CLUSTER invoices USING idx_invoices_customer

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_12_release_train.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 2 coverage gap(s) need a named sign-off before this can be called safe. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 3 blocker, 5 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
