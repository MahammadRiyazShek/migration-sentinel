# Migration review: Add a concurrent index from inside the framework's DDL transaction

**BLOCK - do not merge**

Do not ship this as written. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-rt_02_concurrently_inside_transaction` · case `rt_02_concurrently_inside_transaction` · owning service `platform` · 5.8 ms · model scripted-v1 (3 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | CONCURRENTLY used inside a transaction block | `idx_usage_events_customer` | static |

### 1. [BLOCKER] CONCURRENTLY used inside a transaction block

statement 1 uses CONCURRENTLY inside the transaction opened at statement 0; Postgres refuses this and the deploy fails on the statement itself

- evidence: statement 0: `BEGIN`
- evidence: statement 1: `CREATE INDEX CONCURRENTLY idx_usage_events_customer ON usage_events (customer_id)`
- evidence: ERROR: CREATE INDEX CONCURRENTLY cannot run inside a transaction block (Postgres, all supported versions)

## Blast radius

- statements in the corpus that touch the changed objects: 7 (weighted score 22)
- shadow replay: 19/19 statements passed before, 19/19 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
CREATE INDEX CONCURRENTLY "idx_usage_events_customer" ON "usage_events" ("customer_id");
```

### Rollback for phase 1

```sql
DROP INDEX CONCURRENTLY "idx_usage_events_customer";
```

### Application changes required between the phases

1. run phase 1 with the framework's DDL transaction disabled (Rails disable_ddl_transaction!, Django atomic = False, Alembic autocommit block): CONCURRENTLY cannot run inside a transaction block

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the accepted risk for CONCURRENT_DDL_IN_TRANSACTION?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/rt_02_concurrently_inside_transaction.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
