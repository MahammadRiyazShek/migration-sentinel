# Migration review: Rename shipment_stops to stops behind a compatibility view

**BLOCK - do not merge**

Do not ship this as written. 2 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 2 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-holdout_03_rename_table_behind_view` · case `holdout_03_rename_table_behind_view` · owning service `dispatch-api` · 13.7 ms · model scripted-v1 (7 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_dispatch_stop_progress` | replay |
| 2 | **BLOCKER** | Live query breaks after migration | `q_driver_stop_arrive` | replay |
| 3 | **HIGH** | Impact lands on a service owned by another team | `-` | static |
| 4 | **HIGH** | Destructive change shipped in a single step | `shipment_stops` | static |
| 5 | **MEDIUM** | No rollback path supplied | `-` | static |

### 1. [BLOCKER] Live query breaks after migration

q_dispatch_stop_progress fails after the migration: OperationalError: cannot modify shipment_stops because it is a view

- evidence: shadow replay: `UPDATE shipment_stops SET status = 'arrived' WHERE id = 1` -> OperationalError: cannot modify shipment_stops because it is a view
- services affected: dispatch-api

### 2. [BLOCKER] Live query breaks after migration

q_driver_stop_arrive fails after the migration: OperationalError: cannot modify shipment_stops because it is a view

- evidence: shadow replay: `INSERT INTO shipment_stops (shipment_id, sequence_no, kind, status, arrived_at) VALUES (1,4,'delivery','arrived','2026-0` -> OperationalError: cannot modify shipment_stops because it is a view
- services affected: driver-app

### 3. [HIGH] Impact lands on a service owned by another team

the migration is owned by `dispatch-api` but breakage lands in driver-app

- evidence: corpus ownership of failing statements: ['driver-app']
- services affected: driver-app

### 4. [HIGH] Destructive change shipped in a single step

rename table on shipment_stops lands in a single deploy

- evidence: statement 0: `ALTER TABLE shipment_stops RENAME TO stops`
- prior incidents: INC-2023-09

### 5. [MEDIUM] No rollback path supplied

the change ships without a rollback script

- evidence: case field `rollback_sql` is empty

## Blast radius

- statements in the corpus that touch the changed objects: 3 (weighted score 11)
- shadow replay: 17/18 statements passed before, 16/18 after
- reproduced failures: 2 · silent column changes: 0 · data-migration failures: 0

| statement | service | engine error |
|---|---|---|
| `q_dispatch_stop_progress` | dispatch-api | OperationalError: cannot modify shipment_stops because it is a view |
| `q_driver_stop_arrive` | driver-app | OperationalError: cannot modify shipment_stops because it is a view |

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 1 - expand (safe to run now)

```sql
CREATE VIEW shipment_stops AS SELECT id, shipment_id, sequence_no, kind, status, address_json, arrived_at FROM stops;
```

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE shipment_stops RENAME TO stops;
```

### Application changes required between the phases

1. switch all readers from shipment_stops to stops

### Human decisions required (the tool will not decide these)

- renaming shipment_stops is not backwards compatible; confirm the cutover window
- no rollback could be generated automatically; write one before shipping

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Which deploy lands first: the query change or the schema change?
- Has the owning team agreed to the deploy order?
- What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
- What is the accepted risk for MISSING_ROLLBACK?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 2 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.

What this audit trusted rather than checked:

- `shipment_stops` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `shipment_stops`; this audit read the name, not the question

- shadow replay of the generated phase2 script against the post-phase-1 schema: 2 of 18 corpus statement(s) break (q_dispatch_stop_progress, q_driver_stop_arrive) - expected for a contract step, which is what the code steps above are for; the number is printed so it can be checked rather than assumed

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/holdout_03_rename_table_behind_view.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 2 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 2 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
