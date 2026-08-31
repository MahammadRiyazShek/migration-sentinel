# Migration review: Drop customers.company_name after the product decision to remove it

**BLOCK - do not merge**

Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 3 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-case_02_drop_column_still_read` · case `case_02_drop_column_still_read` · owning service `web` · 10.7 ms · model scripted-v1 (7 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

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

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE "customers" DROP COLUMN "company_name";
```

### Application changes required between the phases

1. remove every read and write of customers.company_name, then wait one full deploy cycle

### Human decisions required (the tool will not decide these)

- confirm customers.company_name has had zero reads for the agreed observation window before phase 2
- no rollback could be generated automatically; write one before shipping

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Which deploy lands first: the query change or the schema change?
- Has the owning team agreed to the deploy order?
- What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
- What is the accepted risk for MISSING_ROLLBACK?
- Do any consumers read this result set positionally or serialise it whole?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 1 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.

What this audit trusted rather than checked:

- `customers.company_name` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `customers.company_name`; this audit read the name, not the question

- shadow replay of the generated phase2 script against the post-phase-1 schema: 1 of 16 corpus statement(s) break (q_support_lookup) - expected for a contract step, which is what the code steps above are for; the number is printed so it can be checked rather than assumed

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

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 3 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
