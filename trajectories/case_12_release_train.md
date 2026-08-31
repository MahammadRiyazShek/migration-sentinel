# Trajectory - case_12_release_train

- run id: `eval-case_12_release_train`
- case: `case_12_release_train`
- events: 44

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "case_12_release_train",
 "migration_statements": 7,
 "tables_declared": [
  "customers",
  "subscriptions",
  "invoices",
  "invoice_lines",
  "usage_events"
 ]
}
```

</details>

**tool** `schema.parse` (0.65 ms)

```json
{
 "args": {
  "sql": "CREATE TABLE customers (\n  id SERIAL PRIMARY KEY,\n  email TEXT NOT NULL,\n  full_name TEXT,\n  company_name TEXT,\n  country_code TEXT NOT NULL DEFAULT 'US',\n  plan TEXT NOT NULL DEFAULT 'free',\n  mrr_cents INTEGER NOT NULL DEFAULT 0,\n  signed_up_at TIMESTAMPTZ NOT NULL,\n  CONSTRAINT customers_plan_chk CHECK (plan IN ('free','team','business','enterprise'))\n);\n\nCREATE TABLE subscriptions (\n  id SERIA...",
  "row_estimates": {
   "customers": 2400000,
   "subscriptions": 2600000,
   "invoices": 48000000,
   "invoice_lines": 190000000,
   "usage_events": 900000000
  }
 }
}
```

_tool responded_

```json
"Schema"
```

**tool** `migration.parse` (0.17 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE subscriptions ADD COLUMN billing_interval TEXT NOT NULL DEFAULT 'monthly';\nCREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id);\nALTER TABLE invoices DROP COLUMN tax_rate;\nCREATE INDEX idx_usage_events_name ON usage_events (event_name);\nALTER TABLE subscriptions DROP CONSTRAINT subscriptions_seats_chk;\nUPDATE invoices SET status = 'open' WHERE status = 'draft';..."
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "subscriptions",
  "column": "billing_interval",
  "detail": {
   "type": "TEXT",
   "not_null": true,
   "default": "'monthly'",
   "unique": false
  },
  "sql": "ALTER TABLE subscriptions ADD COLUMN billing_interval TEXT NOT NULL DEFAULT 'monthly'",
  "index": 0
 },
 {
  "kind": "create_index",
  "table": "subscriptions",
  "column": null,
  "detail": {
   "name": "idx_subscriptions_customer",
   "unique": true,
   "concurrently": false,
   "columns": [
    "customer_id"
   ]
  },
  "sql": "CREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id)",
  "index": 1
 },
 {
  "kind": "drop_column",
  "table": "invoices",
  "column": "tax_rate",
  "detail": {},
  "sql": "ALTER TABLE invoices DROP COLUMN tax_rate",
  "index": 2
 },
 {
  "kind": "create_index",
  "table": "usage_events",
  "column": null,
  "detail": {
   "name": "idx_usage_events_name",
   "unique": false,
   "concurrently": false,
   "columns": [
    "event_name"
   ]
  },
  "sql": "CREATE INDEX idx_usage_events_name ON usage_events (event_name)",
  "index": 3
 },
 {
  "kind": "drop_constraint",
  "table": "subscriptions",
  "column": null,
  "detail": {
   "constraint": "subscriptions_seats_chk"
  },
  "sql": "ALTER TABLE subscriptions DROP CONSTRAINT subscriptions_seats_chk",
  "index": 4
 },
 {
  "kind": "dml_update",
  "table": "invoices",
  "column": null,
  "detail": {
   "where": true,
   "batched": false
  },
  "sql": "UPDATE invoices SET status = 'open' WHERE status = 'draft'",
  "index": 5
 },
 {
  "kind": "maintenance_rewrite",
  "table": "invoices",
  "column": null,
  "detail": {
   "command": "CLUSTER"
  },
  "sql": "CLUSTER invoices USING idx_invoices_customer",
  "index": 6
 }
]
```

**tool** `migration.audit` (0.15 ms)

```json
{
 "args": {
  "migration_sql": "ALTER TABLE subscriptions ADD COLUMN billing_interval TEXT NOT NULL DEFAULT 'monthly';\nCREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id);\nALTER TABLE invoices DROP COLUMN tax_rate;\nCREATE INDEX idx_usage_events_name ON usage_events (event_name);\nALTER TABLE subscriptions DROP CONSTRAINT subscriptions_seats_chk;\nUPDATE invoices SET status = 'open' WHERE status = 'draft';...",
  "ops": [
   {
    "kind": "add_column",
    "table": "subscriptions",
    "column": "billing_interval",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": "'monthly'",
     "unique": false
    },
    "sql": "ALTER TABLE subscriptions ADD COLUMN billing_interval TEXT NOT NULL DEFAULT 'monthly'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "subscriptions",
    "column": null,
    "detail": {
     "name": "idx_subscriptions_customer",
     "unique": true,
     "concurrently": false,
     "columns": [
      "customer_id"
     ]
    },
    "sql": "CREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id)",
    "index": 1
   },
   {
    "kind": "drop_column",
    "table": "invoices",
```

_tool responded_

```json
{
 "lexed_statements": 7,
 "ops": 7,
 "unterminated": [],
 "unaccounted": [],
 "procedural": [],
 "conservation": {
  "significant_chars": 390,
  "attributed_chars": 390,
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
    "table": "subscriptions",
    "column": "billing_interval",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": "'monthly'",
     "unique": false
    },
    "sql": "ALTER TABLE subscriptions ADD COLUMN billing_interval TEXT NOT NULL DEFAULT 'monthly'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "subscriptions",
    "column": null,
    "detail": {
     "name": "idx_subscriptions_customer",
     "unique": true,
     "concurrently": false,
     "columns": [
      "customer_id"
     ]
    },
    "sql": "CREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id)",
    "index": 1
   },
   {
    "kind": "drop_column",
    "table": "invoices",
    "column": "tax_rate",
    "detail": {},
    "sql": "ALTER TABLE invoices DROP COLUMN tax_rate",
    "index": 2
   },
   {
    "kind": "create_index",
    "table": "usage_events",
    "column": null,
    "detail": {
     "name": "idx_usage_events_name",
     "unique": false,
     "concurrently": false,
     "columns": [
      "event_name"
     ]
    },
    "sql": "CREATE INDEX idx_usage_events_name ON 
```

_tool responded_

```json
[
 "Schema",
 [
  "op 6 (maintenance_rewrite) not modelled structurally: CLUSTER invoices USING idx_invoices_customer"
 ]
]
```

_note (cartographer)_: Some statements could not be modelled structurally; they are passed to the risk officer as unknowns rather than silently assumed safe.

**result**

```json
{
 "op_kinds": [
  "add_column",
  "create_index",
  "dml_update",
  "drop_column",
  "drop_constraint",
  "maintenance_rewrite"
 ],
 "tables_touched": [
  "invoices",
  "subscriptions",
  "usage_events"
 ],
 "unmodelled": [
  "op 6 (maintenance_rewrite) not modelled structurally: CLUSTER invoices USING idx_invoices_customer"
 ]
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "case_12_release_train",
 "corpus_size": 14,
 "services": [
  "bi",
  "billing-api",
  "dunning-worker",
  "mobile-api",
  "support-admin",
  "web"
 ]
}
```

</details>

**tool** `corpus.dependents` (0.18 ms)

```json
{
 "args": {
  "queries": [
   {
    "id": "q_web_profile",
    "service": "web",
    "criticality": "critical",
    "label": "customer profile page",
    "sql": "SELECT id, email, full_name, plan FROM customers WHERE id = 1"
   },
   {
    "id": "q_web_signup",
    "service": "web",
    "criticality": "critical",
    "label": "signup insert",
    "sql": "INSERT INTO customers (email, full_name, signed_up_at) VALUES ('new@corp.example','New Person','2026-02-01')"
   },
   {
    "id": "q_support_lookup",
    "service": "support-admin",
    "criticality": "high",
    "label": "support customer lookup",
    "sql": "SELECT id, email, company_name FROM customers WHERE email = 'ada@corp.example'"
   },
   {
    "id": "q_bi_summary",
    "service": "bi",
    "criticality": "high",
    "label": "dbt model stg_customers",
    "sql": "SELECT * FROM customer_billing_summary"
   },
   {
    "id": "q_bi_mrr",
    "service": "bi",
    "criticality": "medium",
    "label": "MRR by plan",
    "sql": "SELECT plan, SUM(mrr_cents) AS mrr FROM customers GROUP BY plan"
   },
   {
    "id": "q_bi_country",
    "service": "bi",
    "criticality": "low",
    "label": "customers by country",
    "sql": "SE
```

_tool responded_

```json
[
 {
  "query_id": "q_billing_invoice_create",
  "service": "billing-api",
  "criticality": "critical",
  "matched": [
   "customer_id",
   "invoices"
  ],
  "uses_select_star": false,
  "label": "invoice creation"
 },
 {
  "query_id": "q_billing_tax",
  "service": "billing-api",
  "criticality": "high",
  "matched": [
   "invoices",
   "tax_rate"
  ],
  "uses_select_star": false,
  "label": "invoice tax display"
 },
 {
  "query_id": "q_billing_currency",
  "service": "billing-api",
  "criticality": "medium",
  "matched": [
   "invoices"
  ],
  "uses_select_star": false,
  "label": "currency rollup"
 },
 {
  "query_id": "q_dunning_open",
  "service": "dunning-worker",
  "criticality": "critical",
  "matched": [
   "open_invoices"
  ],
  "uses_select_star": true,
  "label": "open invoice sweep"
 },
 {
  "query_id": "q_mobile_seats",
  "service": "mobile-api",
  "criticality": "high",
  "matched": [
   "customer_id",
   "subscriptions"
  ],
  "uses_select_star": false,
  "label": "seat count for the app"
 },
 {
  "query_id": "q_analytics_usage",
  "service": "bi",
  "criticality": "medium",
  "matched": [
   "event_name",
   "usage_events"
  ],
  "uses_select_star": false,
  "label": "usage rollup"
 },
 {
  "query_id": "q_billing_status_update",
  "service": "billing-api",
  "criticality": "high",
  "matched": [
   "invoices"
  ],
  "uses_select_star": false,
  "label": "mark invoice open"
 }
]
```

**tool** `corpus.blast_score` (0.02 ms)

```json
{
 "args": {
  "hits": [
   {
    "query_id": "q_billing_invoice_create",
    "service": "billing-api",
    "criticality": "critical",
    "matched": [
     "customer_id",
     "invoices"
    ],
    "uses_select_star": false,
    "label": "invoice creation"
   },
   {
    "query_id": "q_billing_tax",
    "service": "billing-api",
    "criticality": "high",
    "matched": [
     "invoices",
     "tax_rate"
    ],
    "uses_select_star": false,
    "label": "invoice tax display"
   },
   {
    "query_id": "q_billing_currency",
    "service": "billing-api",
    "criticality": "medium",
    "matched": [
     "invoices"
    ],
    "uses_select_star": false,
    "label": "currency rollup"
   },
   {
    "query_id": "q_dunning_open",
    "service": "dunning-worker",
    "criticality": "critical",
    "matched": [
     "open_invoices"
    ],
    "uses_select_star": true,
    "label": "open invoice sweep"
   },
   {
    "query_id": "q_mobile_seats",
    "service": "mobile-api",
    "criticality": "high",
    "matched": [
     "customer_id",
     "subscriptions"
    ],
    "uses_select_star": false,
    "label": "seat count for the app"
   },
   {
    "query_id": "q_analytics_usage",
    "se
```

_tool responded_

```json
21
```

**tool** `shadow.replay` (2.09 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "subscriptions",
    "column": "billing_interval",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": "'monthly'",
     "unique": false
    },
    "sql": "ALTER TABLE subscriptions ADD COLUMN billing_interval TEXT NOT NULL DEFAULT 'monthly'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "subscriptions",
    "column": null,
    "detail": {
     "name": "idx_subscriptions_customer",
     "unique": true,
     "concurrently": false,
     "columns": [
      "customer_id"
     ]
    },
    "sql": "CREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id)",
    "index": 1
   },
   {
    "kind": "drop_column",
    "table": "invoices",
    "column": "tax_rate",
    "detail": {},
    "sql": "ALTER TABLE invoices DROP COLUMN tax_rate",
    "index": 2
   },
   {
    "kind": "create_index",
    "table": "usage_events",
    "column": null,
    "detail": {
     "name": "idx_usage_events_name",
     "unique": false,
     "concurrently": false,
     "columns": [
      "event_name"
     ]
    },
    "sql": "CREATE 
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [
  "backfill subscriptions: UNIQUE constraint failed: subscriptions.customer_id (row={'id': 2, 'customer_id': 1, 'status': '..."
 ],
 "broken": [
  {
   "query_id": "q_billing_tax",
   "service": "billing-api",
   "criticality": "high",
   "label": "invoice tax display",
   "error": "OperationalError: no such column: tax_rate",
   "sql": "SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1"
  }
 ],
 "column_drift": [],
 "rowcount_drift": [
  {
   "query_id": "q_mobile_seats",
   "service": "mobile-api",
   "before_rows": 2,
   "after_rows": 1,
   "sql": "SELECT id, seats, status FROM subscriptions WHERE customer_id = 1"
  }
 ],
 "data_loss": [],
 "queries_run": 16,
 "queries_ok_before": 16,
 "queries_ok_after": 15
}
```

**result**

```json
{
 "dependent_queries": 7,
 "blast_score": 21,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [
   "backfill subscriptions: UNIQUE constraint failed: subscriptions.customer_id (row={'id': 2, 'customer_id': 1, 'status': 'canceled', 'seats': 3, 'price_cents': 9900, 'started_on': '2023-02-01', 'canceled_on': '2024-01-03'})"
  ],
  "broken": [
   {
    "query_id": "q_billing_tax",
    "service": "billing-api",
    "criticality": "high",
    "label": "invoice tax display",
    "error": "OperationalError: no such column: tax_rate",
    "sql": "SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1"
   }
  ],
  "column_drift": [],
  "rowcount_drift": [
   {
    "query_id": "q_mobile_seats",
    "service": "mobile-api",
    "before_rows": 2,
    "after_rows": 1,
    "sql": "SELECT id, seats, status FROM subscriptions WHERE customer_id = 1"
   }
  ],
  "data_loss": [],
  "queries_run": 16,
  "queries_ok_before": 16,
  "queries_ok_after": 15
 },
 "hazards_found": [
  "BREAKING_QUERY",
  "UNIQUE_VIOLATION_EXISTING_DATA"
 ]
}
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "case_12_release_train",
 "row_estimates": {
  "customers": 2400000,
  "subscriptions": 2600000,
  "invoices": 48000000,
  "invoice_lines": 190000000,
  "usage_events": 900000000
 },
 "inherited_hazards": [
  "BREAKING_QUERY",
  "UNIQUE_VIOLATION_EXISTING_DATA"
 ]
}
```

</details>

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "BREAKING_QUERY",
  "table": "q_billing_tax"
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
  "table": "usage_events"
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
  "hazard_code": "UNIQUE_VIOLATION_EXISTING_DATA",
  "table": "subscriptions"
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

**tool** `memory.escalation` (0.0 ms)

```json
{
 "args": {
  "hazard_code": "DESTRUCTIVE_NO_EXPAND_CONTRACT",
  "table": "invoices"
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
  "hazard_code": "INDEX_LOCK_NO_CONCURRENT",
  "table": "subscriptions"
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
  "hazard_code": "INTEGRITY_CONSTRAINT_REMOVED",
  "table": "subscriptions"
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
  "hazard_code": "TABLE_REWRITE_LOCK",
  "table": "invoices"
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
  "table": "invoices"
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

**tool** `coverage.ledger` (0.15 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "add_column",
    "table": "subscriptions",
    "column": "billing_interval",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": "'monthly'",
     "unique": false
    },
    "sql": "ALTER TABLE subscriptions ADD COLUMN billing_interval TEXT NOT NULL DEFAULT 'monthly'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "subscriptions",
    "column": null,
    "detail": {
     "name": "idx_subscriptions_customer",
     "unique": true,
     "concurrently": false,
     "columns": [
      "customer_id"
     ]
    },
    "sql": "CREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id)",
    "index": 1
   },
   {
    "kind": "drop_column",
    "table": "invoices",
    "column": "tax_rate",
    "detail": {},
    "sql": "ALTER TABLE invoices DROP COLUMN tax_rate",
    "index": 2
   },
   {
    "kind": "create_index",
    "table": "usage_events",
    "column": null,
    "detail": {
     "name": "idx_usage_events_name",
     "unique": false,
     "concurrently": false,
     "columns": [
      "event_name"
     ]
    },
    "sql": "CREATE INDEX idx_usage_events_name ON usage_events (event_na
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "in_place_data_mutation",
   "object": "invoices.status",
   "object_inferred": false,
   "statement_index": 5,
   "statement": "UPDATE invoices SET status = 'open' WHERE status = 'draft'",
   "why": "rows that already exist in invoices are rewritten; replay proves the corpus still executes, never that it still returns ...",
   "closes_with": "a reviewer confirms which consumers of invoices.status depend on the current values",
   "irreversible": false
  },
  {
   "kind": "unmodelled_statement",
   "object": "invoices",
   "object_inferred": false,
   "statement_index": 6,
   "statement": "CLUSTER invoices USING idx_invoices_customer",
   "why": "the parser produced no structural model for this statement, so no post-migration schema and no replay covers it",
   "closes_with": "a reviewer confirms by hand what statement 6 does to invoices and to anything reading it",
   "irreversible": false
  }
 ],
 "gap_kinds": [
  "in_place_data_mutation",
  "unmodelled_statement"
 ],
 "irreversible": [],
 "corpus_statements": 14,
 "parser_notes": [
  "op 6 (maintenance_rewrite) not modelled structurally: CLUSTER invoices USING idx_invoices_customer"
 ]
}
```

**model** `scripted-v1` tag=`hazard_narrative` tokens=451/73 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1` -> OperationalError: no such column: tax_rate Owning service(s): billing-api.

**model** `scripted-v1` tag=`hazard_narrative` tokens=462/63 cost=$0.0

> Index built without CONCURRENTLY on a large table. Writes queue behind the build; at this row count that is a user-visible stall. Evidence: statement 3: `CREATE INDEX idx_usage_events_name ON usage_events (event_name)` Previously bit us in INC-2024-07.

**model** `scripted-v1` tag=`hazard_narrative` tokens=482/96 cost=$0.0

> Uniqueness conflicts with data already in the table. The index build fails partway through, leaving the deploy half-applied. Evidence: shadow backfill: backfill subscriptions: UNIQUE constraint failed: subscriptions.customer_id (row={'id': 2, 'customer_id': 1, 'status': 'canceled', 'seats': 3, 'price_cents': 9900, 'started_on': '2023-02-01', 'cancele Previously bit us in INC-2025-04.

**model** `scripted-v1` tag=`hazard_narrative` tokens=431/58 cost=$0.0

> Destructive change shipped in a single step. Dropping or renaming in one deploy means old and new application code cannot both work. Evidence: statement 2: `ALTER TABLE invoices DROP COLUMN tax_rate` Previously bit us in INC-2023-09.

**model** `scripted-v1` tag=`hazard_narrative` tokens=464/66 cost=$0.0

> Index built without CONCURRENTLY on a large table. Writes queue behind the build; at this row count that is a user-visible stall. Evidence: statement 1: `CREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id)` Previously bit us in INC-2024-07.

**model** `scripted-v1` tag=`hazard_narrative` tokens=454/54 cost=$0.0

> Data-integrity constraint removed. Nothing breaks today; invalid rows start accumulating and are expensive to clean up later. Evidence: statement 4: `ALTER TABLE subscriptions DROP CONSTRAINT subscriptions_seats_chk`

**model** `scripted-v1` tag=`hazard_narrative` tokens=478/48 cost=$0.0

> Type change forces a full table rewrite. An ACCESS EXCLUSIVE lock for the length of the rewrite is downtime by another name. Evidence: statement 6: `CLUSTER invoices USING idx_invoices_customer`

**model** `scripted-v1` tag=`hazard_narrative` tokens=428/51 cost=$0.0

> Backfill runs as one unbounded statement. One long transaction holds locks and bloats WAL; it cannot be paused or resumed. Evidence: statement 5: `UPDATE invoices SET status = 'open' WHERE status = 'draft'`

**model** `scripted-v1` tag=`hazard_narrative` tokens=406/30 cost=$0.0

> No rollback path supplied. Recovery at 3am should not require improvising DDL. Evidence: case field `rollback_sql` is empty

**result**

```json
{
 "verdict": "BLOCK",
 "counts": {
  "low": 0,
  "medium": 1,
  "high": 5,
  "blocker": 3
 },
 "coverage_gaps": [
  "in_place_data_mutation:invoices.status",
  "unmodelled_statement:invoices"
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
   "code": "UNIQUE_VIOLATION_EXISTING_DATA",
   "severity": "blocker",
   "source": "replay",
   "memory": [
    "INC-2025-04"
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
   "code": "INDEX_LOCK_NO_CONCURRENT",
   "severity": "high",
   "source": "static",
   "memory": [
    "INC-2024-07"
   ]
  },
  {
   "code": "INTEGRITY_CONSTRAINT_REMOVED",
   "severity": "high",
   "source": "static",
   "memory": []
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
 "case": "case_12_release_train",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "BREAKING_QUERY",
  "DESTRUCTIVE_NO_EXPAND_CONTRACT",
  "INDEX_LOCK_NO_CONCURRENT",
  "INTEGRITY_CONSTRAINT_REMOVED",
  "MISSING_ROLLBACK",
  "TABLE_REWRITE_LOCK",
  "UNBATCHED_BACKFILL",
  "UNIQUE_VIOLATION_EXISTING_DATA"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=524/88 cost=$0.0

> - Which deploy lands first: the query change or the schema change?
> - What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
> - What is the acceptable write-stall window for this table?
> - What enforces this invariant once the constraint is gone?
> - What is the accepted risk for MISSING_ROLLBACK?
> - What is the accepted risk for TABLE_REWRITE_LOCK?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 5,
 "phase2_statements": 4,
 "human_gates": 6
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "case_12_release_train",
 "attempt": 1,
 "phase1_statements": 5
}
```

</details>

**tool** `migration.parse` (0.19 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"subscriptions\" ADD COLUMN \"billing_interval\" TEXT DEFAULT 'monthly';\nCREATE INDEX CONCURRENTLY \"idx_subscriptions_customer_tmp_nonunique\" ON \"subscriptions\" (\"customer_id\");\nCREATE INDEX CONCURRENTLY \"idx_usage_events_name\" ON \"usage_events\" (\"event_name\");\nUPDATE invoices SET status = 'open' WHERE status = 'draft' AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE status = 'draft' LIMIT ..."
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "subscriptions",
  "column": "billing_interval",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": "'monthly'",
   "unique": false
  },
  "sql": "ALTER TABLE \"subscriptions\" ADD COLUMN \"billing_interval\" TEXT DEFAULT 'monthly'",
  "index": 0
 },
 {
  "kind": "create_index",
  "table": "subscriptions",
  "column": null,
  "detail": {
   "name": "idx_subscriptions_customer_tmp_nonunique",
   "unique": false,
   "concurrently": true,
   "columns": [
    "customer_id"
   ]
  },
  "sql": "CREATE INDEX CONCURRENTLY \"idx_subscriptions_customer_tmp_nonunique\" ON \"subscriptions\" (\"customer_id\")",
  "index": 1
 },
 {
  "kind": "create_index",
  "table": "usage_events",
  "column": null,
  "detail": {
   "name": "idx_usage_events_name",
   "unique": false,
   "concurrently": true,
   "columns": [
    "event_name"
   ]
  },
  "sql": "CREATE INDEX CONCURRENTLY \"idx_usage_events_name\" ON \"usage_events\" (\"event_name\")",
  "index": 2
 },
 {
  "kind": "dml_update",
  "table": "invoices",
  "column": null,
  "detail": {
   "where": true,
   "batched": true
  },
  "sql": "UPDATE invoices SET status = 'open' WHERE status = 'draft' AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE status = 'draf...",
  "index": 3
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
    "kind": "add_column",
    "table": "subscriptions",
    "column": "billing_interval",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "'monthly'",
     "unique": false
    },
    "sql": "ALTER TABLE \"subscriptions\" ADD COLUMN \"billing_interval\" TEXT DEFAULT 'monthly'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "subscriptions",
    "column": null,
    "detail": {
     "name": "idx_subscriptions_customer_tmp_nonunique",
     "unique": false,
     "concurrently": true,
     "columns": [
      "customer_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_subscriptions_customer_tmp_nonunique\" ON \"subscriptions\" (\"customer_id\")",
    "index": 1
   },
   {
    "kind": "create_index",
    "table": "usage_events",
    "column": null,
    "detail": {
     "name": "idx_usage_events_name",
     "unique": false,
     "concurrently": true,
     "columns": [
      "event_name"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_usage_events_name\" ON \"usage_events\" (\"event_name\")",
    "index": 2
   },
   {
    "kind": "dml_update",
    "table": "invoices",
   
```

_tool responded_

```json
[
 "Schema",
 []
]
```

**tool** `shadow.replay` (2.14 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "subscriptions",
    "column": "billing_interval",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "'monthly'",
     "unique": false
    },
    "sql": "ALTER TABLE \"subscriptions\" ADD COLUMN \"billing_interval\" TEXT DEFAULT 'monthly'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "subscriptions",
    "column": null,
    "detail": {
     "name": "idx_subscriptions_customer_tmp_nonunique",
     "unique": false,
     "concurrently": true,
     "columns": [
      "customer_id"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_subscriptions_customer_tmp_nonunique\" ON \"subscriptions\" (\"customer_id\")",
    "index": 1
   },
   {
    "kind": "create_index",
    "table": "usage_events",
    "column": null,
    "detail": {
     "name": "idx_usage_events_name",
     "unique": false,
     "concurrently": true,
     "columns": [
      "event_name"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_usage_events_name\" ON \"usage_events\" (\"event_name\")",
    "index": 2
   },
   {
    "kind": "dml_update
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
 "queries_run": 16,
 "queries_ok_before": 16,
 "queries_ok_after": 16
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
  "queries_run": 16,
  "queries_ok_before": 16,
  "queries_ok_after": 16
 },
 "unmodelled": []
}
```

**model** `scripted-v1` tag=`executive_summary` tokens=38/78 cost=$0.0

> Do not ship this as written. 2 coverage gap(s) need a named sign-off before this can be called safe. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 3 blocker, 5 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
