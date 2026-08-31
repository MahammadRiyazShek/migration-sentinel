# Migration review: Release train: six fleet changes in one migration

**BLOCK - do not merge**

Do not ship this as written. 3 coverage gap(s) need a named sign-off before this can be called safe. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 7 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. 2 defect(s) in the SQL this packet generated: see the plan self-audit before running any of it. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-holdout_08_release_train_fleet` · case `holdout_08_release_train_fleet` · owning service `dispatch-api` · 19.8 ms · model scripted-v1 (12 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_driver_profile` | replay |
| 2 | **BLOCKER** | Index built without CONCURRENTLY on a large table | `geofence_events` | static |
| 3 | **HIGH** | Constraint added without NOT VALID / VALIDATE split | `carrier_invoices` | static |
| 4 | **HIGH** | Impact lands on a service owned by another team | `-` | static |
| 5 | **HIGH** | Destructive change shipped in a single step | `drivers.phone` | static |
| 6 | **HIGH** | Destructive change shipped in a single step | `shipments.legacy_ref` | static |
| 7 | **HIGH** | SELECT * consumer receives a different column set | `q_etl_driver_roster` | replay |
| 8 | **HIGH** | Type change forces a full table rewrite | `shipments` | static |
| 9 | **HIGH** | Backfill runs as one unbounded statement | `shipment_stops` | static |
| 10 | **MEDIUM** | No rollback path supplied | `-` | static |

### 1. [BLOCKER] Live query breaks after migration

q_driver_profile fails after the migration: OperationalError: no such column: phone

- evidence: shadow replay: `SELECT id, full_name, phone, licence_class FROM drivers WHERE id = 1` -> OperationalError: no such column: phone
- services affected: driver-app

### 2. [BLOCKER] Index built without CONCURRENTLY on a large table

index idx_geofence_events_shipment is built without CONCURRENTLY on geofence_events (1,200,000,000 rows, very large)

- evidence: statement 1: `CREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id)`
- evidence: declared row estimate for geofence_events: 1,200,000,000
- prior incidents: INC-2024-07

### 3. [HIGH] Constraint added without NOT VALID / VALIDATE split

carrier_invoices_shipment_fk is added without NOT VALID, so validation scans all 9,400,000 rows under a lock

- evidence: statement 4: `ALTER TABLE carrier_invoices ADD CONSTRAINT carrier_invoices_shipment_fk FOREIGN KEY (shipment_id) REFERENCES `
- prior incidents: INC-2024-11

### 4. [HIGH] Impact lands on a service owned by another team

the migration is owned by `dispatch-api` but breakage lands in bi-etl, driver-app

- evidence: corpus ownership of failing statements: ['bi-etl', 'driver-app']
- services affected: bi-etl, driver-app

### 5. [HIGH] Destructive change shipped in a single step

rename column on drivers.phone lands in a single deploy

- evidence: statement 0: `ALTER TABLE drivers RENAME COLUMN phone TO phone_e164`
- prior incidents: INC-2023-09

### 6. [HIGH] Destructive change shipped in a single step

drop column on shipments.legacy_ref lands in a single deploy

- evidence: statement 2: `ALTER TABLE shipments DROP COLUMN legacy_ref`
- prior incidents: INC-2023-09

### 7. [HIGH] SELECT * consumer receives a different column set

q_etl_driver_roster still runs but its column set changes (removed ['phone'], added ['phone_e164'])

- evidence: shadow replay columns before=['id', 'carrier_id', 'full_name', 'phone', 'licence_class', 'employment_type', 'hired_on'] after=['id', 'carrier_id', 'full_name', 'licence_class', 'employment_type', 'hired_on', 'phone_e164']
- prior incidents: INC-2025-02
- services affected: bi-etl

### 8. [HIGH] Type change forces a full table rewrite

VACUUM FULL rewrites shipments under an ACCESS EXCLUSIVE lock (62,000,000 rows, very large)

- evidence: statement 5: `VACUUM FULL shipments`
- evidence: declared row estimate for shipments: 62,000,000
- evidence: recognised as a whole-relation maintenance command; the statement itself is still not modelled structurally and stays in the coverage ledger

### 9. [HIGH] Backfill runs as one unbounded statement

backfill on shipment_stops runs as one statement over 310,000,000 rows

- evidence: statement 3: `UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed'`

### 10. [MEDIUM] No rollback path supplied

the change ships without a rollback script

- evidence: case field `rollback_sql` is empty

## Blast radius

- statements in the corpus that touch the changed objects: 13 (weighted score 42)
- shadow replay: 17/17 statements passed before, 16/17 after
- reproduced failures: 1 · silent column changes: 2 · data-migration failures: 0

| statement | service | engine error |
|---|---|---|
| `q_driver_profile` | driver-app | OperationalError: no such column: phone |

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 1 - expand (safe to run now)

```sql
ALTER TABLE "drivers" ADD COLUMN "phone_e164" TEXT;
UPDATE "drivers" SET "phone_e164" = "phone" WHERE "phone_e164" IS NULL AND "id" IN (SELECT "id" FROM "drivers" WHERE "phone_e164" IS NULL LIMIT 5000);
CREATE INDEX CONCURRENTLY "idx_geofence_events_shipment" ON "geofence_events" ("shipment_id");
-- repeat until zero rows are affected (batch size 5000):
UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed' AND "id" IN (SELECT "id" FROM "shipment_stops" WHERE status = 'missed' LIMIT 5000);
ALTER TABLE "carrier_invoices" ADD CONSTRAINT "carrier_invoices_shipment_fk" FOREIGN KEY (shipment_id) REFERENCES shipments (id) NOT VALID;
```

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE "drivers" DROP COLUMN "phone";
ALTER TABLE "shipments" DROP COLUMN "legacy_ref";
ALTER TABLE "carrier_invoices" VALIDATE CONSTRAINT "carrier_invoices_shipment_fk";
```

### Rollback for phase 1

```sql
ALTER TABLE "drivers" DROP COLUMN "phone_e164";
DROP INDEX CONCURRENTLY "idx_geofence_events_shipment";
ALTER TABLE "carrier_invoices" DROP CONSTRAINT "carrier_invoices_shipment_fk";
```

### Application changes required between the phases

1. deploy code that writes both drivers.phone and drivers.phone_e164, and reads drivers.phone_e164
2. remove every read and write of shipments.legacy_ref, then wait one full deploy cycle

### Human decisions required (the tool will not decide these)

- confirm no consumer still reads drivers.phone before phase 2 drops it
- confirm shipments.legacy_ref has had zero reads for the agreed observation window before phase 2
- statement 5 (maintenance_rewrite) is outside the tool's model and needs manual review: VACUUM FULL shipments
- coverage gap on `shipments.legacy_ref` (uncovered_object): a reviewer greps the real consumers for legacy_ref before phase 2
- coverage gap on `shipment_stops.status` (in_place_data_mutation): a reviewer confirms which consumers of shipment_stops.status depend on the current values
- coverage gap on `shipments` (unmodelled_statement): a reviewer confirms by hand what statement 5 does to shipments and to anything reading it
- PLAN DEFECT (CONTRACT_STEP_UNGATED) in the generated phase2 script: the plan carries a gate naming this object, or the statement moves out of the generated script
- PLAN DEFECT (ROLLBACK_WINDOW_UNSTATED) in the generated rollback script: the plan states the window - roll back phase 1 only before the code step, and after it use a forward fix instead

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Which deploy lands first: the query change or the schema change?
- What is the accepted risk for CONSTRAINT_VALIDATION_LOCK?
- Has the owning team agreed to the deploy order?
- What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
- What is the acceptable write-stall window for this table?
- What is the accepted risk for MISSING_ROLLBACK?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 11 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

| # | defect | script | statement |
|---|---|---|---|
| 1 | **CONTRACT_STEP_UNGATED** | phase2 | `ALTER TABLE "carrier_invoices" VALIDATE CONSTRAINT "carrier_invoices_shipment_fk"` |
| 2 | **ROLLBACK_WINDOW_UNSTATED** | rollback | `ALTER TABLE "drivers" DROP COLUMN "phone_e164"` |

### 1. A contract step this pipeline generated has no human gate

a `validate_constraint` this pipeline wrote into phase 2 is not named by any human gate, so the packet asks someone to run a destructive statement it never asked anyone to decide about.

- evidence: generated phase 2 statement 2: ALTER TABLE "carrier_invoices" VALIDATE CONSTRAINT "carrier_invoices_shipment_fk"
- evidence: human gates in this packet: 6, none naming carrier_invoices
- evidence: rule inventory: `validate_constraint` is RESIDUAL on the input side - the second half of a NOT VALID split takes its own lock over the whole relation and no rule prices it against the row estimate
- closes when: the plan carries a gate naming this object, or the statement moves out of the generated script

### 2. The rollback is only valid before a code step this same packet asks for

the rollback removes `drivers.phone_e164`, and a code step in this same packet asks the team to start using it; run them in the printed order and the rollback breaks the deploy the packet asked for. The corpus cannot show this: the statements that break are the ones this packet is asking someone to write.

- evidence: generated rollback statement 0: ALTER TABLE "drivers" DROP COLUMN "phone_e164"
- evidence: generated code step: deploy code that writes both drivers.phone and drivers.phone_e164, and reads drivers.phone_e164
- evidence: shadow replay of this rollback breaks 0 corpus statements, which is why replay alone reports it as safe
- closes when: the plan states the window - roll back phase 1 only before the code step, and after it use a forward fix instead

What this audit trusted rather than checked:

- `drivers.phone` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `drivers.phone`; this audit read the name, not the question
- `shipments.legacy_ref` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `shipments.legacy_ref`; this audit read the name, not the question
- `carrier_invoices` (unruled_generated_statement, generated phase2): this pipeline generated a statement of a kind nothing in this pipeline inspects: the second half of a NOT VALID split takes its own lock over the whole relation and no rule prices it against the row estimate
- `drivers` (audit_gate_text_only, generated rollback): this step is treated as gated because a human gate names `drivers`; this audit read the name, not the question

- shadow replay of the generated phase2 script against the post-phase-1 schema: 1 of 17 corpus statement(s) break (q_driver_profile) - expected for a contract step, which is what the code steps above are for; the number is printed so it can be checked rather than assumed
- shadow replay of the generated rollback script against the post-phase-1 schema: 0 of 17 corpus statement(s) break

## Coverage ledger

3 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `shipments.legacy_ref` | no statement in the corpus references this object | no statement in the 15-statement corpus references legacy_ref, so replay had nothing to run against it; that is silence, not a clean bill of health | a reviewer greps the real consumers for legacy_ref before phase 2 |
| `shipment_stops.status` | existing rows rewritten; replay cannot see changed answers | rows that already exist in shipment_stops are rewritten; replay proves the corpus still executes, never that it still returns the same answer | a reviewer confirms which consumers of shipment_stops.status depend on the current values |
| `shipments` | statement not modelled by the parser | the parser produced no structural model for this statement, so no post-migration schema and no replay covers it | a reviewer confirms by hand what statement 5 does to shipments and to anything reading it |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.
- unmodelled statement: op 5 (maintenance_rewrite) not modelled structurally: VACUUM FULL shipments

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/holdout_08_release_train_fleet.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 3 coverage gap(s) need a named sign-off before this can be called safe. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 7 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
