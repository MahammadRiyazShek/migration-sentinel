# Migration review: Enforce unique customer emails

**BLOCK - do not merge**

Do not ship this as written. 1 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-case_05_unique_email_with_duplicates` · case `case_05_unique_email_with_duplicates` · owning service `web` · 13.8 ms · model scripted-v1 (4 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Uniqueness conflicts with data already in the table | `customers.email` | replay |
| 2 | **HIGH** | Index built without CONCURRENTLY on a large table | `customers` | static |

### 1. [BLOCKER] Uniqueness conflicts with data already in the table

Uniqueness on customers.email is violated by rows already in the table

- evidence: shadow backfill: backfill customers: UNIQUE constraint failed: customers.email (row={'id': 3, 'email': 'ada@corp.example', 'full_name': 'Alan Turing', 'company_name': None, 'country_code': 'GB', 'plan': 'free', 'mrr_c
- prior incidents: INC-2025-04

### 2. [HIGH] Index built without CONCURRENTLY on a large table

index idx_customers_email is built without CONCURRENTLY on customers (2,400,000 rows, large)

- evidence: statement 0: `CREATE UNIQUE INDEX idx_customers_email ON customers (email)`
- evidence: declared row estimate for customers: 2,400,000
- prior incidents: INC-2024-07

## Blast radius

- statements in the corpus that touch the changed objects: 6 (weighted score 17)
- shadow replay: 16/16 statements passed before, 16/16 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 1

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 1 - expand (safe to run now)

```sql
CREATE INDEX CONCURRENTLY "idx_customers_email_tmp_nonunique" ON "customers" ("email");
```

### Phase 2 - contract (only after the code steps below)

```sql
CREATE UNIQUE INDEX CONCURRENTLY "idx_customers_email" ON "customers" ("email");
```

### Rollback for phase 1

```sql
DROP INDEX CONCURRENTLY "idx_customers_email_tmp_nonunique";
```

### Human decisions required (the tool will not decide these)

- duplicates already exist for customers ("email"); a human must decide the dedupe rule - phase 2 promotes the index to UNIQUE only after that

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the acceptable write-stall window for this table?
- Who owns cleaning the duplicate rows, and by when?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 3 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.

- shadow replay of the generated phase2 script against the post-phase-1 schema: 0 of 16 corpus statement(s) break
- shadow replay of the generated rollback script against the post-phase-1 schema: 0 of 16 corpus statement(s) break

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_05_unique_email_with_duplicates.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 1 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
