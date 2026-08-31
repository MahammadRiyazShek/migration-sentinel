# Migration review: Drop the shipments status CHECK constraint

**SHIP AS PLAN - not as written**

Shippable, but only as the staged plan below. 0 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-holdout_05_drop_status_check` · case `holdout_05_drop_status_check` · owning service `dispatch-api` · 9.0 ms · model scripted-v1 (3 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **HIGH** | Data-integrity constraint removed | `shipments` | static |

### 1. [HIGH] Data-integrity constraint removed

shipments_status_chk (check) is dropped from shipments; no query breaks today, invalid rows become possible tomorrow

- evidence: statement 0: `ALTER TABLE shipments DROP CONSTRAINT shipments_status_chk`
- evidence: constraint text: (status IN ('planned','in_transit','delivered','cancelled'))

## Blast radius

- statements in the corpus that touch the changed objects: 5 (weighted score 17)
- shadow replay: 17/17 statements passed before, 17/17 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE shipments DROP CONSTRAINT shipments_status_chk;
```

### Human decisions required (the tool will not decide these)

- dropping shipments_status_chk removes an invariant: the data owner must sign off and a monitoring check should replace it

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What enforces this invariant once the constraint is gone?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/holdout_05_drop_status_check.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Shippable, but only as the staged plan below. 0 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
