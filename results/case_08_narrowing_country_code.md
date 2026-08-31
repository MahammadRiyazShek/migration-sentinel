# Migration review: Narrow customers.country_code to varchar(2)

**BLOCK - do not merge**

Do not ship this as written. 1 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

`run eval-case_08_narrowing_country_code` · case `case_08_narrowing_country_code` · owning service `web` · 9.1 ms · model scripted-v1 (4 calls, $0.0000)

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Narrowing type change can silently lose data | `customers.country_code` | replay |
| 2 | **HIGH** | Type change forces a full table rewrite | `customers.country_code` | static |

### 1. [BLOCKER] Narrowing type change can silently lose data

customers.country_code TEXT -> varchar(2) would not survive 1/4 fixture rows

- evidence: value scan offenders=['USA']

### 2. [HIGH] Type change forces a full table rewrite

customers.country_code -> varchar(2) forces a rewrite of a large table (2,400,000 rows)

- evidence: statement 0: `ALTER TABLE customers ALTER COLUMN country_code TYPE varchar(2)`

## Blast radius

- statements in the corpus that touch the changed objects: 6 (weighted score 17)
- shadow replay: 16/16 statements passed before, 16/16 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 2 - contract (only after the code steps below)

```sql
-- blocked pending human decision: ALTER TABLE customers ALTER COLUMN country_code TYPE varchar(2);
```

### Human decisions required (the tool will not decide these)

- customers.country_code -> varchar(2) loses data for rows that exist today; a human must approve the truncation rule or widen the target type

### Questions for the reviewer

- What is the accepted risk for TABLE_REWRITE_LOCK?
- Is the truncated value recoverable from anywhere else?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_08_narrowing_country_code.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________
