# Migration review: Index invoices.status to speed up the dunning sweep

**BLOCK - do not merge**

Do not ship this as written. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

`run eval-case_03_index_on_hot_table` · case `case_03_index_on_hot_table` · owning service `billing-api` · 6.1 ms · model scripted-v1 (3 calls, $0.0000)

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Index built without CONCURRENTLY on a large table | `invoices` | static |

### 1. [BLOCKER] Index built without CONCURRENTLY on a large table

index idx_invoices_status is built without CONCURRENTLY on invoices (48,000,000 rows, very large)

- evidence: statement 0: `CREATE INDEX idx_invoices_status ON invoices (status)`
- evidence: declared row estimate for invoices: 48,000,000
- prior incidents: INC-2024-07

## Blast radius

- statements in the corpus that touch the changed objects: 6 (weighted score 19)
- shadow replay: 16/16 statements passed before, 16/16 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
CREATE INDEX CONCURRENTLY "idx_invoices_status" ON "invoices" ("status");
```

### Rollback for phase 1

```sql
DROP INDEX CONCURRENTLY "idx_invoices_status";
```

### Questions for the reviewer

- What is the acceptable write-stall window for this table?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_03_index_on_hot_table.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________
