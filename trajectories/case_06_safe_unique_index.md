# Trajectory - case_06_safe_unique_index

- run id: `eval-case_06_safe_unique_index`
- case: `case_06_safe_unique_index`
- events: 26

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "case_06_safe_unique_index",
 "migration_statements": 1,
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

**tool** `schema.parse` (0.79 ms)

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

**tool** `migration.parse` (0.04 ms)

```json
{
 "args": {
  "sql": "CREATE UNIQUE INDEX CONCURRENTLY idx_invoices_number ON invoices (invoice_number);\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "create_index",
  "table": "invoices",
  "column": null,
  "detail": {
   "name": "idx_invoices_number",
   "unique": true,
   "concurrently": true,
   "columns": [
    "invoice_number"
   ]
  },
  "sql": "CREATE UNIQUE INDEX CONCURRENTLY idx_invoices_number ON invoices (invoice_number)",
  "index": 0
 }
]
```

**tool** `migration.audit` (0.05 ms)

```json
{
 "args": {
  "migration_sql": "CREATE UNIQUE INDEX CONCURRENTLY idx_invoices_number ON invoices (invoice_number);\n",
  "ops": [
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_number",
     "unique": true,
     "concurrently": true,
     "columns": [
      "invoice_number"
     ]
    },
    "sql": "CREATE UNIQUE INDEX CONCURRENTLY idx_invoices_number ON invoices (invoice_number)",
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
  "significant_chars": 74,
  "attributed_chars": 74,
  "unattributed_chars": 0
 },
 "clean": true
}
```

**tool** `schema.apply_ops` (0.05 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_number",
     "unique": true,
     "concurrently": true,
     "columns": [
      "invoice_number"
     ]
    },
    "sql": "CREATE UNIQUE INDEX CONCURRENTLY idx_invoices_number ON invoices (invoice_number)",
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
 "case": "case_06_safe_unique_index",
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

**tool** `corpus.dependents` (0.16 ms)

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
   "invoice_number",
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
   "invoice_number",
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
     "invoice_number",
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
     "invoice_number",
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
   }
  ]
 }
}
```

_tool responded_

```json
16
```

**tool** `shadow.replay` (2.72 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_number",
     "unique": true,
     "concurrently": true,
     "columns": [
      "invoice_number"
     ]
    },
    "sql": "CREATE UNIQUE INDEX CONCURRENTLY idx_invoices_number ON invoices (invoice_number)",
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
     "email": "katherine@na
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
 "dependent_queries": 5,
 "blast_score": 16,
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
 "hazards_found": []
}
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "case_06_safe_unique_index",
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

**tool** `coverage.ledger` (0.2 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_number",
     "unique": true,
     "concurrently": true,
     "columns": [
      "invoice_number"
     ]
    },
    "sql": "CREATE UNIQUE INDEX CONCURRENTLY idx_invoices_number ON invoices (invoice_number)",
    "index": 0
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
    "id": "q_bi_summary",
    "service": "bi",
    "criticality": "high",
    "label": "dbt model stg_
```

_tool responded_

```json
{
 "gaps": [],
 "gap_kinds": [],
 "irreversible": [],
 "corpus_statements": 14,
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
 "case": "case_06_safe_unique_index",
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
 "phase1_statements": 1,
 "phase2_statements": 0,
 "human_gates": 0
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "case_06_safe_unique_index",
 "attempt": 1,
 "phase1_statements": 1
}
```

</details>

**tool** `migration.parse` (0.05 ms)

```json
{
 "args": {
  "sql": "CREATE UNIQUE INDEX CONCURRENTLY \"idx_invoices_number\" ON \"invoices\" (\"invoice_number\");"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "create_index",
  "table": "invoices",
  "column": null,
  "detail": {
   "name": "idx_invoices_number",
   "unique": true,
   "concurrently": true,
   "columns": [
    "invoice_number"
   ]
  },
  "sql": "CREATE UNIQUE INDEX CONCURRENTLY \"idx_invoices_number\" ON \"invoices\" (\"invoice_number\")",
  "index": 0
 }
]
```

**tool** `schema.apply_ops` (0.05 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_number",
     "unique": true,
     "concurrently": true,
     "columns": [
      "invoice_number"
     ]
    },
    "sql": "CREATE UNIQUE INDEX CONCURRENTLY \"idx_invoices_number\" ON \"invoices\" (\"invoice_number\")",
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

**tool** `shadow.replay` (2.58 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "create_index",
    "table": "invoices",
    "column": null,
    "detail": {
     "name": "idx_invoices_number",
     "unique": true,
     "concurrently": true,
     "columns": [
      "invoice_number"
     ]
    },
    "sql": "CREATE UNIQUE INDEX CONCURRENTLY \"idx_invoices_number\" ON \"invoices\" (\"invoice_number\")",
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
     "email": "
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

**tool** `plan.audit` (2.89 ms)

```json
{
 "args": {
  "plan": {
   "attempt": 1,
   "phase1_sql": [
    "CREATE UNIQUE INDEX CONCURRENTLY \"idx_invoices_number\" ON \"invoices\" (\"invoice_number\");"
   ],
   "phase2_sql": [],
   "rollback_sql": [
    "DROP INDEX CONCURRENTLY \"idx_invoices_number\";"
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
    "sql": "SELECT id, email, company_name F
```

_tool responded_

```json
{
 "statements_audited": 2,
 "scripts": {
  "phase1": 1,
  "phase2": 0,
  "rollback": 1
 },
 "findings": [],
 "finding_codes": [],
 "gaps": [],
 "gap_kinds": [],
 "kind_inventory": [
  {
   "script": "phase1",
   "statement_index": 0,
   "kind": "create_index",
   "bucket": "RULED"
  },
  {
   "script": "rollback",
   "statement_index": 0,
   "kind": "drop_index",
   "bucket": "RULED"
  }
 ],
 "gates_trusted": 0,
 "replay": {
  "ran": true,
  "scripts": {
   "rollback": {
    "queries_run": 16,
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
