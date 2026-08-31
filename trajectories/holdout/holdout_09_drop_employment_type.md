# Trajectory - holdout_09_drop_employment_type

- run id: `eval-holdout_09_drop_employment_type`
- case: `holdout_09_drop_employment_type`
- events: 34

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_09_drop_employment_type",
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

**tool** `schema.parse` (1.04 ms)

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

**tool** `migration.parse` (0.03 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE drivers DROP COLUMN employment_type;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "drop_column",
  "table": "drivers",
  "column": "employment_type",
  "detail": {},
  "sql": "ALTER TABLE drivers DROP COLUMN employment_type",
  "index": 0
 }
]
```

**tool** `schema.apply_ops` (0.07 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "drop_column",
    "table": "drivers",
    "column": "employment_type",
    "detail": {},
    "sql": "ALTER TABLE drivers DROP COLUMN employment_type",
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
  "drop_column"
 ],
 "tables_touched": [
  "drivers"
 ],
 "unmodelled": []
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_09_drop_employment_type",
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
[
 {
  "query_id": "q_driver_profile",
  "service": "driver-app",
  "criticality": "high",
  "matched": [
   "drivers"
  ],
  "uses_select_star": false,
  "label": "driver profile in the app"
 },
 {
  "query_id": "q_etl_driver_roster",
  "service": "bi-etl",
  "criticality": "high",
  "matched": [
   "driver_roster"
  ],
  "uses_select_star": true,
  "label": "warehouse load of the driver roster"
 }
]
```

**tool** `corpus.blast_score` (0.01 ms)

```json
{
 "args": {
  "hits": [
   {
    "query_id": "q_driver_profile",
    "service": "driver-app",
    "criticality": "high",
    "matched": [
     "drivers"
    ],
    "uses_select_star": false,
    "label": "driver profile in the app"
   },
   {
    "query_id": "q_etl_driver_roster",
    "service": "bi-etl",
    "criticality": "high",
    "matched": [
     "driver_roster"
    ],
    "uses_select_star": true,
    "label": "warehouse load of the driver roster"
   }
  ]
 }
}
```

_tool responded_

```json
6
```

**tool** `shadow.replay` (3.79 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "drop_column",
    "table": "drivers",
    "column": "employment_type",
    "detail": {},
    "sql": "ALTER TABLE drivers DROP COLUMN employment_type",
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
     "id": 3,
     "carrier_id": 8,
     "plate": "DE-91
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [],
 "broken": [],
 "column_drift": [
  {
   "query_id": "q_etl_driver_roster",
   "service": "bi-etl",
   "criticality": "high",
   "before": [
    "id",
    "carrier_id",
    "full_name",
    "phone",
    "licence_class",
    "employment_type",
    "hired_on"
   ],
   "after": [
    "id",
    "carrier_id",
    "full_name",
    "phone",
    "licence_class",
    "hired_on"
   ],
   "removed": [
    "employment_type"
   ],
   "added": [],
   "sql": "SELECT * FROM driver_roster"
  },
  {
   "query_id": "__view__driver_roster",
   "service": "database",
   "criticality": "high",
   "before": [
    "id",
    "carrier_id",
    "full_name",
    "phone",
    "licence_class",
    "employment_type",
    "hired_on"
   ],
   "after": [
    "id",
    "carrier_id",
    "full_name",
    "phone",
    "licence_class",
    "hired_on"
   ],
   "removed": [
    "employment_type"
   ],
   "added": [],
   "sql": "SELECT * FROM \"driver_roster\" LIMIT 1"
  }
 ],
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
 "dependent_queries": 2,
 "blast_score": 6,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [],
  "broken": [],
  "column_drift": [
   {
    "query_id": "q_etl_driver_roster",
    "service": "bi-etl",
    "criticality": "high",
    "before": [
     "id",
     "carrier_id",
     "full_name",
     "phone",
     "licence_class",
     "employment_type",
     "hired_on"
    ],
    "after": [
     "id",
     "carrier_id",
     "full_name",
     "phone",
     "licence_class",
     "hired_on"
    ],
    "removed": [
     "employment_type"
    ],
    "added": [],
    "sql": "SELECT * FROM driver_roster"
   },
   {
    "query_id": "__view__driver_roster",
    "service": "database",
    "criticality": "high",
    "before": [
     "id",
     "carrier_id",
     "full_name",
     "phone",
     "licence_class",
     "employment_type",
     "hired_on"
    ],
    "after": [
     "id",
     "carrier_id",
     "full_name",
     "phone",
     "licence_class",
     "hired_on"
    ],
    "removed": [
     "employment_type"
    ],
    "added": [],
    "sql": "SELECT * FROM \"driver_roster\" LIMIT 1"
   }
  ],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 17,
  "queries_ok_before": 17,
  "queries_ok_after": 17
 },
 "hazards_found": [
  "SELECT_STAR_DRIFT"
 ]
}
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_09_drop_employment_type",
 "row_estimates": {
  "carriers": 4200,
  "vehicles": 21000,
  "drivers": 48000,
  "shipments": 62000000,
  "shipment_stops": 310000000,
  "carrier_invoices": 9400000,
  "geofence_events": 1200000000
 },
 "inherited_hazards": [
  "SELECT_STAR_DRIFT"
 ]
}
```

</details>

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "CROSS_SERVICE_UNCOORDINATED",
  "table": null
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

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "DESTRUCTIVE_NO_EXPAND_CONTRACT",
  "table": "drivers"
 }
}
```

_tool responded_

```json
[
 0,
 [
  "INC-2023-09"
 ]
]
```

**tool** `memory.escalation` (0.0 ms)

```json
{
 "args": {
  "hazard_code": "SELECT_STAR_DRIFT",
  "table": "q_etl_driver_roster"
 }
}
```

_tool responded_

```json
[
 0,
 [
  "INC-2025-02"
 ]
]
```

**tool** `memory.escalation` (0.0 ms)

```json
{
 "args": {
  "hazard_code": "MISSING_ROLLBACK",
  "table": null
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

**tool** `coverage.ledger` (0.17 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "drop_column",
    "table": "drivers",
    "column": "employment_type",
    "detail": {},
    "sql": "ALTER TABLE drivers DROP COLUMN employment_type",
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
    "sql": "SELECT reference, status, promised_at, delivered_at FROM shipments WHERE refe
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "uncovered_object",
   "object": "drivers.employment_type",
   "object_inferred": false,
   "statement_index": 0,
   "statement": "ALTER TABLE drivers DROP COLUMN employment_type",
   "why": "no statement in the 15-statement corpus references employment_type, so replay had nothing to run against it; that is sil...",
   "closes_with": "a reviewer greps the real consumers for employment_type before phase 2",
   "irreversible": false
  }
 ],
 "gap_kinds": [
  "uncovered_object"
 ],
 "irreversible": [],
 "corpus_statements": 15,
 "parser_notes": []
}
```

_note (risk_officer)_: verdict capped to NEEDS_COVERAGE_SIGNOFF: 1 coverage gap(s) on objects this migration touches (drivers.employment_type). No hazard was invented; the packet cannot certify what it did not see.

**model** `scripted-v1` tag=`hazard_narrative` tokens=427/58 cost=$0.0

> Impact lands on a service owned by another team. The fix needs a deploy the migration author does not control, so ordering must be agreed first. Evidence: corpus ownership of failing statements: ['bi-etl'] Owning service(s): bi-etl.

**model** `scripted-v1` tag=`hazard_narrative` tokens=436/59 cost=$0.0

> Destructive change shipped in a single step. Dropping or renaming in one deploy means old and new application code cannot both work. Evidence: statement 0: `ALTER TABLE drivers DROP COLUMN employment_type` Previously bit us in INC-2023-09.

**model** `scripted-v1` tag=`hazard_narrative` tokens=478/103 cost=$0.0

> SELECT * consumer receives a different column set. The query still runs, so tests pass, but downstream code indexing by position or key breaks. Evidence: shadow replay columns before=['id', 'carrier_id', 'full_name', 'phone', 'licence_class', 'employment_type', 'hired_on'] after=['id', 'carrier_id', 'full_name', 'phone', 'licence_class', 'hired_on'] Owning service(s): bi-etl. Previously bit us in INC-2025-02.

**model** `scripted-v1` tag=`hazard_narrative` tokens=406/30 cost=$0.0

> No rollback path supplied. Recovery at 3am should not require improvising DDL. Evidence: case field `rollback_sql` is empty

**result**

```json
{
 "verdict": "NEEDS_COVERAGE_SIGNOFF",
 "counts": {
  "low": 0,
  "medium": 1,
  "high": 3,
  "blocker": 0
 },
 "coverage_gaps": [
  "uncovered_object:drivers.employment_type"
 ],
 "verdict_capped_by_coverage": true,
 "hazards": [
  {
   "code": "CROSS_SERVICE_UNCOORDINATED",
   "severity": "high",
   "source": "static",
   "memory": []
  },
  {
   "code": "DESTRUCTIVE_NO_EXPAND_CONTRACT",
   "severity": "high",
   "source": "static",
   "memory": [
    "INC-2023-09"
   ]
  },
  {
   "code": "SELECT_STAR_DRIFT",
   "severity": "high",
   "source": "replay",
   "memory": [
    "INC-2025-02"
   ]
  },
  {
   "code": "MISSING_ROLLBACK",
   "severity": "medium",
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
 "case": "holdout_09_drop_employment_type",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "CROSS_SERVICE_UNCOORDINATED",
  "DESTRUCTIVE_NO_EXPAND_CONTRACT",
  "MISSING_ROLLBACK",
  "SELECT_STAR_DRIFT"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=498/59 cost=$0.0

> - Has the owning team agreed to the deploy order?
> - What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
> - What is the accepted risk for MISSING_ROLLBACK?
> - Do any consumers read this result set positionally or serialise it whole?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 0,
 "phase2_statements": 1,
 "human_gates": 3
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_09_drop_employment_type",
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

**tool** `schema.apply_ops` (0.07 ms)

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

**tool** `shadow.replay` (3.36 ms)

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

**model** `scripted-v1` tag=`executive_summary` tokens=43/77 cost=$0.0

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 3 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - coverage sign-off: **REQUIRED**

The verdict is capped at NEEDS_COVERAGE_SIGNOFF. The hazards found are not blocking, but this review has 1 declared blind spot(s) on objects the migration touches, and a packet must not certify what it did not see. Each gap is a human gate in the plan.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
