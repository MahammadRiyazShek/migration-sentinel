# Migration review: Normalise the invoice currency default, then retire the unused tax column

**BLOCK - do not merge**

Do not ship this as written. 1 coverage gap(s) need a named sign-off before this can be called safe. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 3 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-rt2_01_comment_marker_inside_literal` · case `rt2_01_comment_marker_inside_literal` · owning service `platform` · 13.4 ms · model scripted-v1 (6 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_billing_tax` | replay |
| 2 | **HIGH** | Impact lands on a service owned by another team | `-` | static |
| 3 | **HIGH** | Destructive change shipped in a single step | `invoices.tax_rate` | static |
| 4 | **HIGH** | Backfill runs as one unbounded statement | `invoices` | static |

### 1. [BLOCKER] Live query breaks after migration

q_billing_tax fails after the migration: OperationalError: no such column: tax_rate

- evidence: shadow replay: `SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1` -> OperationalError: no such column: tax_rate
- services affected: billing-api

### 2. [HIGH] Impact lands on a service owned by another team

the migration is owned by `platform` but breakage lands in billing-api

- evidence: corpus ownership of failing statements: ['billing-api']
- services affected: billing-api

### 3. [HIGH] Destructive change shipped in a single step

drop column on invoices.tax_rate lands in a single deploy

- evidence: statement 1: `ALTER TABLE invoices DROP COLUMN tax_rate`
- prior incidents: INC-2023-09

### 4. [HIGH] Backfill runs as one unbounded statement

backfill on invoices runs as one statement over 48,000,000 rows

- evidence: statement 0: `UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL`

## Blast radius

- statements in the corpus that touch the changed objects: 8 (weighted score 25)
- shadow replay: 19/19 statements passed before, 18/19 after
- reproduced failures: 1 · silent column changes: 0 · data-migration failures: 0

| statement | service | engine error |
|---|---|---|
| `q_billing_tax` | billing-api | OperationalError: no such column: tax_rate |

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 1 - expand (safe to run now)

```sql
-- repeat until zero rows are affected (batch size 5000):
UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL AND "id" IN (SELECT "id" FROM "invoices" WHERE currency IS NULL LIMIT 5000);
```

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE "invoices" DROP COLUMN "tax_rate";
```

### Application changes required between the phases

1. remove every read and write of invoices.tax_rate, then wait one full deploy cycle

### Human decisions required (the tool will not decide these)

- confirm invoices.tax_rate has had zero reads for the agreed observation window before phase 2
- coverage gap on `invoices.currency` (in_place_data_mutation): a reviewer confirms which consumers of invoices.currency depend on the current values

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Which deploy lands first: the query change or the schema change?
- Has the owning team agreed to the deploy order?
- What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
- What batch size and pause has this table tolerated before?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 2 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.

What this audit trusted rather than checked:

- `invoices.tax_rate` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `invoices.tax_rate`; this audit read the name, not the question

- shadow replay of the generated phase2 script against the post-phase-1 schema: 1 of 19 corpus statement(s) break (q_billing_tax) - expected for a contract step, which is what the code steps above are for; the number is printed so it can be checked rather than assumed

## Coverage ledger

1 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `invoices.currency` | existing rows rewritten; replay cannot see changed answers | rows that already exist in invoices are rewritten; replay proves the corpus still executes, never that it still returns the same answer | a reviewer confirms which consumers of invoices.currency depend on the current values |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/rt2_01_comment_marker_inside_literal.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 1 coverage gap(s) need a named sign-off before this can be called safe. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 3 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
