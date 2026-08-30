# Migration review: Drop customers.company_name after the product decision to remove it

**BLOCK - do not merge**

Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 3 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

`run eval-case_02_drop_column_still_read` · case `case_02_drop_column_still_read` · owning service `web` · 6.4 ms · model scripted-v1 (7 calls, $0.0000)

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_support_lookup` | replay |
| 2 | **HIGH** | Impact lands on a service owned by another team | `-` | static |
| 3 | **HIGH** | Destructive change shipped in a single step | `customers.company_name` | static |
| 4 | **HIGH** | SELECT * consumer receives a different column set | `q_bi_summary` | replay |
| 5 | **MEDIUM** | No rollback path supplied | `-` | static |

### 1. [BLOCKER] Live query breaks after migration

q_support_lookup fails after the migration: OperationalError: no such column: company_name

- evidence: shadow replay: `SELECT id, email, company_name FROM customers WHERE email = 'ada@corp.example'` -> OperationalError: no such column: company_name
- services affected: support-admin

### 2. [HIGH] Impact lands on a service owned by another team

the migration is owned by `web` but breakage lands in bi, support-admin

- evidence: corpus ownership of failing statements: ['bi', 'support-admin']
- services affected: bi, support-admin

### 3. [HIGH] Destructive change shipped in a single step

drop column on customers.company_name lands in a single deploy

- evidence: statement 0: `ALTER TABLE customers DROP COLUMN company_name`
- prior incidents: INC-2023-09

### 4. [HIGH] SELECT * consumer receives a different column set

q_bi_summary still runs but its column set changes (removed ['company_name'], added none)

- evidence: shadow replay columns before=['id', 'email', 'full_name', 'company_name', 'country_code', 'plan', 'mrr_cents', 'signed_up_at'] after=['id', 'email', 'full_name', 'country_code', 'plan', 'mrr_cents', 'signed_up_at']
- prior incidents: INC-2025-02
- services affected: bi

### 5. [MEDIUM] No rollback path supplied

the change ships without a rollback script

- evidence: case field `rollback_sql` is empty

## Blast radius

- statements in the corpus that touch the changed objects: 6 (weighted score 17)
- shadow replay: 16/16 statements passed before, 15/16 after
- reproduced failures: 1 · silent column changes: 2 · data-migration failures: 0

| statement | service | engine error |
|---|---|---|
| `q_support_lookup` | support-admin | OperationalError: no such column: company_name |

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE "customers" DROP COLUMN "company_name";
```

### Application changes required between the phases

1. remove every read and write of customers.company_name, then wait one full deploy cycle

### Human decisions required (the tool will not decide these)

- confirm customers.company_name has had zero reads for the agreed observation window before phase 2
- no rollback could be generated automatically; write one before shipping

### Questions for the reviewer

- Which deploy lands first: the query change or the schema change?
- Has the owning team agreed to the deploy order?
- What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
- What is the accepted risk for MISSING_ROLLBACK?
- Do any consumers read this result set positionally or serialise it whole?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_02_drop_column_still_read.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________
