# Migration review: Narrow carrier_invoices.amount to numeric(8,2)

**NOT CLEARED - coverage gap on an affected object**

Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 1 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-holdout_07_narrow_invoice_amount` · case `holdout_07_narrow_invoice_amount` · owning service `finance-ops` · 8.2 ms · model scripted-v1 (4 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

> **Not cleared on coverage.** The hazards found here are not blocking, but 1 object(s) this migration touches sit inside a blind spot of the review. The verdict is capped rather than clean: no hazard has been invented, and nothing has been certified either. See *Coverage ledger* below.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **HIGH** | Type change forces a full table rewrite | `carrier_invoices.amount` | static |
| 2 | **MEDIUM** | Narrowing type change can silently lose data | `carrier_invoices.amount` | replay |

### 1. [HIGH] Type change forces a full table rewrite

carrier_invoices.amount -> numeric(8,2) forces a rewrite of a very large table (9,400,000 rows)

- evidence: statement 0: `ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2)`

### 2. [MEDIUM] Narrowing type change can silently lose data

carrier_invoices.amount NUMERIC(12,2) -> numeric(8,2) would not survive 0/5 fixture rows

- evidence: value scan offenders=[]

## Blast radius

- statements in the corpus that touch the changed objects: 2 (weighted score 5)
- shadow replay: 17/17 statements passed before, 17/17 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
ALTER TABLE "carrier_invoices" ADD COLUMN "amount_new" numeric(8,2);
UPDATE "carrier_invoices" SET "amount_new" = "amount" WHERE "amount_new" IS NULL AND "id" IN (SELECT "id" FROM "carrier_invoices" WHERE "amount_new" IS NULL LIMIT 5000);
```

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE "carrier_invoices" DROP COLUMN "amount";
ALTER TABLE "carrier_invoices" RENAME COLUMN "amount_new" TO "amount";
```

### Rollback for phase 1

```sql
ALTER TABLE "carrier_invoices" DROP COLUMN "amount_new";
```

### Application changes required between the phases

1. deploy code that dual-writes carrier_invoices.amount and carrier_invoices.amount_new

### Human decisions required (the tool will not decide these)

- IRREVERSIBLE - coverage gap on `carrier_invoices.amount` (fixture_bounded_value_scan): a reviewer counts the real offenders before phase 2: SELECT count(*) FROM carrier_invoices WHERE amount would not fit numeric(8,2)

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the accepted risk for TABLE_REWRITE_LOCK?
- Is the truncated value recoverable from anywhere else?

## Coverage ledger

1 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `carrier_invoices.amount` **(irreversible)** | fixture_bounded_value_scan | the value scan for carrier_invoices.amount -> numeric(8,2) ran over 5 fixture row(s) against a declared 9,400,000 in production and found nothing that would be refused; that is a fact about the fixture, not about the column, and the rollback restores the type without the values | a reviewer counts the real offenders before phase 2: SELECT count(*) FROM carrier_invoices WHERE amount would not fit numeric(8,2) |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/holdout_07_narrow_invoice_amount.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 1 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
