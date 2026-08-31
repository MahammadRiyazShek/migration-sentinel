# Migration review: Add a concurrent unique index on invoices.invoice_number

**SAFE - no blocking hazards found**

No blocking hazards found. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

`run eval-case_06_safe_unique_index` · case `case_06_safe_unique_index` · owning service `billing-api` · 10.2 ms · model scripted-v1 (2 calls, $0.0000)

## Hazards

No hazards found by execution or by the static rules.

## Blast radius

- statements in the corpus that touch the changed objects: 5 (weighted score 16)
- shadow replay: 16/16 statements passed before, 16/16 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
CREATE UNIQUE INDEX CONCURRENTLY "idx_invoices_number" ON "invoices" ("invoice_number");
```

### Rollback for phase 1

```sql
DROP INDEX CONCURRENTLY "idx_invoices_number";
```

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_06_safe_unique_index.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________
