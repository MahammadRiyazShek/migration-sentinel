# Migration review: Add the missing invoices -> customers foreign key

**BLOCK - do not merge**

Do not ship this as written. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. 1 defect(s) in the SQL this packet generated: see the plan self-audit before running any of it. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-case_10_add_fk_constraint` · case `case_10_add_fk_constraint` · owning service `billing-api` · 13.0 ms · model scripted-v1 (3 calls, $0.0000)

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

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

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

### Human decisions required (the tool will not decide these)

- PLAN DEFECT (CONTRACT_STEP_UNGATED) in the generated phase2 script: the plan carries a gate naming this object, or the statement moves out of the generated script

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the accepted risk for CONSTRAINT_VALIDATION_LOCK?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 3 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

| # | defect | script | statement |
|---|---|---|---|
| 1 | **CONTRACT_STEP_UNGATED** | phase2 | `ALTER TABLE "invoices" VALIDATE CONSTRAINT "invoices_customer_fk"` |

### 1. A contract step this pipeline generated has no human gate

a `validate_constraint` this pipeline wrote into phase 2 is not named by any human gate, so the packet asks someone to run a destructive statement it never asked anyone to decide about.

- evidence: generated phase 2 statement 0: ALTER TABLE "invoices" VALIDATE CONSTRAINT "invoices_customer_fk"
- evidence: human gates in this packet: 0, none naming invoices
- evidence: rule inventory: `validate_constraint` is RESIDUAL on the input side - the second half of a NOT VALID split takes its own lock over the whole relation and no rule prices it against the row estimate
- closes when: the plan carries a gate naming this object, or the statement moves out of the generated script

What this audit trusted rather than checked:

- `invoices` (unruled_generated_statement, generated phase2): this pipeline generated a statement of a kind nothing in this pipeline inspects: the second half of a NOT VALID split takes its own lock over the whole relation and no rule prices it against the row estimate

- shadow replay of the generated phase2 script against the post-phase-1 schema: 0 of 16 corpus statement(s) break
- shadow replay of the generated rollback script against the post-phase-1 schema: 0 of 16 corpus statement(s) break

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
