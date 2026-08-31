# Trajectory - holdout_04_safe_additive_language

- run id: `eval-holdout_04_safe_additive_language`
- case: `holdout_04_safe_additive_language`
- events: 27

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_04_safe_additive_language",
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

**tool** `schema.parse` (1.07 ms)

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

**tool** `migration.parse` (0.07 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE drivers ADD COLUMN preferred_language TEXT;\nCREATE INDEX CONCURRENTLY idx_drivers_carrier ON drivers (carrier_id);\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "drivers",
  "column": "preferred_language",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE drivers ADD COLUMN preferred_language TEXT",
  "index": 0
 },
 {
  "kind": "create_index",
  "table": "drivers",
  "column": null,
  "detail": {
   "name": "idx_drivers_carrier",
   "unique": false,
   "concurrently": true,
   "columns": [
    "carrier_id"
   ]
  },
  "sql": "CREATE INDEX CONCURRENTLY idx_drivers_carrier ON drivers (carrier_id)",
  "index": 1
 }
]
```

**tool** `migration.audit` (0.07 ms)

```json
{
 "args": {
  "migration_sql": "ALTER TABLE drivers ADD COLUMN preferred_language TEXT;\nCREATE INDEX CONCURRENTLY idx_drivers_carrier ON drivers (carrier_id);\n",
  "ops": [
   {
    "kind": "add_column",
    "table": "drivers",
    "column": "preferred_language",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE drivers ADD COLUMN preferred_language TEXT",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "drivers",
    "column": null,
    "detail": {
     "name": "idx_drivers_carrier",
     "unique": false,
     "concurrently": true,
     "columns": [
      "carrier_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY idx_drivers_carrier ON drivers (carrier_id)",
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
  "significant_chars": 111,
  "attributed_chars": 111,
  "unattributed_chars": 0
 },
 "clean": true
}
```

**tool** `schema.apply_ops` (0.15 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "drivers",
    "column": "preferred_language",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE drivers ADD COLUMN preferred_language TEXT",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "drivers",
    "column": null,
    "detail": {
     "name": "idx_drivers_carrier",
     "unique": false,
     "concurrently": true,
     "columns": [
      "carrier_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY idx_drivers_carrier ON drivers (carrier_id)",
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
 []
]
```

**result**

```json
{
 "op_kinds": [
  "add_column",
  "create_index"
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
 "case": "holdout_04_safe_additive_language",
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
   "carrier_id"
  ],
  "uses_select_star": false,
  "label": "shipment creation"
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
  "query_id": "q_ops_vehicles",
  "service": "ops-console",
  "criticality": "medium",
  "matched": [
   "carrier_id"
  ],
  "uses_select_star": false,
  "label": "fleet panel"
 },
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
 },
 {
  "query_id": "q_finance_totals",
  "service": "finance-ops",
  "criticality": "high",
  "matched": [
   "carrier_id"
  ],
  "uses_select_star": false,
  "label": "carrier spend rollup"
 },
 {
  "query_id": "q_finance_lookup",
  "service": "finance-ops",
  "criticality": "medium",
  "matched": [
   "carrier_id"
  ],
  "uses_select_star": false,
  "label": "invoice lookup"
 }
]
```

**tool** `corpus.blast_score` (0.03 ms)

```json
{
 "args": {
  "hits": [
   {
    "query_id": "q_dispatch_create",
    "service": "dispatch-api",
    "criticality": "critical",
    "matched": [
     "carrier_id"
    ],
    "uses_select_star": false,
    "label": "shipment creation"
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
    "query_id": "q_ops_vehicles",
    "service": "ops-console",
    "criticality": "medium",
    "matched": [
     "carrier_id"
    ],
    "uses_select_star": false,
    "label": "fleet panel"
   },
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
   },
   {
    "query_id": "q_finance_totals",
    "service": "finance-ops",
    "criticality": "high",
 
```

_tool responded_

```json
20
```

**tool** `shadow.replay` (3.29 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "drivers",
    "column": "preferred_language",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE drivers ADD COLUMN preferred_language TEXT",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "drivers",
    "column": null,
    "detail": {
     "name": "idx_drivers_carrier",
     "unique": false,
     "concurrently": true,
     "columns": [
      "carrier_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY idx_drivers_carrier ON drivers (carrier_id)",
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
     "onboarded_
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
    "employment_type",
    "hired_on",
    "preferred_language"
   ],
   "removed": [],
   "added": [
    "preferred_language"
   ],
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
    "employment_type",
    "hired_on",
    "preferred_language"
   ],
   "removed": [],
   "added": [
    "preferred_language"
   ],
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

_note (blast_radius)_: q_etl_driver_roster gains column(s) ['preferred_language']; recorded as a note, not a hazard, because nothing is removed from the result set

**result**

```json
{
 "dependent_queries": 7,
 "blast_score": 20,
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
     "employment_type",
     "hired_on",
     "preferred_language"
    ],
    "removed": [],
    "added": [
     "preferred_language"
    ],
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
     "employment_type",
     "hired_on",
     "preferred_language"
    ],
    "removed": [],
    "added": [
     "preferred_language"
    ],
    "sql": "SELECT * FROM \"driver_roster\" LIMIT 1"
   }
  ],
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
 "case": "holdout_04_safe_additive_language",
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

**tool** `coverage.ledger` (0.17 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "add_column",
    "table": "drivers",
    "column": "preferred_language",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE drivers ADD COLUMN preferred_language TEXT",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "drivers",
    "column": null,
    "detail": {
     "name": "idx_drivers_carrier",
     "unique": false,
     "concurrently": true,
     "columns": [
      "carrier_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY idx_drivers_carrier ON drivers (carrier_id)",
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

**result**

```json
{
 "verdict": "SAFE",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 0,
  "blocker": 0
 },
 "coverage_gaps": [],
 "verdict_capped_by_coverage": false,
 "hazards": []
}
```

## Agent: rollout_engineer

**Goal** Rewrite the migration as a phase-1 (expand, safe now) / phase-2 (contract, after the code deploy) plan with a rollback, and surface every step that needs a human decision.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_04_safe_additive_language",
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
 "phase1_statements": 2,
 "phase2_statements": 0,
 "human_gates": 0
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_04_safe_additive_language",
 "attempt": 1,
 "phase1_statements": 2
}
```

</details>

**tool** `migration.parse` (0.08 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"drivers\" ADD COLUMN \"preferred_language\" TEXT;\nCREATE INDEX CONCURRENTLY \"idx_drivers_carrier\" ON \"drivers\" (\"carrier_id\");"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "drivers",
  "column": "preferred_language",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE \"drivers\" ADD COLUMN \"preferred_language\" TEXT",
  "index": 0
 },
 {
  "kind": "create_index",
  "table": "drivers",
  "column": null,
  "detail": {
   "name": "idx_drivers_carrier",
   "unique": false,
   "concurrently": true,
   "columns": [
    "carrier_id"
   ]
  },
  "sql": "CREATE INDEX CONCURRENTLY \"idx_drivers_carrier\" ON \"drivers\" (\"carrier_id\")",
  "index": 1
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
    "kind": "add_column",
    "table": "drivers",
    "column": "preferred_language",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"drivers\" ADD COLUMN \"preferred_language\" TEXT",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "drivers",
    "column": null,
    "detail": {
     "name": "idx_drivers_carrier",
     "unique": false,
     "concurrently": true,
     "columns": [
      "carrier_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_drivers_carrier\" ON \"drivers\" (\"carrier_id\")",
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
 []
]
```

**tool** `shadow.replay` (3.3 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "drivers",
    "column": "preferred_language",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"drivers\" ADD COLUMN \"preferred_language\" TEXT",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "drivers",
    "column": null,
    "detail": {
     "name": "idx_drivers_carrier",
     "unique": false,
     "concurrently": true,
     "columns": [
      "carrier_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_drivers_carrier\" ON \"drivers\" (\"carrier_id\")",
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
     "active":
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
    "employment_type",
    "hired_on",
    "preferred_language"
   ],
   "removed": [],
   "added": [
    "preferred_language"
   ],
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
    "employment_type",
    "hired_on",
    "preferred_language"
   ],
   "removed": [],
   "added": [
    "preferred_language"
   ],
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
 "verified": true,
 "problems": [],
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
     "employment_type",
     "hired_on",
     "preferred_language"
    ],
    "removed": [],
    "added": [
     "preferred_language"
    ],
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
     "employment_type",
     "hired_on",
     "preferred_language"
    ],
    "removed": [],
    "added": [
     "preferred_language"
    ],
    "sql": "SELECT * FROM \"driver_roster\" LIMIT 1"
   }
  ],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 17,
  "queries_ok_before": 17,
  "queries_ok_after": 17
 },
 "unmodelled": []
}
```

**tool** `plan.audit` (3.69 ms)

```json
{
 "args": {
  "plan": {
   "attempt": 1,
   "phase1_sql": [
    "ALTER TABLE \"drivers\" ADD COLUMN \"preferred_language\" TEXT;",
    "CREATE INDEX CONCURRENTLY \"idx_drivers_carrier\" ON \"drivers\" (\"carrier_id\");"
   ],
   "phase2_sql": [],
   "rollback_sql": [
    "ALTER TABLE \"drivers\" DROP COLUMN \"preferred_language\";",
    "DROP INDEX CONCURRENTLY \"idx_drivers_carrier\";"
   ],
   "code_steps": [],
   "human_gates": [],
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
    "label": "dispatch board",
    "sql": "SELECT id, reference, status, promised_at FROM shipments WHERE status = 'in_transit
```

_tool responded_

```json
{
 "statements_audited": 4,
 "scripts": {
  "phase1": 2,
  "phase2": 0,
  "rollback": 2
 },
 "findings": [],
 "finding_codes": [],
 "gaps": [],
 "gap_kinds": [],
 "kind_inventory": [
  {
   "script": "phase1",
   "statement_index": 0,
   "kind": "add_column",
   "bucket": "RULED"
  },
  {
   "script": "phase1",
   "statement_index": 1,
   "kind": "create_index",
   "bucket": "RULED"
  },
  {
   "script": "rollback",
   "statement_index": 0,
   "kind": "drop_column",
   "bucket": "RULED"
  },
  {
   "script": "rollback",
   "statement_index": 1,
   "kind": "drop_index",
   "bucket": "RULED"
  }
 ],
 "gates_trusted": 0,
 "replay": {
  "ran": true,
  "scripts": {
   "rollback": {
    "queries_run": 17,
    "broken_after": 0,
    "broken_query_ids": []
   }
  },
  "note": "the generated phase 2 is expected to break today's statements - that is what the code steps are for. The number is publi..."
 },
 "clean": true
}
```

**model** `scripted-v1` tag=`executive_summary` tokens=38/34 cost=$0.0

> No blocking hazards found. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
