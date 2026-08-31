# Trajectory - rt2_01_comment_marker_inside_literal

- run id: `eval-rt2_01_comment_marker_inside_literal`
- case: `rt2_01_comment_marker_inside_literal`
- events: 34

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_01_comment_marker_inside_literal",
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

**tool** `schema.parse` (0.84 ms)

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

**tool** `migration.parse` (0.07 ms)

```json
{
 "args": {
  "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL;\nALTER TABLE invoices DROP COLUMN tax_rate;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "dml_update",
  "table": "invoices",
  "column": null,
  "detail": {
   "where": true,
   "batched": false
  },
  "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL",
  "index": 0
 },
 {
  "kind": "drop_column",
  "table": "invoices",
  "column": "tax_rate",
  "detail": {},
  "sql": "ALTER TABLE invoices DROP COLUMN tax_rate",
  "index": 1
 }
]
```

**tool** `migration.audit` (0.08 ms)

```json
{
 "args": {
  "migration_sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL;\nALTER TABLE invoices DROP COLUMN tax_rate;\n",
  "ops": [
   {
    "kind": "dml_update",
    "table": "invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": false
    },
    "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL",
    "index": 0
   },
   {
    "kind": "drop_column",
    "table": "invoices",
    "column": "tax_rate",
    "detail": {},
    "sql": "ALTER TABLE invoices DROP COLUMN tax_rate",
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
  "significant_chars": 101,
  "attributed_chars": 101,
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
    "kind": "dml_update",
    "table": "invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": false
    },
    "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL",
    "index": 0
   },
   {
    "kind": "drop_column",
    "table": "invoices",
    "column": "tax_rate",
    "detail": {},
    "sql": "ALTER TABLE invoices DROP COLUMN tax_rate",
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
  "dml_update",
  "drop_column"
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
 "case": "rt2_01_comment_marker_inside_literal",
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

**tool** `corpus.dependents` (0.23 ms)

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

**tool** `corpus.blast_score` (0.03 ms)

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
    "cr
```

_tool responded_

```json
25
```

**tool** `shadow.replay` (3.58 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "dml_update",
    "table": "invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": false
    },
    "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL",
    "index": 0
   },
   {
    "kind": "drop_column",
    "table": "invoices",
    "column": "tax_rate",
    "detail": {},
    "sql": "ALTER TABLE invoices DROP COLUMN tax_rate",
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
     "plan": "team",
     "mrr_cents": 9900,
     "signed_up_at": "2024-03-11"
    },
    {
     "id": 3,
     "email": "alan@lab.example",
     "full_name": "Alan Turing",
     "company_name": null,
     "country_code": "GB",
     "plan": "free",
     "mrr_cents": 0,
     "
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [],
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
 "rowcount_drift": [],
 "data_loss": [],
 "queries_run": 19,
 "queries_ok_before": 19,
 "queries_ok_after": 18
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
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 19,
  "queries_ok_before": 19,
  "queries_ok_after": 18
 },
 "hazards_found": [
  "BREAKING_QUERY"
 ]
}
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_01_comment_marker_inside_literal",
 "row_estimates": {
  "customers": 2400000,
  "subscriptions": 2600000,
  "invoices": 48000000,
  "invoice_lines": 190000000,
  "usage_events": 900000000
 },
 "inherited_hazards": [
  "BREAKING_QUERY"
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

**tool** `memory.escalation` (0.01 ms)

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

**tool** `coverage.ledger` (0.22 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "dml_update",
    "table": "invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": false
    },
    "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL",
    "index": 0
   },
   {
    "kind": "drop_column",
    "table": "invoices",
    "column": "tax_rate",
    "detail": {},
    "sql": "ALTER TABLE invoices DROP COLUMN tax_rate",
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
    "id": "q_bi_summ
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "in_place_data_mutation",
   "object": "invoices.currency",
   "object_inferred": false,
   "statement_index": 0,
   "statement": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL",
   "why": "rows that already exist in invoices are rewritten; replay proves the corpus still executes, never that it still returns ...",
   "closes_with": "a reviewer confirms which consumers of invoices.currency depend on the current values",
   "irreversible": false
  }
 ],
 "gap_kinds": [
  "in_place_data_mutation"
 ],
 "irreversible": [],
 "corpus_statements": 17,
 "parser_notes": []
}
```

**model** `scripted-v1` tag=`hazard_narrative` tokens=451/73 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1` -> OperationalError: no such column: tax_rate Owning service(s): billing-api.

**model** `scripted-v1` tag=`hazard_narrative` tokens=430/60 cost=$0.0

> Impact lands on a service owned by another team. The fix needs a deploy the migration author does not control, so ordering must be agreed first. Evidence: corpus ownership of failing statements: ['billing-api'] Owning service(s): billing-api.

**model** `scripted-v1` tag=`hazard_narrative` tokens=431/58 cost=$0.0

> Destructive change shipped in a single step. Dropping or renaming in one deploy means old and new application code cannot both work. Evidence: statement 1: `ALTER TABLE invoices DROP COLUMN tax_rate` Previously bit us in INC-2023-09.

**model** `scripted-v1` tag=`hazard_narrative` tokens=432/56 cost=$0.0

> Backfill runs as one unbounded statement. One long transaction holds locks and bloats WAL; it cannot be paused or resumed. Evidence: statement 0: `UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL`

**result**

```json
{
 "verdict": "BLOCK",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 3,
  "blocker": 1
 },
 "coverage_gaps": [
  "in_place_data_mutation:invoices.currency"
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
   "code": "UNBATCHED_BACKFILL",
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
 "case": "rt2_01_comment_marker_inside_literal",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "BREAKING_QUERY",
  "CROSS_SERVICE_UNCOORDINATED",
  "DESTRUCTIVE_NO_EXPAND_CONTRACT",
  "UNBATCHED_BACKFILL"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=498/60 cost=$0.0

> - Which deploy lands first: the query change or the schema change?
> - Has the owning team agreed to the deploy order?
> - What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
> - What batch size and pause has this table tolerated before?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 2,
 "phase2_statements": 1,
 "human_gates": 2
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_01_comment_marker_inside_literal",
 "attempt": 1,
 "phase1_statements": 2
}
```

</details>

**tool** `migration.parse` (0.08 ms)

```json
{
 "args": {
  "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE currency IS NULL LIMIT 5000);"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "dml_update",
  "table": "invoices",
  "column": null,
  "detail": {
   "where": true,
   "batched": true
  },
  "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL AND \"id\" IN (SELECT \"id\" FROM \"invoices\" W...",
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
    "kind": "dml_update",
    "table": "invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": true
    },
    "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL AND \"id\" IN (SELECT \"id\" FROM \"invoices\" W...",
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

**tool** `shadow.replay` (2.98 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "dml_update",
    "table": "invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": true
    },
    "sql": "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL AND \"id\" IN (SELECT \"id\" FROM \"invoices\" W...",
    "index": 0
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
     "plan": "team",
     "mrr_cents": 9900,
     "signed_up_at": "2024-03-11"
    },
    {
     "id": 3,
     "email": "alan@lab.example",
     "full_name": "Alan Turing",
     "company_name": null,
     "country_code": "GB",
     "plan": "free",
     "mrr_cents": 0,
     "signed_up_at": "2025-06-02"
    },
    {
     "id": 4,
     "email": "katherine@nasa.example",
     "full_name": "Katherine Joh
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

**tool** `plan.audit` (3.55 ms)

```json
{
 "args": {
  "plan": {
   "attempt": 1,
   "phase1_sql": [
    "-- repeat until zero rows are affected (batch size 5000):",
    "UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL AND \"id\" IN (SELECT \"id\" FROM \"invoices\" W..."
   ],
   "phase2_sql": [
    "ALTER TABLE \"invoices\" DROP COLUMN \"tax_rate\";"
   ],
   "rollback_sql": [],
   "code_steps": [
    "remove every read and write of invoices.tax_rate, then wait one full deploy cycle"
   ],
   "human_gates": [
    "confirm invoices.tax_rate has had zero reads for the agreed observation window before phase 2",
    "coverage gap on `invoices.currency` (in_place_data_mutation): a reviewer confirms which consumers of invoices.currency d..."
   ],
   "questions": [
    "Which deploy lands first: the query change or the schema change?",
    "Has the owning team agreed to the deploy order?",
    "What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?",
    "What batch size and pause has this table tolerated before?"
   ],
   "questions_source": "model",
   "questions_dropped": [],
   "policy": {
    "include_view_changes": true,
    "expand_contract_type_change": true,
    "minimal_phase1": 
```

_tool responded_

```json
{
 "statements_audited": 2,
 "scripts": {
  "phase1": 1,
  "phase2": 1,
  "rollback": 0
 },
 "findings": [],
 "finding_codes": [],
 "gaps": [
  {
   "kind": "audit_gate_text_only",
   "object": "invoices.tax_rate",
   "object_inferred": false,
   "script": "phase2",
   "statement_index": 0,
   "statement": "ALTER TABLE \"invoices\" DROP COLUMN \"tax_rate\"",
   "why": "this step is treated as gated because a human gate names `invoices.tax_rate`; this audit read the name, not the question",
   "closes_with": "a reviewer confirms the gate on this object actually asks about this statement",
   "irreversible": false
  }
 ],
 "gap_kinds": [
  "audit_gate_text_only"
 ],
 "kind_inventory": [
  {
   "script": "phase1",
   "statement_index": 0,
   "kind": "dml_update",
   "bucket": "RULED"
  },
  {
   "script": "phase2",
   "statement_index": 0,
   "kind": "drop_column",
   "bucket": "RULED"
  }
 ],
 "gates_trusted": 1,
 "replay": {
  "ran": true,
  "scripts": {
   "phase2": {
    "queries_run": 19,
    "broken_after": 1,
    "broken_query_ids": [
     "q_billing_tax"
    ]
   }
  },
  "note": "the generated phase 2 is expected to break today's statements - that is what the code steps are for. The number is publi..."
 },
 "clean": true
}
```

**model** `scripted-v1` tag=`executive_summary` tokens=38/78 cost=$0.0

> Do not ship this as written. 1 coverage gap(s) need a named sign-off before this can be called safe. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 3 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
