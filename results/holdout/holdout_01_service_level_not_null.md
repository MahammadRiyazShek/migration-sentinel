# Migration review: Add shipments.service_level as NOT NULL

**BLOCK - do not merge**

Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-holdout_01_service_level_not_null` · case `holdout_01_service_level_not_null` · owning service `dispatch-api` · 15.4 ms · model scripted-v1 (4 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_dispatch_create` | replay |
| 2 | **BLOCKER** | NOT NULL added without a usable default | `shipments.service_level` | replay |

### 1. [BLOCKER] Live query breaks after migration

q_dispatch_create fails after the migration: IntegrityError: NOT NULL constraint failed: shipments.service_level

- evidence: shadow replay: `INSERT INTO shipments (carrier_id, reference, status, weight_kg, promised_at) VALUES (7,'SHP-77001','planned',1200,'2026` -> IntegrityError: NOT NULL constraint failed: shipments.service_level
- services affected: dispatch-api

### 2. [BLOCKER] NOT NULL added without a usable default

Existing rows cannot satisfy NOT NULL on shipments.service_level

- evidence: shadow backfill: backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 1, 'carrier_id': 7, 'vehicle_id': 1, 'parent_shipment_id': None, 'reference': 'SHP-10001', 'legacy_ref': 'OLD-4471',
- evidence: shadow backfill: backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 2, 'carrier_id': 7, 'vehicle_id': 2, 'parent_shipment_id': 1, 'reference': 'SHP-10002', 'legacy_ref': None, 'status'
- evidence: shadow backfill: backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 3, 'carrier_id': 8, 'vehicle_id': 3, 'parent_shipment_id': None, 'reference': 'SHP-10003', 'legacy_ref': 'OLD-4480',
- evidence: shadow backfill: backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 4, 'carrier_id': 9, 'vehicle_id': None, 'parent_shipment_id': None, 'reference': 'SHP-10004', 'legacy_ref': None, 's
- evidence: statement 0: `ALTER TABLE shipments ADD COLUMN service_level TEXT NOT NULL`

## Blast radius

- statements in the corpus that touch the changed objects: 5 (weighted score 17)
- shadow replay: 17/17 statements passed before, 16/17 after
- reproduced failures: 1 · silent column changes: 0 · data-migration failures: 4

| statement | service | engine error |
|---|---|---|
| `q_dispatch_create` | dispatch-api | IntegrityError: NOT NULL constraint failed: shipments.service_level |

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 1 - expand (safe to run now)

```sql
ALTER TABLE "shipments" ADD COLUMN "service_level" TEXT;
```

### Phase 2 - contract (only after the code steps below)

```sql
-- after backfill: ALTER TABLE "shipments" ALTER COLUMN "service_level" SET NOT NULL;
```

### Rollback for phase 1

```sql
ALTER TABLE "shipments" DROP COLUMN "service_level";
```

### Human decisions required (the tool will not decide these)

- shipments.service_level is NOT NULL with no default: a human must supply a backfill value before phase 2 can add the constraint

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Which deploy lands first: the query change or the schema change?
- What is the accepted risk for NOT_NULL_NO_DEFAULT?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 2 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.

What this audit trusted rather than checked:

- `shipments.service_level` (audit_gate_text_only, generated rollback): this step is treated as gated because a human gate names `shipments.service_level`; this audit read the name, not the question

- shadow replay of the generated rollback script against the post-phase-1 schema: 0 of 17 corpus statement(s) break

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/holdout_01_service_level_not_null.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
