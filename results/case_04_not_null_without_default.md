# Migration review: Add customers.billing_email as NOT NULL

**BLOCK - do not merge**

Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-case_04_not_null_without_default` · case `case_04_not_null_without_default` · owning service `billing-api` · 7.5 ms · model scripted-v1 (5 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_web_signup` | replay |
| 2 | **BLOCKER** | NOT NULL added without a usable default | `customers.billing_email` | replay |
| 3 | **HIGH** | Impact lands on a service owned by another team | `-` | static |

### 1. [BLOCKER] Live query breaks after migration

q_web_signup fails after the migration: IntegrityError: NOT NULL constraint failed: customers.billing_email

- evidence: shadow replay: `INSERT INTO customers (email, full_name, signed_up_at) VALUES ('new@corp.example','New Person','2026-02-01')` -> IntegrityError: NOT NULL constraint failed: customers.billing_email
- services affected: web

### 2. [BLOCKER] NOT NULL added without a usable default

Existing rows cannot satisfy NOT NULL on customers.billing_email

- evidence: shadow backfill: backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 1, 'email': 'ada@corp.example', 'full_name': 'Ada Lovelace', 'company_name': 'Corp', 'country_code': 'US', 'plan': '
- evidence: shadow backfill: backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 2, 'email': 'grace@corp.example', 'full_name': 'Grace Hopper', 'company_name': 'Corp', 'country_code': 'USA', 'plan'
- evidence: shadow backfill: backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 3, 'email': 'alan@lab.example', 'full_name': 'Alan Turing', 'company_name': None, 'country_code': 'GB', 'plan': 'fre
- evidence: shadow backfill: backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 4, 'email': 'katherine@nasa.example', 'full_name': 'Katherine Johnson', 'company_name': 'NASA', 'country_code': 'US'
- evidence: statement 0: `ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL`

### 3. [HIGH] Impact lands on a service owned by another team

the migration is owned by `billing-api` but breakage lands in web

- evidence: corpus ownership of failing statements: ['web']
- services affected: web

## Blast radius

- statements in the corpus that touch the changed objects: 6 (weighted score 17)
- shadow replay: 16/16 statements passed before, 15/16 after
- reproduced failures: 1 · silent column changes: 2 · data-migration failures: 4

| statement | service | engine error |
|---|---|---|
| `q_web_signup` | web | IntegrityError: NOT NULL constraint failed: customers.billing_email |

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
ALTER TABLE "customers" ADD COLUMN "billing_email" TEXT;
```

### Phase 2 - contract (only after the code steps below)

```sql
-- after backfill: ALTER TABLE "customers" ALTER COLUMN "billing_email" SET NOT NULL;
```

### Rollback for phase 1

```sql
ALTER TABLE "customers" DROP COLUMN "billing_email";
```

### Human decisions required (the tool will not decide these)

- customers.billing_email is NOT NULL with no default: a human must supply a backfill value before phase 2 can add the constraint

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Which deploy lands first: the query change or the schema change?
- Has the owning team agreed to the deploy order?
- What is the accepted risk for NOT_NULL_NO_DEFAULT?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_04_not_null_without_default.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
