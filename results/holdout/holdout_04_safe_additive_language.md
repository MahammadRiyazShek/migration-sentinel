# Migration review: Add drivers.preferred_language and index drivers.carrier_id concurrently

**SAFE - no blocking hazards found**

No blocking hazards found. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-holdout_04_safe_additive_language` · case `holdout_04_safe_additive_language` · owning service `dispatch-api` · 9.4 ms · model scripted-v1 (2 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

No hazards found by execution or by the static rules.

## Blast radius

- statements in the corpus that touch the changed objects: 7 (weighted score 20)
- shadow replay: 17/17 statements passed before, 17/17 after
- reproduced failures: 0 · silent column changes: 2 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 1 - expand (safe to run now)

```sql
ALTER TABLE "drivers" ADD COLUMN "preferred_language" TEXT;
CREATE INDEX CONCURRENTLY "idx_drivers_carrier" ON "drivers" ("carrier_id");
```

### Rollback for phase 1

```sql
ALTER TABLE "drivers" DROP COLUMN "preferred_language";
DROP INDEX CONCURRENTLY "idx_drivers_carrier";
```

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/holdout_04_safe_additive_language.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> No blocking hazards found. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
