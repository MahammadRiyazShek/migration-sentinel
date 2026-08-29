# Migration review: Drop the plan CHECK constraint to allow new plan names

**SHIP AS PLAN - not as written**

Shippable, but only as the staged plan below. 0 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

`run eval-case_07_drop_check_constraint` · case `case_07_drop_check_constraint` · owning service `billing-api` · 6.1 ms · model scripted-v1 (3 calls, $0.0000)

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **HIGH** | Data-integrity constraint removed | `customers` | static |

### 1. [HIGH] Data-integrity constraint removed

customers_plan_chk (check) is dropped from customers; no query breaks today, invalid rows become possible tomorrow

- evidence: statement 0: `ALTER TABLE customers DROP CONSTRAINT customers_plan_chk`
- evidence: constraint text: (plan IN ('free','team','business','enterprise'))

## Blast radius

- statements in the corpus that touch the changed objects: 6 (weighted score 17)
- shadow replay: 16/16 statements passed before, 16/16 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE customers DROP CONSTRAINT customers_plan_chk;
```

### Human decisions required (the tool will not decide these)

- dropping customers_plan_chk removes an invariant: the data owner must sign off and a monitoring check should replace it

### Questions for the reviewer

- What enforces this invariant once the constraint is gone?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_07_drop_check_constraint.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________
