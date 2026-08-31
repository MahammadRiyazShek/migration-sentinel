# Trajectory - holdout_06_audit_trigger

- run id: `eval-holdout_06_audit_trigger`
- case: `holdout_06_audit_trigger`
- events: 29

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_06_audit_trigger",
 "migration_statements": 2,
 "tables_declared": [
  "carriers",
  "vehicles",
  "drivers",
  "shipments",
  "shipment_stops",
  "carrier_invoices",
  "geofence_events"
 ]
}
```

</details>

**tool** `schema.parse` (1.08 ms)

```json
{
 "args": {
  "sql": "CREATE TABLE carriers (\n  id SERIAL PRIMARY KEY,\n  code TEXT NOT NULL,\n  legal_name TEXT NOT NULL,\n  region TEXT NOT NULL DEFAULT 'emea',\n  active INTEGER NOT NULL DEFAULT 1,\n  onboarded_at TIMESTAMPTZ NOT NULL\n);\n\nCREATE TABLE vehicles (\n  id SERIAL PRIMARY KEY,\n  carrier_id INTEGER NOT NULL,\n  plate TEXT NOT NULL,\n  capacity_kg INTEGER NOT NULL DEFAULT 0,\n  refrigerated INTEGER NOT NULL DEFAULT ...",
  "row_estimates": {
   "carriers": 4200,
   "vehicles": 21000,
   "drivers": 48000,
   "shipments": 62000000,
   "shipment_stops": 310000000,
   "carrier_invoices": 9400000,
   "geofence_events": 1200000000
  }
 }
}
```

_tool responded_

```json
"Schema"
```

**tool** `migration.parse` (0.15 ms)

```json
{
 "args": {
  "sql": "CREATE TABLE stop_status_audit (\n  id SERIAL PRIMARY KEY,\n  stop_id INTEGER NOT NULL,\n  old_status TEXT,\n  new_status TEXT,\n  changed_at TIMESTAMPTZ NOT NULL\n);\nCREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status ON shipment_stops\n  FOR EACH ROW EXECUTE FUNCTION log_stop_status_change();\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "create_table",
  "table": "stop_status_audit",
  "column": null,
  "detail": {
   "table": "Table"
  },
  "sql": "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, chan...",
  "index": 0
 },
 {
  "kind": "unsupported",
  "table": null,
  "column": null,
  "detail": {},
  "sql": "CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status ON shipment_stops FOR EACH ROW EXECUTE FUNCTION log_stop_sta...",
  "index": 1
 }
]
```

**tool** `migration.audit` (0.13 ms)

```json
{
 "args": {
  "migration_sql": "CREATE TABLE stop_status_audit (\n  id SERIAL PRIMARY KEY,\n  stop_id INTEGER NOT NULL,\n  old_status TEXT,\n  new_status TEXT,\n  changed_at TIMESTAMPTZ NOT NULL\n);\nCREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status ON shipment_stops\n  FOR EACH ROW EXECUTE FUNCTION log_stop_status_change();\n",
  "ops": [
   {
    "kind": "create_table",
    "table": "stop_status_audit",
    "column": null,
    "detail": {
     "table": "Table"
    },
    "sql": "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, chan...",
    "index": 0
   },
   {
    "kind": "unsupported",
    "table": null,
    "column": null,
    "detail": {},
    "sql": "CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status ON shipment_stops FOR EACH ROW EXECUTE FUNCTION log_stop_sta...",
    "index": 1
   }
  ]
 }
}
```

_tool responded_

```json
{
 "lexed_statements": 2,
 "ops": 2,
 "unterminated": [],
 "unaccounted": [],
 "procedural": [],
 "conservation": {
  "significant_chars": 247,
  "attributed_chars": 247,
  "unattributed_chars": 0
 },
 "clean": true
}
```

**tool** `schema.apply_ops` (0.1 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "create_table",
    "table": "stop_status_audit",
    "column": null,
    "detail": {
     "table": "Table"
    },
    "sql": "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, chan...",
    "index": 0
   },
   {
    "kind": "unsupported",
    "table": null,
    "column": null,
    "detail": {},
    "sql": "CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status ON shipment_stops FOR EACH ROW EXECUTE FUNCTION log_stop_sta...",
    "index": 1
   }
  ]
 }
}
```

_tool responded_

```json
[
 "Schema",
 [
  "op 1 (unsupported) not modelled structurally: CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status "
 ]
]
```

_note (cartographer)_: Some statements could not be modelled structurally; they are passed to the risk officer as unknowns rather than silently assumed safe.

**result**

```json
{
 "op_kinds": [
  "create_table",
  "unsupported"
 ],
 "tables_touched": [
  "stop_status_audit"
 ],
 "unmodelled": [
  "op 1 (unsupported) not modelled structurally: CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status "
 ]
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_06_audit_trigger",
 "corpus_size": 15,
 "services": [
  "bi-etl",
  "customer-portal",
  "dispatch-api",
  "driver-app",
  "finance-ops",
  "ops-console",
  "telemetry-worker"
 ]
}
```

</details>

**tool** `corpus.dependents` (0.11 ms)

```json
{
 "args": {
  "queries": [
   {
    "id": "q_dispatch_create",
    "service": "dispatch-api",
    "criticality": "critical",
    "label": "shipment creation",
    "sql": "INSERT INTO shipments (carrier_id, reference, status, weight_kg, promised_at) VALUES (7,'SHP-77001','planned',1200,'2026..."
   },
   {
    "id": "q_dispatch_board",
    "service": "dispatch-api",
    "criticality": "critical",
    "label": "dispatch board",
    "sql": "SELECT id, reference, status, promised_at FROM shipments WHERE status = 'in_transit'"
   },
   {
    "id": "q_dispatch_stop_progress",
    "service": "dispatch-api",
    "criticality": "high",
    "label": "mark a stop arrived",
    "sql": "UPDATE shipment_stops SET status = 'arrived' WHERE id = 1"
   },
   {
    "id": "q_portal_track",
    "service": "customer-portal",
    "criticality": "critical",
    "label": "public tracking page",
    "sql": "SELECT reference, status, promised_at, delivered_at FROM shipments WHERE reference = 'SHP-10001'"
   },
   {
    "id": "q_ops_active",
    "service": "ops-console",
    "criticality": "high",
    "label": "active shipment list",
    "sql": "SELECT * FROM active_shipments"
   },
   {
    "id": "q_ops_veh
```

_tool responded_

```json
[]
```

**tool** `corpus.blast_score` (0.0 ms)

```json
{
 "args": {
  "hits": []
 }
}
```

_tool responded_

```json
0
```

**tool** `shadow.replay` (3.34 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "create_table",
    "table": "stop_status_audit",
    "column": null,
    "detail": {
     "table": "Table"
    },
    "sql": "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, chan...",
    "index": 0
   },
   {
    "kind": "unsupported",
    "table": null,
    "column": null,
    "detail": {},
    "sql": "CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status ON shipment_stops FOR EACH ROW EXECUTE FUNCTION log_stop_sta...",
    "index": 1
   }
  ],
  "seed": {
   "carriers": [
    {
     "id": 7,
     "code": "NRDX",
     "legal_name": "Nordex Freight BV",
     "region": "emea",
     "active": 1,
     "onboarded_at": "2022-04-11"
    },
    {
     "id": 8,
     "code": "MRLN",
     "legal_name": "Merlin Road Ltd",
     "region": "emea",
     "active": 1,
     "onboarded_at": "2023-08-02"
    },
    {
     "id": 9,
     "code": "ATLS",
     "legal_name": "Atlas Logistica SA",
     "region": "latam",
     "active": 0,
     "onboarded_at": "2021-01-19"
    }
   ],
   "vehicles": [
    {
     "id": 1,
     "carrier_id": 7
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [],
 "broken": [],
 "column_drift": [],
 "rowcount_drift": [],
 "data_loss": [],
 "queries_run": 17,
 "queries_ok_before": 17,
 "queries_ok_after": 17
}
```

**result**

```json
{
 "dependent_queries": 0,
 "blast_score": 0,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [],
  "broken": [],
  "column_drift": [],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 17,
  "queries_ok_before": 17,
  "queries_ok_after": 17
 },
 "hazards_found": []
}
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_06_audit_trigger",
 "row_estimates": {
  "carriers": 4200,
  "vehicles": 21000,
  "drivers": 48000,
  "shipments": 62000000,
  "shipment_stops": 310000000,
  "carrier_invoices": 9400000,
  "geofence_events": 1200000000
 },
 "inherited_hazards": []
}
```

</details>

**tool** `coverage.ledger` (0.19 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "create_table",
    "table": "stop_status_audit",
    "column": null,
    "detail": {
     "table": "Table"
    },
    "sql": "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, chan...",
    "index": 0
   },
   {
    "kind": "unsupported",
    "table": null,
    "column": null,
    "detail": {},
    "sql": "CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status ON shipment_stops FOR EACH ROW EXECUTE FUNCTION log_stop_sta...",
    "index": 1
   }
  ],
  "schema": "Schema",
  "queries": [
   {
    "id": "q_dispatch_create",
    "service": "dispatch-api",
    "criticality": "critical",
    "label": "shipment creation",
    "sql": "INSERT INTO shipments (carrier_id, reference, status, weight_kg, promised_at) VALUES (7,'SHP-77001','planned',1200,'2026..."
   },
   {
    "id": "q_dispatch_board",
    "service": "dispatch-api",
    "criticality": "critical",
    "label": "dispatch board",
    "sql": "SELECT id, reference, status, promised_at FROM shipments WHERE status = 'in_transit'"
   },
   {
    "id": "q_dispatch_stop_progress",
    "service": "dispatch-api",
    "criticalit
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "unmodelled_statement",
   "object": "shipment_stops",
   "object_inferred": true,
   "statement_index": 1,
   "statement": "CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status ON shipment_stops FOR EACH ROW EXECUTE FUNCTION log_stop_sta...",
   "why": "the parser produced no structural model for this statement, so no post-migration schema and no replay covers it; the rel...",
   "closes_with": "a reviewer confirms by hand what statement 1 does to shipment_stops and to anything reading it",
   "irreversible": false
  }
 ],
 "gap_kinds": [
  "unmodelled_statement"
 ],
 "irreversible": [],
 "corpus_statements": 15,
 "parser_notes": [
  "op 1 (unsupported) not modelled structurally: CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status "
 ]
}
```

_note (risk_officer)_: verdict capped to NEEDS_COVERAGE_SIGNOFF: 1 coverage gap(s) on objects this migration touches (shipment_stops). No hazard was invented; the packet cannot certify what it did not see.

**result**

```json
{
 "verdict": "NEEDS_COVERAGE_SIGNOFF",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 0,
  "blocker": 0
 },
 "coverage_gaps": [
  "unmodelled_statement:shipment_stops"
 ],
 "verdict_capped_by_coverage": true,
 "hazards": []
}
```

## Agent: rollout_engineer

**Goal** Rewrite the migration as a phase-1 (expand, safe now) / phase-2 (contract, after the code deploy) plan with a rollback, and surface every step that needs a human decision.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_06_audit_trigger",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": []
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=472/1 cost=$0.0

> 

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 1,
 "phase2_statements": 0,
 "human_gates": 2
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_06_audit_trigger",
 "attempt": 1,
 "phase1_statements": 1
}
```

</details>

**tool** `migration.parse` (0.12 ms)

```json
{
 "args": {
  "sql": "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, changed_at TIMESTAMPTZ NOT NULL );"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "create_table",
  "table": "stop_status_audit",
  "column": null,
  "detail": {
   "table": "Table"
  },
  "sql": "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, chan...",
  "index": 0
 }
]
```

**tool** `schema.apply_ops` (0.06 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "create_table",
    "table": "stop_status_audit",
    "column": null,
    "detail": {
     "table": "Table"
    },
    "sql": "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, chan...",
    "index": 0
   }
  ]
 }
}
```

_tool responded_

```json
[
 "Schema",
 []
]
```

**tool** `shadow.replay` (3.23 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "create_table",
    "table": "stop_status_audit",
    "column": null,
    "detail": {
     "table": "Table"
    },
    "sql": "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, chan...",
    "index": 0
   }
  ],
  "seed": {
   "carriers": [
    {
     "id": 7,
     "code": "NRDX",
     "legal_name": "Nordex Freight BV",
     "region": "emea",
     "active": 1,
     "onboarded_at": "2022-04-11"
    },
    {
     "id": 8,
     "code": "MRLN",
     "legal_name": "Merlin Road Ltd",
     "region": "emea",
     "active": 1,
     "onboarded_at": "2023-08-02"
    },
    {
     "id": 9,
     "code": "ATLS",
     "legal_name": "Atlas Logistica SA",
     "region": "latam",
     "active": 0,
     "onboarded_at": "2021-01-19"
    }
   ],
   "vehicles": [
    {
     "id": 1,
     "carrier_id": 7,
     "plate": "NL-14-BXR",
     "capacity_kg": 18000,
     "refrigerated": 1,
     "last_service_on": "2026-01-08"
    },
    {
     "id": 2,
     "carrier_id": 7,
     "plate": "NL-22-QQT",
     "capacity_kg": 7500,
     "refrigerated": 0,
     
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [],
 "broken": [],
 "column_drift": [],
 "rowcount_drift": [],
 "data_loss": [],
 "queries_run": 17,
 "queries_ok_before": 17,
 "queries_ok_after": 17
}
```

**result**

```json
{
 "verified": true,
 "problems": [],
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [],
  "broken": [],
  "column_drift": [],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 17,
  "queries_ok_before": 17,
  "queries_ok_after": 17
 },
 "unmodelled": []
}
```

**tool** `plan.audit` (0.41 ms)

```json
{
 "args": {
  "plan": {
   "attempt": 1,
   "phase1_sql": [
    "CREATE TABLE stop_status_audit ( id SERIAL PRIMARY KEY, stop_id INTEGER NOT NULL, old_status TEXT, new_status TEXT, chan..."
   ],
   "phase2_sql": [],
   "rollback_sql": [],
   "code_steps": [],
   "human_gates": [
    "statement 1 (unsupported) is outside the tool's model and needs manual review: CREATE TRIGGER trg_stop_status_audit AFTE...",
    "coverage gap on `shipment_stops` (unmodelled_statement): a reviewer confirms by hand what statement 1 does to shipment_s..."
   ],
   "questions": [],
   "questions_source": "model",
   "questions_dropped": [],
   "policy": {
    "include_view_changes": true,
    "expand_contract_type_change": true,
    "minimal_phase1": false,
    "notes": []
   }
  },
  "schema": "Schema",
  "queries": [
   {
    "id": "q_dispatch_create",
    "service": "dispatch-api",
    "criticality": "critical",
    "label": "shipment creation",
    "sql": "INSERT INTO shipments (carrier_id, reference, status, weight_kg, promised_at) VALUES (7,'SHP-77001','planned',1200,'2026..."
   },
   {
    "id": "q_dispatch_board",
    "service": "dispatch-api",
    "criticality": "critical",
    "label": "dis
```

_tool responded_

```json
{
 "statements_audited": 1,
 "scripts": {
  "phase1": 1,
  "phase2": 0,
  "rollback": 0
 },
 "findings": [],
 "finding_codes": [],
 "gaps": [],
 "gap_kinds": [],
 "kind_inventory": [
  {
   "script": "phase1",
   "statement_index": 0,
   "kind": "create_table",
   "bucket": "REPLAY_COVERED"
  }
 ],
 "gates_trusted": 0,
 "replay": {
  "ran": true,
  "scripts": {},
  "note": "the generated phase 2 is expected to break today's statements - that is what the code steps are for. The number is publi..."
 },
 "clean": true
}
```

**model** `scripted-v1` tag=`executive_summary` tokens=43/77 cost=$0.0

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - coverage sign-off: **REQUIRED**

The verdict is capped at NEEDS_COVERAGE_SIGNOFF. The hazards found are not blocking, but this review has 1 declared blind spot(s) on objects the migration touches, and a packet must not certify what it did not see. Each gap is a human gate in the plan.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
