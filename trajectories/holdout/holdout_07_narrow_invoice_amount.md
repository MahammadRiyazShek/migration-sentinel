# Trajectory - holdout_07_narrow_invoice_amount

- run id: `eval-holdout_07_narrow_invoice_amount`
- case: `holdout_07_narrow_invoice_amount`
- events: 31

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_07_narrow_invoice_amount",
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

**tool** `schema.parse` (1.01 ms)

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

**tool** `migration.parse` (0.06 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2);\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "alter_type",
  "table": "carrier_invoices",
  "column": "amount",
  "detail": {
   "new_type": "numeric(8,2)"
  },
  "sql": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2)",
  "index": 0
 }
]
```

**tool** `migration.audit` (0.05 ms)

```json
{
 "args": {
  "migration_sql": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2);\n",
  "ops": [
   {
    "kind": "alter_type",
    "table": "carrier_invoices",
    "column": "amount",
    "detail": {
     "new_type": "numeric(8,2)"
    },
    "sql": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2)",
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
  "significant_chars": 59,
  "attributed_chars": 59,
  "unattributed_chars": 0
 },
 "clean": true
}
```

**tool** `schema.apply_ops` (0.07 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "alter_type",
    "table": "carrier_invoices",
    "column": "amount",
    "detail": {
     "new_type": "numeric(8,2)"
    },
    "sql": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2)",
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
  "alter_type"
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
 "case": "holdout_07_narrow_invoice_amount",
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
  "query_id": "q_finance_totals",
  "service": "finance-ops",
  "criticality": "high",
  "matched": [
   "amount",
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
   "amount",
   "carrier_invoices"
  ],
  "uses_select_star": false,
  "label": "invoice lookup"
 }
]
```

**tool** `corpus.blast_score` (0.01 ms)

```json
{
 "args": {
  "hits": [
   {
    "query_id": "q_finance_totals",
    "service": "finance-ops",
    "criticality": "high",
    "matched": [
     "amount",
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
     "amount",
     "carrier_invoices"
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
5
```

**tool** `shadow.replay` (3.29 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "alter_type",
    "table": "carrier_invoices",
    "column": "amount",
    "detail": {
     "new_type": "numeric(8,2)"
    },
    "sql": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2)",
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
 "data_loss": [
  {
   "table": "carrier_invoices",
   "column": "amount",
   "from": "NUMERIC(12,2)",
   "to": "numeric(8,2)",
   "rows_checked": 5,
   "offending_samples": [],
   "offending_rows": 0
  }
 ],
 "queries_run": 17,
 "queries_ok_before": 17,
 "queries_ok_after": 17
}
```

**result**

```json
{
 "dependent_queries": 2,
 "blast_score": 5,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [],
  "broken": [],
  "column_drift": [],
  "rowcount_drift": [],
  "data_loss": [
   {
    "table": "carrier_invoices",
    "column": "amount",
    "from": "NUMERIC(12,2)",
    "to": "numeric(8,2)",
    "rows_checked": 5,
    "offending_samples": [],
    "offending_rows": 0
   }
  ],
  "queries_run": 17,
  "queries_ok_before": 17,
  "queries_ok_after": 17
 },
 "hazards_found": [
  "TYPE_NARROWING_DATA_LOSS"
 ]
}
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_07_narrow_invoice_amount",
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
  "TYPE_NARROWING_DATA_LOSS"
 ]
}
```

</details>

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "TABLE_REWRITE_LOCK",
  "table": "carrier_invoices"
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
  "hazard_code": "TYPE_NARROWING_DATA_LOSS",
  "table": "carrier_invoices"
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

**tool** `coverage.ledger` (0.28 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "alter_type",
    "table": "carrier_invoices",
    "column": "amount",
    "detail": {
     "new_type": "numeric(8,2)"
    },
    "sql": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2)",
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
    "sql": "SELECT reference, stat
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "fixture_bounded_value_scan",
   "object": "carrier_invoices.amount",
   "object_inferred": false,
   "statement_index": 0,
   "statement": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2)",
   "why": "the value scan for carrier_invoices.amount -> numeric(8,2) ran over 5 fixture row(s) against a declared 9,400,000 in pro...",
   "closes_with": "a reviewer counts the real offenders before phase 2: SELECT count(*) FROM carrier_invoices WHERE amount would not fit nu...",
   "irreversible": true
  }
 ],
 "gap_kinds": [
  "fixture_bounded_value_scan"
 ],
 "irreversible": [
  "carrier_invoices.amount"
 ],
 "corpus_statements": 15,
 "parser_notes": []
}
```

_note (risk_officer)_: verdict capped to NEEDS_COVERAGE_SIGNOFF: 1 coverage gap(s) on objects this migration touches (carrier_invoices.amount). No hazard was invented; the packet cannot certify what it did not see.

**model** `scripted-v1` tag=`hazard_narrative` tokens=441/54 cost=$0.0

> Type change forces a full table rewrite. An ACCESS EXCLUSIVE lock for the length of the rewrite is downtime by another name. Evidence: statement 0: `ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2)`

**model** `scripted-v1` tag=`hazard_narrative` tokens=428/39 cost=$0.0

> Narrowing type change can silently lose data. Values that do not fit are truncated or rejected, and the old values are gone. Evidence: value scan offenders=[]

**result**

```json
{
 "verdict": "NEEDS_COVERAGE_SIGNOFF",
 "counts": {
  "low": 0,
  "medium": 1,
  "high": 1,
  "blocker": 0
 },
 "coverage_gaps": [
  "fixture_bounded_value_scan:carrier_invoices.amount"
 ],
 "verdict_capped_by_coverage": true,
 "hazards": [
  {
   "code": "TABLE_REWRITE_LOCK",
   "severity": "high",
   "source": "static",
   "memory": []
  },
  {
   "code": "TYPE_NARROWING_DATA_LOSS",
   "severity": "medium",
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
 "case": "holdout_07_narrow_invoice_amount",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "TABLE_REWRITE_LOCK",
  "TYPE_NARROWING_DATA_LOSS"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=484/27 cost=$0.0

> - What is the accepted risk for TABLE_REWRITE_LOCK?
> - Is the truncated value recoverable from anywhere else?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 2,
 "phase2_statements": 2,
 "human_gates": 1
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_07_narrow_invoice_amount",
 "attempt": 1,
 "phase1_statements": 2
}
```

</details>

**tool** `migration.parse` (0.11 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"carrier_invoices\" ADD COLUMN \"amount_new\" numeric(8,2);\nUPDATE \"carrier_invoices\" SET \"amount_new\" = \"amount\" WHERE \"amount_new\" IS NULL AND \"id\" IN (SELECT \"id\" FROM \"carrier_invoices\" WHERE \"amount_new\" IS NULL LIMIT 5000);"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "carrier_invoices",
  "column": "amount_new",
  "detail": {
   "type": "numeric(8,2)",
   "not_null": false,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE \"carrier_invoices\" ADD COLUMN \"amount_new\" numeric(8,2)",
  "index": 0
 },
 {
  "kind": "dml_update",
  "table": "carrier_invoices",
  "column": null,
  "detail": {
   "where": true,
   "batched": true
  },
  "sql": "UPDATE \"carrier_invoices\" SET \"amount_new\" = \"amount\" WHERE \"amount_new\" IS NULL AND \"id\" IN (SELECT \"id\" FROM \"carrier_...",
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
    "table": "carrier_invoices",
    "column": "amount_new",
    "detail": {
     "type": "numeric(8,2)",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"carrier_invoices\" ADD COLUMN \"amount_new\" numeric(8,2)",
    "index": 0
   },
   {
    "kind": "dml_update",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": true
    },
    "sql": "UPDATE \"carrier_invoices\" SET \"amount_new\" = \"amount\" WHERE \"amount_new\" IS NULL AND \"id\" IN (SELECT \"id\" FROM \"carrier_...",
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

**tool** `shadow.replay` (3.45 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "carrier_invoices",
    "column": "amount_new",
    "detail": {
     "type": "numeric(8,2)",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"carrier_invoices\" ADD COLUMN \"amount_new\" numeric(8,2)",
    "index": 0
   },
   {
    "kind": "dml_update",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": true
    },
    "sql": "UPDATE \"carrier_invoices\" SET \"amount_new\" = \"amount\" WHERE \"amount_new\" IS NULL AND \"id\" IN (SELECT \"id\" FROM \"carrier_...",
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

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 1 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - coverage sign-off: **REQUIRED**

The verdict is capped at NEEDS_COVERAGE_SIGNOFF. The hazards found are not blocking, but this review has 1 declared blind spot(s) on objects the migration touches, and a packet must not certify what it did not see. Each gap is a human gate in the plan.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
