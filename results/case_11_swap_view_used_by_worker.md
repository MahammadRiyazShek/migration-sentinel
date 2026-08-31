# Migration review: Replace the open_invoices view with a v2 definition

**BLOCK - do not merge**

Do not ship this as written. 2 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 1 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

`run eval-case_11_swap_view_used_by_worker` · case `case_11_swap_view_used_by_worker` · owning service `billing-api` · 8.4 ms · model scripted-v1 (5 calls, $0.0000)

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_dunning_open` | replay |
| 2 | **HIGH** | Impact lands on a service owned by another team | `-` | static |
| 3 | **MEDIUM** | No rollback path supplied | `-` | static |

### 1. [BLOCKER] Live query breaks after migration

q_dunning_open fails after the migration: OperationalError: no such table: open_invoices

- evidence: shadow replay: `SELECT * FROM open_invoices` -> OperationalError: no such table: open_invoices
- services affected: dunning-worker

### 2. [HIGH] Impact lands on a service owned by another team

the migration is owned by `billing-api` but breakage lands in dunning-worker

- evidence: corpus ownership of failing statements: ['dunning-worker']
- services affected: dunning-worker

### 3. [MEDIUM] No rollback path supplied

the change ships without a rollback script

- evidence: case field `rollback_sql` is empty

## Blast radius

- statements in the corpus that touch the changed objects: 1 (weighted score 4)
- shadow replay: 16/16 statements passed before, 15/16 after
- reproduced failures: 2 · silent column changes: 0 · data-migration failures: 0

| statement | service | engine error |
|---|---|---|
| `q_dunning_open` | dunning-worker | OperationalError: no such table: open_invoices |
| `__view__open_invoices` | database | object removed by migration (view or table no longer exists) |

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open');
```

### Phase 2 - contract (only after the code steps below)

```sql
DROP VIEW open_invoices;
```

### Human decisions required (the tool will not decide these)

- confirm nothing reads open_invoices before phase 2 removes it
- no rollback could be generated automatically; write one before shipping

### Questions for the reviewer

- Which deploy lands first: the query change or the schema change?
- Has the owning team agreed to the deploy order?
- What is the accepted risk for MISSING_ROLLBACK?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_11_swap_view_used_by_worker.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________
