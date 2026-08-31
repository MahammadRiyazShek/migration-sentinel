# Trajectory - rt2_06_ordinary_migration_with_quotes

- run id: `eval-rt2_06_ordinary_migration_with_quotes`
- case: `rt2_06_ordinary_migration_with_quotes`
- events: 25

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_06_ordinary_migration_with_quotes",
 "migration_statements": 2,
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

**tool** `schema.parse` (0.83 ms)

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

**tool** `migration.parse` (0.09 ms)

```json
{
 "args": {
  "sql": "-- dunning copy for the retry email, PLAT-4471\nALTER TABLE invoices ADD COLUMN dunning_note TEXT DEFAULT 'not attempted -- see runbook';\nCREATE INDEX CONCURRENTLY idx_invoices_dunning_note ON invoices (dunning_note);\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "invoices",
  "column": "dunning_note",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": "'not attempted -- see runbook'",
   "unique": false
  },
  "sql": "ALTER TABLE invoices ADD COLUMN dunning_note TEXT DEFAULT 'not attempted -- see runbook'",
  "index": 0
 },
 {
  "kind": "create_index",
  "table": "invoices",
  "column": null,
  "detail": {
   "name": "idx_invoices_dunning_note",
   "unique": false,
   "concurrently": true,
   "columns": [
    "dunning_note"
   ]
  },
  "sql": "CREATE INDEX CONCURRENTLY idx_invoices_dunning_note ON invoices (dunning_note)",
  "index": 1
 }
]
```

**tool** `migration.audit` (0.1 ms)

```json
{
 "args": {
  "migration_sql": "-- dunning copy for the retry email, PLAT-4471\nALTER TABLE invoices ADD COLUMN dunning_note TEXT DEFAULT 'not attempted -- see runbook';\nCREATE INDEX CONCURRENTLY idx_invoices_dunning_note ON invoices (dunning_note);\n",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_note",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "'not attempted -- see runbook'",
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN dunning_note TEXT DEFAULT 'not attempted -- see runbook'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_dunning_note",
     "unique": false,
     "concurrently": true,
     "columns": [
      "dunning_note"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY idx_invoices_dunning_note ON invoices (dunning_note)",
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
  "significant_chars": 187,
  "attributed_chars": 187,
  "unattributed_chars": 0
 },
 "clean": true
}
```

**tool** `schema.apply_ops` (0.06 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_note",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "'not attempted -- see runbook'",
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN dunning_note TEXT DEFAULT 'not attempted -- see runbook'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_dunning_note",
     "unique": false,
     "concurrently": true,
     "columns": [
      "dunning_note"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY idx_invoices_dunning_note ON invoices (dunning_note)",
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
  "invoices"
 ],
 "unmodelled": []
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_06_ordinary_migration_with_quotes",
 "corpus_size": 17,
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

**tool** `corpus.dependents` (0.14 ms)

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
   "invoices"
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
  "query_id": "q_billing_status_update",
  "service": "billing-api",
  "criticality": "high",
  "matched": [
   "invoices"
  ],
  "uses_select_star": false,
  "label": "mark invoice open"
 },
 {
  "query_id": "q_billing_customer_invoices",
  "service": "billing-api",
  "criticality": "critical",
  "matched": [
   "invoices"
  ],
  "uses_select_star": false,
  "label": "customer invoice list"
 },
 {
  "query_id": "q_support_open_for_customer",
  "service": "support-admin",
  "criticality": "high",
  "matched": [
   "invoices"
  ],
  "uses_select_star": false,
  "label": "open invoices for a customer"
 },
 {
  "query_id": "q_bi_revenue_by_customer",
  "service": "bi",
  "criticality": "medium",
  "matched": [
   "invoices"
  ],
  "uses_select_star": false,
  "label": "revenue per customer"
 }
]
```

**tool** `corpus.blast_score` (0.05 ms)

```json
{
 "args": {
  "hits": [
   {
    "query_id": "q_billing_invoice_create",
    "service": "billing-api",
    "criticality": "critical",
    "matched": [
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
     "invoices"
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
    "query_id": "q_billing_status_update",
    "service": "billing-api",
    "criticality": "high",
    "matched": [
     "invoices"
    ],
    "uses_select_star": false,
    "label": "mark invoice open"
   },
   {
    "query_id": "q_billing_customer_invoices",
    "service": "billing-api",
    "criticality": "crit
```

_tool responded_

```json
25
```

**tool** `shadow.replay` (3.03 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_note",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "'not attempted -- see runbook'",
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN dunning_note TEXT DEFAULT 'not attempted -- see runbook'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_dunning_note",
     "unique": false,
     "concurrently": true,
     "columns": [
      "dunning_note"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY idx_invoices_dunning_note ON invoices (dunning_note)",
    "index": 1
   }
  ],
  "seed": {
   "customers": [
    {
     "id": 1,
     "email": "ada@corp.example",
     "full_name": "Ada Lovelace",
     "company_name": "Corp",
     "country_code": "US",
     "plan": "business",
     "mrr_cents": 49900,
     "signed_up_at": "2024-01-04"
    },
    {
     "id": 2,
     "email": "grace@corp.example",
     "full_name": "Grace Hopper",
     "company_name": "Corp",
     "country_code": "USA",
     "
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
 "queries_run": 19,
 "queries_ok_before": 19,
 "queries_ok_after": 19
}
```

**result**

```json
{
 "dependent_queries": 8,
 "blast_score": 25,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [],
  "broken": [],
  "column_drift": [],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 19,
  "queries_ok_before": 19,
  "queries_ok_after": 19
 },
 "hazards_found": []
}
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_06_ordinary_migration_with_quotes",
 "row_estimates": {
  "customers": 2400000,
  "subscriptions": 2600000,
  "invoices": 48000000,
  "invoice_lines": 190000000,
  "usage_events": 900000000
 },
 "inherited_hazards": []
}
```

</details>

**tool** `coverage.ledger` (0.15 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_note",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "'not attempted -- see runbook'",
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN dunning_note TEXT DEFAULT 'not attempted -- see runbook'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_dunning_note",
     "unique": false,
     "concurrently": true,
     "columns": [
      "dunning_note"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY idx_invoices_dunning_note ON invoices (dunning_note)",
    "index": 1
   }
  ],
  "schema": "Schema",
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
    "sql": "INSERT INTO customers (email, full_name, signed_up_at) VALUES ('new@corp.example','New Person','2026-02-
```

_tool responded_

```json
{
 "gaps": [],
 "gap_kinds": [],
 "irreversible": [],
 "corpus_statements": 17,
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
 "case": "rt2_06_ordinary_migration_with_quotes",
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
 "case": "rt2_06_ordinary_migration_with_quotes",
 "attempt": 1,
 "phase1_statements": 2
}
```

</details>

**tool** `migration.parse` (0.09 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"dunning_note\" TEXT DEFAULT 'not attempted -- see runbook';\nCREATE INDEX CONCURRENTLY \"idx_invoices_dunning_note\" ON \"invoices\" (\"dunning_note\");"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "invoices",
  "column": "dunning_note",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": "'not attempted -- see runbook'",
   "unique": false
  },
  "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"dunning_note\" TEXT DEFAULT 'not attempted -- see runbook'",
  "index": 0
 },
 {
  "kind": "create_index",
  "table": "invoices",
  "column": null,
  "detail": {
   "name": "idx_invoices_dunning_note",
   "unique": false,
   "concurrently": true,
   "columns": [
    "dunning_note"
   ]
  },
  "sql": "CREATE INDEX CONCURRENTLY \"idx_invoices_dunning_note\" ON \"invoices\" (\"dunning_note\")",
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
    "table": "invoices",
    "column": "dunning_note",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "'not attempted -- see runbook'",
     "unique": false
    },
    "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"dunning_note\" TEXT DEFAULT 'not attempted -- see runbook'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_dunning_note",
     "unique": false,
     "concurrently": true,
     "columns": [
      "dunning_note"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_invoices_dunning_note\" ON \"invoices\" (\"dunning_note\")",
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

**tool** `shadow.replay` (2.97 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_note",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "'not attempted -- see runbook'",
     "unique": false
    },
    "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"dunning_note\" TEXT DEFAULT 'not attempted -- see runbook'",
    "index": 0
   },
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_dunning_note",
     "unique": false,
     "concurrently": true,
     "columns": [
      "dunning_note"
     ]
    },
    "sql": "CREATE INDEX CONCURRENTLY \"idx_invoices_dunning_note\" ON \"invoices\" (\"dunning_note\")",
    "index": 1
   }
  ],
  "seed": {
   "customers": [
    {
     "id": 1,
     "email": "ada@corp.example",
     "full_name": "Ada Lovelace",
     "company_name": "Corp",
     "country_code": "US",
     "plan": "business",
     "mrr_cents": 49900,
     "signed_up_at": "2024-01-04"
    },
    {
     "id": 2,
     "email": "grace@corp.example",
     "full_name": "Grace Hopper",
     "company_name": "Corp",
     "country_
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
 "queries_run": 19,
 "queries_ok_before": 19,
 "queries_ok_after": 19
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
  "queries_run": 19,
  "queries_ok_before": 19,
  "queries_ok_after": 19
 },
 "unmodelled": []
}
```

**model** `scripted-v1` tag=`executive_summary` tokens=38/34 cost=$0.0

> No blocking hazards found. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
