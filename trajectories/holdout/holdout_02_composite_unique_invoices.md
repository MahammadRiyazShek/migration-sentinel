# Trajectory - holdout_02_composite_unique_invoices

- run id: `eval-holdout_02_composite_unique_invoices`
- case: `holdout_02_composite_unique_invoices`
- events: 28

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_02_composite_unique_invoices",
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

**tool** `schema.parse` (0.88 ms)

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
  "sql": "CREATE UNIQUE INDEX idx_carrier_invoices_number ON carrier_invoices (carrier_id, invoice_number);\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "create_index",
  "table": "carrier_invoices",
  "column": null,
  "detail": {
   "name": "idx_carrier_invoices_number",
   "unique": true,
   "concurrently": false,
   "columns": [
    "carrier_id",
    "invoice_number"
   ]
  },
  "sql": "CREATE UNIQUE INDEX idx_carrier_invoices_number ON carrier_invoices (carrier_id, invoice_number)",
  "index": 0
 }
]
```

**tool** `schema.apply_ops` (0.1 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "create_index",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
     "name": "idx_carrier_invoices_number",
     "unique": true,
     "concurrently": false,
     "columns": [
      "carrier_id",
      "invoice_number"
     ]
    },
    "sql": "CREATE UNIQUE INDEX idx_carrier_invoices_number ON carrier_invoices (carrier_id, invoice_number)",
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
  "create_index"
 ],
 "tables_touched": [
  "carrier_invoices"
 ],
 "unmodelled": []
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_02_composite_unique_invoices",
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

**tool** `corpus.dependents` (0.13 ms)

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
  "query_id": "q_finance_totals",
  "service": "finance-ops",
  "criticality": "high",
  "matched": [
   "carrier_id",
   "carrier_invoices"
  ],
  "uses_select_star": false,
  "label": "carrier spend rollup"
 },
 {
  "query_id": "q_finance_lookup",
  "service": "finance-ops",
  "criticality": "medium",
  "matched": [
   "carrier_id",
   "carrier_invoices",
   "invoice_number"
  ],
  "uses_select_star": false,
  "label": "invoice lookup"
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
    "query_id": "q_finance_totals",
    "service": "finance-ops",
    "criticality": "high",
    "matched": [
     "carrier_id",
     "carrier_invoices"
    ],
    "uses_select_star": false,
    "label": "carrier spend rollup"
   },
   {
    "query_id": "q_finance_lookup",
    "service": "finance-ops",
    "criticality": "medium",
    "matched": [
     "carrier_id",
     "carrier_invoices",
     "invoice_number"
    ],
    "uses_select_star": false,
    "label": "invoice lookup"
   }
  ]
 }
}
```

_tool responded_

```json
14
```

**tool** `shadow.replay` (3.56 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "create_index",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
     "name": "idx_carrier_invoices_number",
     "unique": true,
     "concurrently": false,
     "columns": [
      "carrier_id",
      "invoice_number"
     ]
    },
    "sql": "CREATE UNIQUE INDEX idx_carrier_invoices_number ON carrier_invoices (carrier_id, invoice_number)",
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
     "i
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [
  "backfill carrier_invoices: UNIQUE constraint failed: carrier_invoices.carrier_id, carrier_invoices.invoice_number (row={..."
 ],
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
 "blast_score": 14,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [
   "backfill carrier_invoices: UNIQUE constraint failed: carrier_invoices.carrier_id, carrier_invoices.invoice_number (row={'id': 4, 'carrier_id': 8, 'invoice_number': 'MRLN-88', 'shipment_id': None, 'amount': 410.75, 'currency': 'gbp', 'status': 'received', 'received_on': '2026-02-27'})"
  ],
  "broken": [],
  "column_drift": [],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 17,
  "queries_ok_before": 17,
  "queries_ok_after": 17
 },
 "hazards_found": [
  "UNIQUE_VIOLATION_EXISTING_DATA"
 ]
}
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_02_composite_unique_invoices",
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
  "UNIQUE_VIOLATION_EXISTING_DATA"
 ]
}
```

</details>

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "INDEX_LOCK_NO_CONCURRENT",
  "table": "carrier_invoices"
 }
}
```

_tool responded_

```json
[
 0,
 [
  "INC-2024-07"
 ]
]
```

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "UNIQUE_VIOLATION_EXISTING_DATA",
  "table": "carrier_invoices"
 }
}
```

_tool responded_

```json
[
 0,
 [
  "INC-2025-04"
 ]
]
```

**tool** `coverage.ledger` (0.2 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "create_index",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
     "name": "idx_carrier_invoices_number",
     "unique": true,
     "concurrently": false,
     "columns": [
      "carrier_id",
      "invoice_number"
     ]
    },
    "sql": "CREATE UNIQUE INDEX idx_carrier_invoices_number ON carrier_invoices (carrier_id, invoice_number)",
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
    "id
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

**model** `scripted-v1` tag=`hazard_narrative` tokens=473/71 cost=$0.0

> Index built without CONCURRENTLY on a large table. Writes queue behind the build; at this row count that is a user-visible stall. Evidence: statement 0: `CREATE UNIQUE INDEX idx_carrier_invoices_number ON carrier_invoices (carrier_id, invoice_number)` Previously bit us in INC-2024-07.

**model** `scripted-v1` tag=`hazard_narrative` tokens=483/96 cost=$0.0

> Uniqueness conflicts with data already in the table. The index build fails partway through, leaving the deploy half-applied. Evidence: shadow backfill: backfill carrier_invoices: UNIQUE constraint failed: carrier_invoices.carrier_id, carrier_invoices.invoice_number (row={'id': 4, 'carrier_id': 8, 'invoice_number': 'MRLN-88', 'shipment_id': None, 'amo Previously bit us in INC-2025-04.

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
   "code": "INDEX_LOCK_NO_CONCURRENT",
   "severity": "blocker",
   "source": "static",
   "memory": [
    "INC-2024-07"
   ]
  },
  {
   "code": "UNIQUE_VIOLATION_EXISTING_DATA",
   "severity": "blocker",
   "source": "replay",
   "memory": [
    "INC-2025-04"
   ]
  }
 ]
}
```

## Agent: rollout_engineer

**Goal** Rewrite the migration as a phase-1 (expand, safe now) / phase-2 (contract, after the code deploy) plan with a rollback, and surface every step that needs a human decision.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_02_composite_unique_invoices",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "INDEX_LOCK_NO_CONCURRENT",
  "UNIQUE_VIOLATION_EXISTING_DATA"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=487/28 cost=$0.0

> - What is the acceptable write-stall window for this table?
> - Who owns cleaning the duplicate rows, and by when?

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
 "case": "holdout_02_composite_unique_invoices",
 "attempt": 1,
 "phase1_statements": 1
}
```

</details>

**tool** `migration.parse` (0.05 ms)

```json
{
 "args": {
  "sql": "CREATE INDEX CONCURRENTLY \"idx_carrier_invoices_number_tmp_nonunique\" ON \"carrier_invoices\" (\"carrier_id\", \"invoice_number\");"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "create_index",
  "table": "carrier_invoices",
  "column": null,
  "detail": {
   "name": "idx_carrier_invoices_number_tmp_nonunique",
   "unique": false,
   "concurrently": true,
   "columns": [
    "carrier_id",
    "invoice_number"
   ]
  },
  "sql": "CREATE INDEX CONCURRENTLY \"idx_carrier_invoices_number_tmp_nonunique\" ON \"carrier_invoices\" (\"carrier_id\", \"invoice_numb...",
  "index": 0
 }
]
```

**tool** `schema.apply_ops` (0.08 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "create_index",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
     "name": "idx_carrier_invoices_number_tmp_nonunique",
     "unique": false,
     "concurrently": true,
     "columns": [
      "carrier_id",
      "invoice_number"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_carrier_invoices_number_tmp_nonunique\" ON \"carrier_invoices\" (\"carrier_id\", \"invoice_numb...",
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

**tool** `shadow.replay` (3.56 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "create_index",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
     "name": "idx_carrier_invoices_number_tmp_nonunique",
     "unique": false,
     "concurrently": true,
     "columns": [
      "carrier_id",
      "invoice_number"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_carrier_invoices_number_tmp_nonunique\" ON \"carrier_invoices\" (\"carrier_id\", \"invoice_numb...",
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
     "las
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

**model** `scripted-v1` tag=`executive_summary` tokens=38/35 cost=$0.0

> Do not ship this as written. 2 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
