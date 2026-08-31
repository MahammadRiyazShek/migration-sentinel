# Migration review: The same index swap, outside a transaction: a correct migration

**SAFE - no blocking hazards found**

No blocking hazards found. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-rt_07_index_swap_done_right` · case `rt_07_index_swap_done_right` · owning service `platform` · 11.4 ms · model scripted-v1 (2 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

No hazards found by execution or by the static rules.

## Blast radius

- statements in the corpus that touch the changed objects: 9 (weighted score 28)
- shadow replay: 19/19 statements passed before, 19/19 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 1 - expand (safe to run now)

```sql
DROP INDEX CONCURRENTLY idx_invoices_customer;
CREATE INDEX CONCURRENTLY "idx_invoices_customer_status" ON "invoices" ("customer_id", "status");
```

### Rollback for phase 1

```sql
DROP INDEX CONCURRENTLY "idx_invoices_customer_status";
```

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 3 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.

- shadow replay of the generated rollback script against the post-phase-1 schema: 0 of 19 corpus statement(s) break

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/rt_07_index_swap_done_right.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> No blocking hazards found. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
