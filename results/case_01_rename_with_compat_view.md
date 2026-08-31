# Migration review: Rename customers.full_name to name and refresh the BI view

**BLOCK - do not merge**

Do not ship this as written. 2 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 3 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. 1 defect(s) in the SQL this packet generated: see the plan self-audit before running any of it. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-case_01_rename_with_compat_view` · case `case_01_rename_with_compat_view` · owning service `web` · 18.7 ms · model scripted-v1 (9 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_web_profile` | replay |
| 2 | **BLOCKER** | Live query breaks after migration | `q_web_signup` | replay |
| 3 | **HIGH** | Impact lands on a service owned by another team | `-` | static |
| 4 | **HIGH** | Destructive change shipped in a single step | `customers.full_name` | static |
| 5 | **HIGH** | SELECT * consumer receives a different column set | `q_bi_summary` | replay |
| 6 | **MEDIUM** | No rollback path supplied | `-` | static |

### 1. [BLOCKER] Live query breaks after migration

q_web_profile fails after the migration: OperationalError: no such column: full_name

- evidence: shadow replay: `SELECT id, email, full_name, plan FROM customers WHERE id = 1` -> OperationalError: no such column: full_name
- services affected: web

### 2. [BLOCKER] Live query breaks after migration

q_web_signup fails after the migration: OperationalError: table customers has no column named full_name

- evidence: shadow replay: `INSERT INTO customers (email, full_name, signed_up_at) VALUES ('new@corp.example','New Person','2026-02-01')` -> OperationalError: table customers has no column named full_name
- services affected: web

### 3. [HIGH] Impact lands on a service owned by another team

the migration is owned by `web` but breakage lands in bi

- evidence: corpus ownership of failing statements: ['bi']
- services affected: bi

### 4. [HIGH] Destructive change shipped in a single step

rename column on customers.full_name lands in a single deploy

- evidence: statement 0: `ALTER TABLE customers RENAME COLUMN full_name TO name`
- prior incidents: INC-2023-09

### 5. [HIGH] SELECT * consumer receives a different column set

q_bi_summary still runs but its column set changes (removed ['full_name'], added ['name'])

- evidence: shadow replay columns before=['id', 'email', 'full_name', 'company_name', 'country_code', 'plan', 'mrr_cents', 'signed_up_at'] after=['id', 'email', 'name', 'company_name', 'country_code', 'plan', 'mrr_cents', 'signed_up_at']
- prior incidents: INC-2025-02
- services affected: bi

### 6. [MEDIUM] No rollback path supplied

the change ships without a rollback script

- evidence: case field `rollback_sql` is empty

## Blast radius

- statements in the corpus that touch the changed objects: 6 (weighted score 17)
- shadow replay: 16/16 statements passed before, 14/16 after
- reproduced failures: 2 · silent column changes: 2 · data-migration failures: 0

| statement | service | engine error |
|---|---|---|
| `q_web_profile` | web | OperationalError: no such column: full_name |
| `q_web_signup` | web | OperationalError: table customers has no column named full_name |

## Recommended rollout

Plan generated on attempt 2 of 2; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 1 - expand (safe to run now)

```sql
ALTER TABLE "customers" ADD COLUMN "name" TEXT;
UPDATE "customers" SET "name" = "full_name" WHERE "name" IS NULL AND "id" IN (SELECT "id" FROM "customers" WHERE "name" IS NULL LIMIT 5000);
```

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE "customers" DROP COLUMN "full_name";
CREATE OR REPLACE VIEW customer_billing_summary AS SELECT id, email, name, company_name, country_code, plan, mrr_cents, signed_up_at FROM customers;
```

### Rollback for phase 1

```sql
ALTER TABLE "customers" DROP COLUMN "name";
```

### Application changes required between the phases

1. deploy code that writes both customers.full_name and customers.name, and reads customers.name
2. point readers at the new definition of customer_billing_summary before phase 2 replaces it

### Human decisions required (the tool will not decide these)

- confirm no consumer still reads customers.full_name before phase 2 drops it
- PLAN DEFECT (ROLLBACK_WINDOW_UNSTATED) in the generated rollback script: the plan states the window - roll back phase 1 only before the code step, and after it use a forward fix instead

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Which deploy lands first: the query change or the schema change?
- Has the owning team agreed to the deploy order?
- What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
- What is the accepted risk for MISSING_ROLLBACK?
- Do any consumers read this result set positionally or serialise it whole?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 5 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

| # | defect | script | statement |
|---|---|---|---|
| 1 | **ROLLBACK_WINDOW_UNSTATED** | rollback | `ALTER TABLE "customers" DROP COLUMN "name"` |

### 1. The rollback is only valid before a code step this same packet asks for

the rollback removes `customers.name`, and a code step in this same packet asks the team to start using it; run them in the printed order and the rollback breaks the deploy the packet asked for. The corpus cannot show this: the statements that break are the ones this packet is asking someone to write.

- evidence: generated rollback statement 0: ALTER TABLE "customers" DROP COLUMN "name"
- evidence: generated code step: deploy code that writes both customers.full_name and customers.name, and reads customers.name
- evidence: shadow replay of this rollback breaks 0 corpus statements, which is why replay alone reports it as safe
- closes when: the plan states the window - roll back phase 1 only before the code step, and after it use a forward fix instead

What this audit trusted rather than checked:

- `customers.full_name` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `customers.full_name`; this audit read the name, not the question
- `customers` (audit_gate_text_only, generated rollback): this step is treated as gated because a human gate names `customers`; this audit read the name, not the question

- shadow replay of the generated phase2 script against the post-phase-1 schema: 2 of 16 corpus statement(s) break (q_web_profile, q_web_signup) - expected for a contract step, which is what the code steps above are for; the number is printed so it can be checked rather than assumed
- shadow replay of the generated rollback script against the post-phase-1 schema: 0 of 16 corpus statement(s) break

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_01_rename_with_compat_view.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 2 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 3 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
