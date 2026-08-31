# Migration review: Add the missing invoices -> customers foreign key

**BLOCK - do not merge**

Do not ship this as written. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-case_10_add_fk_constraint` · case `case_10_add_fk_constraint` · owning service `billing-api` · 7.2 ms · model scripted-v1 (3 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Constraint added without NOT VALID / VALIDATE split | `invoices` | static+memory |

### 1. [BLOCKER] Constraint added without NOT VALID / VALIDATE split

invoices_customer_fk is added without NOT VALID, so validation scans all 48,000,000 rows under a lock

- evidence: statement 0: `ALTER TABLE invoices ADD CONSTRAINT invoices_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (id)`
- evidence: severity raised high -> blocker by prior incident(s) INC-2024-11
- prior incidents: INC-2024-11

## Blast radius

- statements in the corpus that touch the changed objects: 5 (weighted score 16)
- shadow replay: 16/16 statements passed before, 16/16 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
ALTER TABLE "invoices" ADD CONSTRAINT "invoices_customer_fk" FOREIGN KEY (customer_id) REFERENCES customers (id) NOT VALID;
```

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE "invoices" VALIDATE CONSTRAINT "invoices_customer_fk";
```

### Rollback for phase 1

```sql
ALTER TABLE "invoices" DROP CONSTRAINT "invoices_customer_fk";
```

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the accepted risk for CONSTRAINT_VALIDATION_LOCK?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_10_add_fk_constraint.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
