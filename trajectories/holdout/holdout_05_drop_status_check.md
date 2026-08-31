# Trajectory - holdout_05_drop_status_check

- run id: `eval-holdout_05_drop_status_check`
- case: `holdout_05_drop_status_check`
- events: 26

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_05_drop_status_check",
 "migration_statements": 1,
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

**tool** `schema.parse` (0.94 ms)

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

**tool** `migration.parse` (0.04 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE shipments DROP CONSTRAINT shipments_status_chk;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "drop_constraint",
  "table": "shipments",
  "column": null,
  "detail": {
   "constraint": "shipments_status_chk"
  },
  "sql": "ALTER TABLE shipments DROP CONSTRAINT shipments_status_chk",
  "index": 0
 }
]
```

**tool** `schema.apply_ops` (0.09 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "drop_constraint",
    "table": "shipments",
    "column": null,
    "detail": {
     "constraint": "shipments_status_chk"
    },
    "sql": "ALTER TABLE shipments DROP CONSTRAINT shipments_status_chk",
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

**result**

```json
{
 "op_kinds": [
  "drop_constraint"
 ],
 "tables_touched": [
  "shipments"
 ],
 "unmodelled": []
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_05_drop_status_check",
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

**tool** `corpus.dependents` (0.12 ms)

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
[
 {
  "query_id": "q_dispatch_create",
  "service": "dispatch-api",
  "criticality": "critical",
  "matched": [
   "shipments"
  ],
  "uses_select_star": false,
  "label": "shipment creation"
 },
 {
  "query_id": "q_dispatch_board",
  "service": "dispatch-api",
  "criticality": "critical",
  "matched": [
   "shipments"
  ],
  "uses_select_star": false,
  "label": "dispatch board"
 },
 {
  "query_id": "q_portal_track",
  "service": "customer-portal",
  "criticality": "critical",
  "matched": [
   "shipments"
  ],
  "uses_select_star": false,
  "label": "public tracking page"
 },
 {
  "query_id": "q_ops_active",
  "service": "ops-console",
  "criticality": "high",
  "matched": [
   "active_shipments"
  ],
  "uses_select_star": true,
  "label": "active shipment list"
 },
 {
  "query_id": "q_etl_volume",
  "service": "bi-etl",
  "criticality": "medium",
  "matched": [
   "shipments"
  ],
  "uses_select_star": false,
  "label": "shipment volume by status"
 }
]
```

**tool** `corpus.blast_score` (0.02 ms)

```json
{
 "args": {
  "hits": [
   {
    "query_id": "q_dispatch_create",
    "service": "dispatch-api",
    "criticality": "critical",
    "matched": [
     "shipments"
    ],
    "uses_select_star": false,
    "label": "shipment creation"
   },
   {
    "query_id": "q_dispatch_board",
    "service": "dispatch-api",
    "criticality": "critical",
    "matched": [
     "shipments"
    ],
    "uses_select_star": false,
    "label": "dispatch board"
   },
   {
    "query_id": "q_portal_track",
    "service": "customer-portal",
    "criticality": "critical",
    "matched": [
     "shipments"
    ],
    "uses_select_star": false,
    "label": "public tracking page"
   },
   {
    "query_id": "q_ops_active",
    "service": "ops-console",
    "criticality": "high",
    "matched": [
     "active_shipments"
    ],
    "uses_select_star": true,
    "label": "active shipment list"
   },
   {
    "query_id": "q_etl_volume",
    "service": "bi-etl",
    "criticality": "medium",
    "matched": [
     "shipments"
    ],
    "uses_select_star": false,
    "label": "shipment volume by status"
   }
  ]
 }
}
```

_tool responded_

```json
17
```

**tool** `shadow.replay` (3.26 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "drop_constraint",
    "table": "shipments",
    "column": null,
    "detail": {
     "constraint": "shipments_status_chk"
    },
    "sql": "ALTER TABLE shipments DROP CONSTRAINT shipments_status_chk",
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
     "last_service_on": "2025-11-30"
    },
    {
     
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
 "dependent_queries": 5,
 "blast_score": 17,
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
 "case": "holdout_05_drop_status_check",
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

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "INTEGRITY_CONSTRAINT_REMOVED",
  "table": "shipments"
 }
}
```

_tool responded_

```json
[
 0,
 []
]
```

**tool** `coverage.ledger` (0.16 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "drop_constraint",
    "table": "shipments",
    "column": null,
    "detail": {
     "constraint": "shipments_status_chk"
    },
    "sql": "ALTER TABLE shipments DROP CONSTRAINT shipments_status_chk",
    "index": 0
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
    "criticality": "high",
    "label": "mark a stop arrived",
    "sql": "UPDATE shipment_stops SET status = 'arrived' WHERE id = 1"
   },
   {
    "id": "q_portal_track",
    "service": "customer-portal",
    "criticality": "critical",
    "label": "public tracking page",
    "sql": "SELECT reference, status, 
```

_tool responded_

```json
{
 "gaps": [],
 "gap_kinds": [],
 "irreversible": [],
 "corpus_statements": 15,
 "parser_notes": []
}
```

**model** `scripted-v1` tag=`hazard_narrative` tokens=462/52 cost=$0.0

> Data-integrity constraint removed. Nothing breaks today; invalid rows start accumulating and are expensive to clean up later. Evidence: statement 0: `ALTER TABLE shipments DROP CONSTRAINT shipments_status_chk`

**result**

```json
{
 "verdict": "SAFE_WITH_PLAN",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 1,
  "blocker": 0
 },
 "coverage_gaps": [],
 "verdict_capped_by_coverage": false,
 "hazards": [
  {
   "code": "INTEGRITY_CONSTRAINT_REMOVED",
   "severity": "high",
   "source": "static",
   "memory": []
  }
 ]
}
```

## Agent: rollout_engineer

**Goal** Rewrite the migration as a phase-1 (expand, safe now) / phase-2 (contract, after the code deploy) plan with a rollback, and surface every step that needs a human decision.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_05_drop_status_check",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "INTEGRITY_CONSTRAINT_REMOVED"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=480/14 cost=$0.0

> - What enforces this invariant once the constraint is gone?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 0,
 "phase2_statements": 1,
 "human_gates": 1
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_05_drop_status_check",
 "attempt": 1,
 "phase1_statements": 0
}
```

</details>

**tool** `migration.parse` (0.01 ms)

```json
{
 "args": {
  "sql": ""
 }
}
```

_tool responded_

```json
[]
```

**tool** `schema.apply_ops` (0.06 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": []
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

**tool** `shadow.replay` (3.46 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [],
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
     "last_service_on": "2025-11-30"
    },
    {
     "id": 3,
     "carrier_id": 8,
     "plate": "DE-91-KLM",
     "capacity_kg": 24000,
     "refrigerated": 0,
     "last_service_on": null
    }
   ],
   "drivers": [
    {
     "id": 1,
     "carrier_id": 7,
     "full_name": "Ines Duarte",
  
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

**model** `scripted-v1` tag=`executive_summary` tokens=41/39 cost=$0.0

> Shippable, but only as the staged plan below. 0 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
