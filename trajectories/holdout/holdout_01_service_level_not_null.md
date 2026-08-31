# Trajectory - holdout_01_service_level_not_null

- run id: `eval-holdout_01_service_level_not_null`
- case: `holdout_01_service_level_not_null`
- events: 29

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_01_service_level_not_null",
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

**tool** `schema.parse` (1.05 ms)

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
  "sql": "ALTER TABLE shipments ADD COLUMN service_level TEXT NOT NULL;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "shipments",
  "column": "service_level",
  "detail": {
   "type": "TEXT",
   "not_null": true,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE shipments ADD COLUMN service_level TEXT NOT NULL",
  "index": 0
 }
]
```

**tool** `migration.audit` (0.05 ms)

```json
{
 "args": {
  "migration_sql": "ALTER TABLE shipments ADD COLUMN service_level TEXT NOT NULL;\n",
  "ops": [
   {
    "kind": "add_column",
    "table": "shipments",
    "column": "service_level",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE shipments ADD COLUMN service_level TEXT NOT NULL",
    "index": 0
   }
  ]
 }
}
```

_tool responded_

```json
{
 "lexed_statements": 1,
 "ops": 1,
 "unterminated": [],
 "unaccounted": [],
 "procedural": [],
 "conservation": {
  "significant_chars": 52,
  "attributed_chars": 52,
  "unattributed_chars": 0
 },
 "clean": true
}
```

**tool** `schema.apply_ops` (0.08 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "shipments",
    "column": "service_level",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE shipments ADD COLUMN service_level TEXT NOT NULL",
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
  "add_column"
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
 "case": "holdout_01_service_level_not_null",
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

**tool** `corpus.dependents` (0.2 ms)

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

**tool** `corpus.blast_score` (0.07 ms)

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

**tool** `shadow.replay` (3.84 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "shipments",
    "column": "service_level",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE shipments ADD COLUMN service_level TEXT NOT NULL",
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
 "data_errors": [
  "backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 1, 'carrier_id': 7, 'vehicle_id': 1,...",
  "backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 2, 'carrier_id': 7, 'vehicle_id': 2,...",
  "backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 3, 'carrier_id': 8, 'vehicle_id': 3,...",
  "backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 4, 'carrier_id': 9, 'vehicle_id': No..."
 ],
 "broken": [
  {
   "query_id": "q_dispatch_create",
   "service": "dispatch-api",
   "criticality": "critical",
   "label": "shipment creation",
   "error": "IntegrityError: NOT NULL constraint failed: shipments.service_level",
   "sql": "INSERT INTO shipments (carrier_id, reference, status, weight_kg, promised_at) VALUES (7,'SHP-77001','planned',1200,'2026..."
  }
 ],
 "column_drift": [],
 "rowcount_drift": [
  {
   "query_id": "q_dispatch_board",
   "service": "dispatch-api",
   "before_rows": 1,
   "after_rows": 0,
   "sql": "SELECT id, reference, status, promised_at FROM shipments WHERE status = 'in_transit'"
  },
  {
   "query_id": "q_portal_track",
   "service": "customer-portal",
   "before_rows": 1,
   "after_rows": 0,
   "sql": "SELECT reference, status, promised_at, delivered_at FROM shipments WHERE reference = 'SHP-10001'"
  },
  {
   "query_id": "q_ops_active",
   "service": "ops-console",
   "before_rows": 2,
   "after_rows": 0,
   "sql": "SELECT * FROM active_shipments"
  },
  {
   "query_id": "q_etl_volume",
   "service": "bi-etl",
   "before_rows": 4,
   "after_rows": 0,
   "sql": "SELECT status, COUNT(*) AS n FROM shipments GROUP BY status"
  },
  {
   "query_id": "__view__active_shipments",
   "service": "database",
   "before_rows": 1,
   "after_rows": 0,
   "sql": "SELECT * FROM \"active_shipments\" LIMIT 1"
  }
 ],
 "data_loss": [],
 "queries_run": 17,
 "queries_ok_before
```

**result**

```json
{
 "dependent_queries": 5,
 "blast_score": 17,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [
   "backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 1, 'carrier_id': 7, 'vehicle_id': 1, 'parent_shipment_id': None, 'reference': 'SHP-10001', 'legacy_ref': 'OLD-4471', 'status': 'in_transit', 'weight_kg': 8200, 'promised_at': '2026-03-02', 'delivered_at': None})",
   "backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 2, 'carrier_id': 7, 'vehicle_id': 2, 'parent_shipment_id': 1, 'reference': 'SHP-10002', 'legacy_ref': None, 'status': 'planned', 'weight_kg': 1400, 'promised_at': '2026-03-03', 'delivered_at': None})",
   "backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 3, 'carrier_id': 8, 'vehicle_id': 3, 'parent_shipment_id': None, 'reference': 'SHP-10003', 'legacy_ref': 'OLD-4480', 'status': 'delivered', 'weight_kg': 19750, 'promised_at': '2026-02-25', 'delivered_at': '2026-02-25'})",
   "backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 4, 'carrier_id': 9, 'vehicle_id': None, 'parent_shipment_id': None, 'reference': 'SHP-10004', 'legacy_ref': None, 'status': 'cancelled', 'weight_kg': 0, 'promised_at': '2026-02-20', 'delivered_at': None})"
  ],
  "broken": [
   {
    "query_id": "q_dispatch_create",
    "service": "dispatch-api",
    "criticality": "critical",
    "label": "shipment creation",
    "error": "IntegrityError: NOT NULL constraint failed: shipments.service_level",
    "sql": "INSERT INTO shipments (carrier_id, reference, status, weight_kg, promised_at) VALUES (7,'SHP-77001','planned',1200,'2026-03-02')"
   }
  ],
  "column_drift": [],
  "rowcount_drift": [
   {
    "query_id": "q_dispatch_board",
    "service": "dispatch-api",
    "before_rows": 1,
    "after_rows": 0,
    "sql": "SELECT id, reference, status, promised_at FROM shipments WHERE status = 'in_transit'"
   },
   {
    "query_id": "
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_01_service_level_not_null",
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
  "BREAKING_QUERY",
  "NOT_NULL_NO_DEFAULT",
  "NOT_NULL_NO_DEFAULT",
  "NOT_NULL_NO_DEFAULT",
  "NOT_NULL_NO_DEFAULT"
 ]
}
```

</details>

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "BREAKING_QUERY",
  "table": "q_dispatch_create"
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

**tool** `memory.escalation` (0.0 ms)

```json
{
 "args": {
  "hazard_code": "NOT_NULL_NO_DEFAULT",
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

**tool** `coverage.ledger` (0.18 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "add_column",
    "table": "shipments",
    "column": "service_level",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE shipments ADD COLUMN service_level TEXT NOT NULL",
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
    "label": "public t
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

**model** `scripted-v1` tag=`hazard_narrative` tokens=477/92 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `INSERT INTO shipments (carrier_id, reference, status, weight_kg, promised_at) VALUES (7,'SHP-77001','planned',1200,'2026` -> IntegrityError: NOT NULL constraint failed: shipments.service_level Owning service(s): dispatch-api.

**model** `scripted-v1` tag=`hazard_narrative` tokens=654/84 cost=$0.0

> NOT NULL added without a usable default. Existing rows or in-flight inserts violate the constraint immediately. Evidence: shadow backfill: backfill shipments: NOT NULL constraint failed: shipments.service_level (row={'id': 1, 'carrier_id': 7, 'vehicle_id': 1, 'parent_shipment_id': None, 'reference': 'SHP-10001', 'legacy_ref': 'OLD-4471',

**result**

```json
{
 "verdict": "BLOCK",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 0,
  "blocker": 2
 },
 "coverage_gaps": [],
 "verdict_capped_by_coverage": false,
 "hazards": [
  {
   "code": "BREAKING_QUERY",
   "severity": "blocker",
   "source": "replay",
   "memory": []
  },
  {
   "code": "NOT_NULL_NO_DEFAULT",
   "severity": "blocker",
   "source": "replay",
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
 "case": "holdout_01_service_level_not_null",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "BREAKING_QUERY",
  "NOT_NULL_NO_DEFAULT"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=482/29 cost=$0.0

> - Which deploy lands first: the query change or the schema change?
> - What is the accepted risk for NOT_NULL_NO_DEFAULT?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 1,
 "phase2_statements": 1,
 "human_gates": 1
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_01_service_level_not_null",
 "attempt": 1,
 "phase1_statements": 1
}
```

</details>

**tool** `migration.parse` (0.05 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"shipments\" ADD COLUMN \"service_level\" TEXT;"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "shipments",
  "column": "service_level",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE \"shipments\" ADD COLUMN \"service_level\" TEXT",
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
    "kind": "add_column",
    "table": "shipments",
    "column": "service_level",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"shipments\" ADD COLUMN \"service_level\" TEXT",
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

**tool** `shadow.replay` (3.46 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "shipments",
    "column": "service_level",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"shipments\" ADD COLUMN \"service_level\" TEXT",
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

**model** `scripted-v1` tag=`executive_summary` tokens=38/60 cost=$0.0

> Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
