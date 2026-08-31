# Trajectory - holdout_08_release_train_fleet

- run id: `eval-holdout_08_release_train_fleet`
- case: `holdout_08_release_train_fleet`
- events: 46

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_08_release_train_fleet",
 "migration_statements": 6,
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

**tool** `schema.parse` (1.02 ms)

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

**tool** `migration.parse` (0.2 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE drivers RENAME COLUMN phone TO phone_e164;\nCREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id);\nALTER TABLE shipments DROP COLUMN legacy_ref;\nUPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed';\nALTER TABLE carrier_invoices ADD CONSTRAINT carrier_invoices_shipment_fk\n  FOREIGN KEY (shipment_id) REFERENCES shipments (id);\nVACUUM FULL shipments;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "rename_column",
  "table": "drivers",
  "column": "phone",
  "detail": {
   "new_name": "phone_e164"
  },
  "sql": "ALTER TABLE drivers RENAME COLUMN phone TO phone_e164",
  "index": 0
 },
 {
  "kind": "create_index",
  "table": "geofence_events",
  "column": null,
  "detail": {
   "name": "idx_geofence_events_shipment",
   "unique": false,
   "concurrently": false,
   "columns": [
    "shipment_id"
   ]
  },
  "sql": "CREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id)",
  "index": 1
 },
 {
  "kind": "drop_column",
  "table": "shipments",
  "column": "legacy_ref",
  "detail": {},
  "sql": "ALTER TABLE shipments DROP COLUMN legacy_ref",
  "index": 2
 },
 {
  "kind": "dml_update",
  "table": "shipment_stops",
  "column": null,
  "detail": {
   "where": true,
   "batched": false
  },
  "sql": "UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed'",
  "index": 3
 },
 {
  "kind": "add_constraint",
  "table": "carrier_invoices",
  "column": null,
  "detail": {
   "constraint": "carrier_invoices_shipment_fk",
   "constraint_kind": "foreign_key",
   "expr": "(shipment_id) REFERENCES shipments (id)",
   "columns": [],
   "not_valid": false
  },
  "sql": "ALTER TABLE carrier_invoices ADD CONSTRAINT carrier_invoices_shipment_fk FOREIGN KEY (shipment_id) REFERENCES shipments ...",
  "index": 4
 },
 {
  "kind": "maintenance_rewrite",
  "table": "shipments",
  "column": null,
  "detail": {
   "command": "VACUUM FULL"
  },
  "sql": "VACUUM FULL shipments",
  "index": 5
 }
]
```

**tool** `migration.audit` (0.22 ms)

```json
{
 "args": {
  "migration_sql": "ALTER TABLE drivers RENAME COLUMN phone TO phone_e164;\nCREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id);\nALTER TABLE shipments DROP COLUMN legacy_ref;\nUPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed';\nALTER TABLE carrier_invoices ADD CONSTRAINT carrier_invoices_shipment_fk\n  FOREIGN KEY (shipment_id) REFERENCES shipments (id);\nVACUUM FULL shipments;\n",
  "ops": [
   {
    "kind": "rename_column",
    "table": "drivers",
    "column": "phone",
    "detail": {
     "new_name": "phone_e164"
    },
    "sql": "ALTER TABLE drivers RENAME COLUMN phone TO phone_e164",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "geofence_events",
    "column": null,
    "detail": {
     "name": "idx_geofence_events_shipment",
     "unique": false,
     "concurrently": false,
     "columns": [
      "shipment_id"
     ]
    },
    "sql": "CREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id)",
    "index": 1
   },
   {
    "kind": "drop_column",
    "table": "shipments",
    "column": "legacy_ref",
    "detail": {},
    "sql": "ALTER TABLE shipments DROP COLUMN legacy_ref",
    
```

_tool responded_

```json
{
 "lexed_statements": 6,
 "ops": 6,
 "unterminated": [],
 "unaccounted": [],
 "procedural": [],
 "conservation": {
  "significant_chars": 345,
  "attributed_chars": 345,
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
    "kind": "rename_column",
    "table": "drivers",
    "column": "phone",
    "detail": {
     "new_name": "phone_e164"
    },
    "sql": "ALTER TABLE drivers RENAME COLUMN phone TO phone_e164",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "geofence_events",
    "column": null,
    "detail": {
     "name": "idx_geofence_events_shipment",
     "unique": false,
     "concurrently": false,
     "columns": [
      "shipment_id"
     ]
    },
    "sql": "CREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id)",
    "index": 1
   },
   {
    "kind": "drop_column",
    "table": "shipments",
    "column": "legacy_ref",
    "detail": {},
    "sql": "ALTER TABLE shipments DROP COLUMN legacy_ref",
    "index": 2
   },
   {
    "kind": "dml_update",
    "table": "shipment_stops",
    "column": null,
    "detail": {
     "where": true,
     "batched": false
    },
    "sql": "UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed'",
    "index": 3
   },
   {
    "kind": "add_constraint",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
     "constraint": "carrier_invoic
```

_tool responded_

```json
[
 "Schema",
 [
  "op 5 (maintenance_rewrite) not modelled structurally: VACUUM FULL shipments"
 ]
]
```

_note (cartographer)_: Some statements could not be modelled structurally; they are passed to the risk officer as unknowns rather than silently assumed safe.

**result**

```json
{
 "op_kinds": [
  "add_constraint",
  "create_index",
  "dml_update",
  "drop_column",
  "maintenance_rewrite",
  "rename_column"
 ],
 "tables_touched": [
  "carrier_invoices",
  "drivers",
  "geofence_events",
  "shipment_stops",
  "shipments"
 ],
 "unmodelled": [
  "op 5 (maintenance_rewrite) not modelled structurally: VACUUM FULL shipments"
 ]
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_08_release_train_fleet",
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

**tool** `corpus.dependents` (0.28 ms)

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
  "query_id": "q_dispatch_stop_progress",
  "service": "dispatch-api",
  "criticality": "high",
  "matched": [
   "shipment_stops"
  ],
  "uses_select_star": false,
  "label": "mark a stop arrived"
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
  "query_id": "q_driver_stop_list",
  "service": "driver-app",
  "criticality": "critical",
  "matched": [
   "shipment_id",
   "shipment_stops"
  ],
  "uses_select_star": false,
  "label": "today's stop list"
 },
 {
  "query_id": "q_driver_stop_arrive",
  "service": "driver-app",
  "criticality": "critical",
  "matched": [
   "shipment_id",
   "shipment_stops"
  ],
  "uses_select_star": false,
  "label": "driver marks arrival"
 },
 {
  "query_id": "q_driver_profile",
  "service": "driver-app",
  "criticality": "high",
  "matched": [
   "drivers",
   "phone"
  ],
  "uses_select_star": false,
  "label": "driver profile in the app"
 },
 "...+5 more"
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
    "query_id": "q_dispatch_stop_progress",
    "service": "dispatch-api",
    "criticality": "high",
    "matched": [
     "shipment_stops"
    ],
    "uses_select_star": false,
    "label": "mark a stop arrived"
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
    "query_id": "q_driver_stop_list",
    "service": "driver-app",
    "criticality": "
```

_tool responded_

```json
42
```

**tool** `shadow.replay` (3.33 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "rename_column",
    "table": "drivers",
    "column": "phone",
    "detail": {
     "new_name": "phone_e164"
    },
    "sql": "ALTER TABLE drivers RENAME COLUMN phone TO phone_e164",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "geofence_events",
    "column": null,
    "detail": {
     "name": "idx_geofence_events_shipment",
     "unique": false,
     "concurrently": false,
     "columns": [
      "shipment_id"
     ]
    },
    "sql": "CREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id)",
    "index": 1
   },
   {
    "kind": "drop_column",
    "table": "shipments",
    "column": "legacy_ref",
    "detail": {},
    "sql": "ALTER TABLE shipments DROP COLUMN legacy_ref",
    "index": 2
   },
   {
    "kind": "dml_update",
    "table": "shipment_stops",
    "column": null,
    "detail": {
     "where": true,
     "batched": false
    },
    "sql": "UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed'",
    "index": 3
   },
   {
    "kind": "add_constraint",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
   
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [],
 "broken": [
  {
   "query_id": "q_driver_profile",
   "service": "driver-app",
   "criticality": "high",
   "label": "driver profile in the app",
   "error": "OperationalError: no such column: phone",
   "sql": "SELECT id, full_name, phone, licence_class FROM drivers WHERE id = 1"
  }
 ],
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
    "licence_class",
    "employment_type",
    "hired_on",
    "phone_e164"
   ],
   "removed": [
    "phone"
   ],
   "added": [
    "phone_e164"
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
    "licence_class",
    "employment_type",
    "hired_on",
    "phone_e164"
   ],
   "removed": [
    "phone"
   ],
   "added": [
    "phone_e164"
   ],
   "sql": "SELECT * FROM \"driver_roster\" LIMIT 1"
  }
 ],
 "rowcount_drift": [],
 "data_loss": [],
 "queries_run": 17,
 "queries_ok_before": 17,
 "queries_ok_after": 16
}
```

**result**

```json
{
 "dependent_queries": 13,
 "blast_score": 42,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [],
  "broken": [
   {
    "query_id": "q_driver_profile",
    "service": "driver-app",
    "criticality": "high",
    "label": "driver profile in the app",
    "error": "OperationalError: no such column: phone",
    "sql": "SELECT id, full_name, phone, licence_class FROM drivers WHERE id = 1"
   }
  ],
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
     "licence_class",
     "employment_type",
     "hired_on",
     "phone_e164"
    ],
    "removed": [
     "phone"
    ],
    "added": [
     "phone_e164"
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
     "licence_class",
     "employment_type",
     "hired_on",
     "phone_e164"
    ],
    "removed": [
     "phone"
    ],
    "added": [
     "phone_e164"
    ],
    "sql": "SELECT * FROM \"driver_roster\" LIMIT 1"
   }
  ],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 17,
  "queries_ok_before": 17,
  "queries_ok_after": 16
 },
 "hazards_found": [
  "BREAKING_QUERY",
  "SELECT_STAR_DRIFT"
 ]
}
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_08_release_train_fleet",
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
  "SELECT_STAR_DRIFT"
 ]
}
```

</details>

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "BREAKING_QUERY",
  "table": "q_driver_profile"
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
  "hazard_code": "INDEX_LOCK_NO_CONCURRENT",
  "table": "geofence_events"
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

**tool** `memory.escalation` (0.0 ms)

```json
{
 "args": {
  "hazard_code": "CONSTRAINT_VALIDATION_LOCK",
  "table": "carrier_invoices"
 }
}
```

_tool responded_

```json
[
 0,
 [
  "INC-2024-11"
 ]
]
```

**tool** `memory.escalation` (0.0 ms)

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

**tool** `memory.escalation` (0.0 ms)

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
  "hazard_code": "DESTRUCTIVE_NO_EXPAND_CONTRACT",
  "table": "shipments"
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
  "hazard_code": "TABLE_REWRITE_LOCK",
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

**tool** `memory.escalation` (0.0 ms)

```json
{
 "args": {
  "hazard_code": "UNBATCHED_BACKFILL",
  "table": "shipment_stops"
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

**tool** `coverage.ledger` (0.23 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "rename_column",
    "table": "drivers",
    "column": "phone",
    "detail": {
     "new_name": "phone_e164"
    },
    "sql": "ALTER TABLE drivers RENAME COLUMN phone TO phone_e164",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "geofence_events",
    "column": null,
    "detail": {
     "name": "idx_geofence_events_shipment",
     "unique": false,
     "concurrently": false,
     "columns": [
      "shipment_id"
     ]
    },
    "sql": "CREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id)",
    "index": 1
   },
   {
    "kind": "drop_column",
    "table": "shipments",
    "column": "legacy_ref",
    "detail": {},
    "sql": "ALTER TABLE shipments DROP COLUMN legacy_ref",
    "index": 2
   },
   {
    "kind": "dml_update",
    "table": "shipment_stops",
    "column": null,
    "detail": {
     "where": true,
     "batched": false
    },
    "sql": "UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed'",
    "index": 3
   },
   {
    "kind": "add_constraint",
    "table": "carrier_invoices",
    "column": null,
    "detail": {
     "constraint": "carrier_invoices_shipment_fk",
     
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "uncovered_object",
   "object": "shipments.legacy_ref",
   "object_inferred": false,
   "statement_index": 2,
   "statement": "ALTER TABLE shipments DROP COLUMN legacy_ref",
   "why": "no statement in the 15-statement corpus references legacy_ref, so replay had nothing to run against it; that is silence,...",
   "closes_with": "a reviewer greps the real consumers for legacy_ref before phase 2",
   "irreversible": false
  },
  {
   "kind": "in_place_data_mutation",
   "object": "shipment_stops.status",
   "object_inferred": false,
   "statement_index": 3,
   "statement": "UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed'",
   "why": "rows that already exist in shipment_stops are rewritten; replay proves the corpus still executes, never that it still re...",
   "closes_with": "a reviewer confirms which consumers of shipment_stops.status depend on the current values",
   "irreversible": false
  },
  {
   "kind": "unmodelled_statement",
   "object": "shipments",
   "object_inferred": false,
   "statement_index": 5,
   "statement": "VACUUM FULL shipments",
   "why": "the parser produced no structural model for this statement, so no post-migration schema and no replay covers it",
   "closes_with": "a reviewer confirms by hand what statement 5 does to shipments and to anything reading it",
   "irreversible": false
  }
 ],
 "gap_kinds": [
  "in_place_data_mutation",
  "uncovered_object",
  "unmodelled_statement"
 ],
 "irreversible": [],
 "corpus_statements": 15,
 "parser_notes": [
  "op 5 (maintenance_rewrite) not modelled structurally: VACUUM FULL shipments"
 ]
}
```

**model** `scripted-v1` tag=`hazard_narrative` tokens=449/71 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `SELECT id, full_name, phone, licence_class FROM drivers WHERE id = 1` -> OperationalError: no such column: phone Owning service(s): driver-app.

**model** `scripted-v1` tag=`hazard_narrative` tokens=469/65 cost=$0.0

> Index built without CONCURRENTLY on a large table. Writes queue behind the build; at this row count that is a user-visible stall. Evidence: statement 1: `CREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id)` Previously bit us in INC-2024-07.

**model** `scripted-v1` tag=`hazard_narrative` tokens=462/72 cost=$0.0

> Constraint added without NOT VALID / VALIDATE split. Validation scans the whole table under a lock that blocks writes. Evidence: statement 4: `ALTER TABLE carrier_invoices ADD CONSTRAINT carrier_invoices_shipment_fk FOREIGN KEY (shipment_id) REFERENCES ` Previously bit us in INC-2024-11.

**model** `scripted-v1` tag=`hazard_narrative` tokens=437/64 cost=$0.0

> Impact lands on a service owned by another team. The fix needs a deploy the migration author does not control, so ordering must be agreed first. Evidence: corpus ownership of failing statements: ['bi-etl', 'driver-app'] Owning service(s): bi-etl, driver-app.

**model** `scripted-v1` tag=`hazard_narrative` tokens=433/61 cost=$0.0

> Destructive change shipped in a single step. Dropping or renaming in one deploy means old and new application code cannot both work. Evidence: statement 0: `ALTER TABLE drivers RENAME COLUMN phone TO phone_e164` Previously bit us in INC-2023-09.

**model** `scripted-v1` tag=`hazard_narrative` tokens=433/59 cost=$0.0

> Destructive change shipped in a single step. Dropping or renaming in one deploy means old and new application code cannot both work. Evidence: statement 2: `ALTER TABLE shipments DROP COLUMN legacy_ref` Previously bit us in INC-2023-09.

**model** `scripted-v1` tag=`hazard_narrative` tokens=484/109 cost=$0.0

> SELECT * consumer receives a different column set. The query still runs, so tests pass, but downstream code indexing by position or key breaks. Evidence: shadow replay columns before=['id', 'carrier_id', 'full_name', 'phone', 'licence_class', 'employment_type', 'hired_on'] after=['id', 'carrier_id', 'full_name', 'licence_class', 'employment_type', 'hired_on', 'phone_e164'] Owning service(s): bi-etl. Previously bit us in INC-2025-02.

**model** `scripted-v1` tag=`hazard_narrative` tokens=474/42 cost=$0.0

> Type change forces a full table rewrite. An ACCESS EXCLUSIVE lock for the length of the rewrite is downtime by another name. Evidence: statement 5: `VACUUM FULL shipments`

**model** `scripted-v1` tag=`hazard_narrative` tokens=433/54 cost=$0.0

> Backfill runs as one unbounded statement. One long transaction holds locks and bloats WAL; it cannot be paused or resumed. Evidence: statement 3: `UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed'`

**model** `scripted-v1` tag=`hazard_narrative` tokens=406/30 cost=$0.0

> No rollback path supplied. Recovery at 3am should not require improvising DDL. Evidence: case field `rollback_sql` is empty

**result**

```json
{
 "verdict": "BLOCK",
 "counts": {
  "low": 0,
  "medium": 1,
  "high": 7,
  "blocker": 2
 },
 "coverage_gaps": [
  "uncovered_object:shipments.legacy_ref",
  "in_place_data_mutation:shipment_stops.status",
  "unmodelled_statement:shipments"
 ],
 "verdict_capped_by_coverage": false,
 "hazards": [
  {
   "code": "BREAKING_QUERY",
   "severity": "blocker",
   "source": "replay",
   "memory": []
  },
  {
   "code": "INDEX_LOCK_NO_CONCURRENT",
   "severity": "blocker",
   "source": "static",
   "memory": [
    "INC-2024-07"
   ]
  },
  {
   "code": "CONSTRAINT_VALIDATION_LOCK",
   "severity": "high",
   "source": "static",
   "memory": [
    "INC-2024-11"
   ]
  },
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
   "code": "TABLE_REWRITE_LOCK",
   "severity": "high",
   "source": "static",
   "memory": []
  },
  {
   "code": "UNBATCHED_BACKFILL",
   "severity": "high",
   "source": "static",
   "memory": []
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
 "case": "holdout_08_release_train_fleet",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "BREAKING_QUERY",
  "CONSTRAINT_VALIDATION_LOCK",
  "CROSS_SERVICE_UNCOORDINATED",
  "DESTRUCTIVE_NO_EXPAND_CONTRACT",
  "INDEX_LOCK_NO_CONCURRENT",
  "MISSING_ROLLBACK",
  "SELECT_STAR_DRIFT",
  "TABLE_REWRITE_LOCK",
  "UNBATCHED_BACKFILL"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=528/87 cost=$0.0

> - Which deploy lands first: the query change or the schema change?
> - What is the accepted risk for CONSTRAINT_VALIDATION_LOCK?
> - Has the owning team agreed to the deploy order?
> - What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
> - What is the acceptable write-stall window for this table?
> - What is the accepted risk for MISSING_ROLLBACK?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 6,
 "phase2_statements": 3,
 "human_gates": 6
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "holdout_08_release_train_fleet",
 "attempt": 1,
 "phase1_statements": 6
}
```

</details>

**tool** `migration.parse` (0.25 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"drivers\" ADD COLUMN \"phone_e164\" TEXT;\nUPDATE \"drivers\" SET \"phone_e164\" = \"phone\" WHERE \"phone_e164\" IS NULL AND \"id\" IN (SELECT \"id\" FROM \"drivers\" WHERE \"phone_e164\" IS NULL LIMIT 5000);\nCREATE INDEX CONCURRENTLY \"idx_geofence_events_shipment\" ON \"geofence_events\" (\"shipment_id\");\nUPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed' AND \"id\" IN (SELECT \"id\" FROM \"sh..."
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "drivers",
  "column": "phone_e164",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE \"drivers\" ADD COLUMN \"phone_e164\" TEXT",
  "index": 0
 },
 {
  "kind": "dml_update",
  "table": "drivers",
  "column": null,
  "detail": {
   "where": true,
   "batched": true
  },
  "sql": "UPDATE \"drivers\" SET \"phone_e164\" = \"phone\" WHERE \"phone_e164\" IS NULL AND \"id\" IN (SELECT \"id\" FROM \"drivers\" WHERE \"ph...",
  "index": 1
 },
 {
  "kind": "create_index",
  "table": "geofence_events",
  "column": null,
  "detail": {
   "name": "idx_geofence_events_shipment",
   "unique": false,
   "concurrently": true,
   "columns": [
    "shipment_id"
   ]
  },
  "sql": "CREATE INDEX CONCURRENTLY \"idx_geofence_events_shipment\" ON \"geofence_events\" (\"shipment_id\")",
  "index": 2
 },
 {
  "kind": "dml_update",
  "table": "shipment_stops",
  "column": null,
  "detail": {
   "where": true,
   "batched": true
  },
  "sql": "UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed' AND \"id\" IN (SELECT \"id\" FROM \"shipment_stops\" WHER...",
  "index": 3
 },
 {
  "kind": "add_constraint",
  "table": "carrier_invoices",
  "column": null,
  "detail": {
   "constraint": "carrier_invoices_shipment_fk",
   "constraint_kind": "foreign_key",
   "expr": "(shipment_id) REFERENCES shipments (id)",
   "columns": [],
   "not_valid": true
  },
  "sql": "ALTER TABLE \"carrier_invoices\" ADD CONSTRAINT \"carrier_invoices_shipment_fk\" FOREIGN KEY (shipment_id) REFERENCES shipme...",
  "index": 4
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
    "kind": "add_column",
    "table": "drivers",
    "column": "phone_e164",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"drivers\" ADD COLUMN \"phone_e164\" TEXT",
    "index": 0
   },
   {
    "kind": "dml_update",
    "table": "drivers",
    "column": null,
    "detail": {
     "where": true,
     "batched": true
    },
    "sql": "UPDATE \"drivers\" SET \"phone_e164\" = \"phone\" WHERE \"phone_e164\" IS NULL AND \"id\" IN (SELECT \"id\" FROM \"drivers\" WHERE \"ph...",
    "index": 1
   },
   {
    "kind": "create_index",
    "table": "geofence_events",
    "column": null,
    "detail": {
     "name": "idx_geofence_events_shipment",
     "unique": false,
     "concurrently": true,
     "columns": [
      "shipment_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_geofence_events_shipment\" ON \"geofence_events\" (\"shipment_id\")",
    "index": 2
   },
   {
    "kind": "dml_update",
    "table": "shipment_stops",
    "column": null,
    "detail": {
     "where": true,
     "batched": true
    },
    "sql": "UPDATE shipment_s
```

_tool responded_

```json
[
 "Schema",
 []
]
```

**tool** `shadow.replay` (3.4 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "drivers",
    "column": "phone_e164",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"drivers\" ADD COLUMN \"phone_e164\" TEXT",
    "index": 0
   },
   {
    "kind": "dml_update",
    "table": "drivers",
    "column": null,
    "detail": {
     "where": true,
     "batched": true
    },
    "sql": "UPDATE \"drivers\" SET \"phone_e164\" = \"phone\" WHERE \"phone_e164\" IS NULL AND \"id\" IN (SELECT \"id\" FROM \"drivers\" WHERE \"ph...",
    "index": 1
   },
   {
    "kind": "create_index",
    "table": "geofence_events",
    "column": null,
    "detail": {
     "name": "idx_geofence_events_shipment",
     "unique": false,
     "concurrently": true,
     "columns": [
      "shipment_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_geofence_events_shipment\" ON \"geofence_events\" (\"shipment_id\")",
    "index": 2
   },
   {
    "kind": "dml_update",
    "table": "shipment_stops",
    "column": null,
    "detail": {
     "where": true,
     "batched": true
    }
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
    "phone_e164"
   ],
   "removed": [],
   "added": [
    "phone_e164"
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
    "phone_e164"
   ],
   "removed": [],
   "added": [
    "phone_e164"
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
     "phone_e164"
    ],
    "removed": [],
    "added": [
     "phone_e164"
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
     "phone_e164"
    ],
    "removed": [],
    "added": [
     "phone_e164"
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

**model** `scripted-v1` tag=`executive_summary` tokens=38/78 cost=$0.0

> Do not ship this as written. 3 coverage gap(s) need a named sign-off before this can be called safe. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 7 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
