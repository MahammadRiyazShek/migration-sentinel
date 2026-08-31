# Migration review: Enforce one invoice number per carrier

**BLOCK - do not merge**

Do not ship this as written. 2 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-holdout_02_composite_unique_invoices` · case `holdout_02_composite_unique_invoices` · owning service `finance-ops` · 6.4 ms · model scripted-v1 (4 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Index built without CONCURRENTLY on a large table | `carrier_invoices` | static |
| 2 | **BLOCKER** | Uniqueness conflicts with data already in the table | `carrier_invoices.carrier_id` | replay |

### 1. [BLOCKER] Index built without CONCURRENTLY on a large table

index idx_carrier_invoices_number is built without CONCURRENTLY on carrier_invoices (9,400,000 rows, very large)

- evidence: statement 0: `CREATE UNIQUE INDEX idx_carrier_invoices_number ON carrier_invoices (carrier_id, invoice_number)`
- evidence: declared row estimate for carrier_invoices: 9,400,000
- prior incidents: INC-2024-07

### 2. [BLOCKER] Uniqueness conflicts with data already in the table

Uniqueness on carrier_invoices.carrier_id is violated by rows already in the table

- evidence: shadow backfill: backfill carrier_invoices: UNIQUE constraint failed: carrier_invoices.carrier_id, carrier_invoices.invoice_number (row={'id': 4, 'carrier_id': 8, 'invoice_number': 'MRLN-88', 'shipment_id': None, 'amo
- prior incidents: INC-2025-04

## Blast radius

- statements in the corpus that touch the changed objects: 5 (weighted score 14)
- shadow replay: 17/17 statements passed before, 17/17 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 1

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
CREATE INDEX CONCURRENTLY "idx_carrier_invoices_number_tmp_nonunique" ON "carrier_invoices" ("carrier_id", "invoice_number");
```

### Phase 2 - contract (only after the code steps below)

```sql
CREATE UNIQUE INDEX CONCURRENTLY "idx_carrier_invoices_number" ON "carrier_invoices" ("carrier_id", "invoice_number");
```

### Rollback for phase 1

```sql
DROP INDEX CONCURRENTLY "idx_carrier_invoices_number_tmp_nonunique";
```

### Human decisions required (the tool will not decide these)

- duplicates already exist for carrier_invoices ("carrier_id", "invoice_number"); a human must decide the dedupe rule - phase 2 promotes the index to UNIQUE only after that

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the acceptable write-stall window for this table?
- Who owns cleaning the duplicate rows, and by when?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/holdout_02_composite_unique_invoices.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 2 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
