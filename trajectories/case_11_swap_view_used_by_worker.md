# Trajectory - case_11_swap_view_used_by_worker

- run id: `eval-case_11_swap_view_used_by_worker`
- case: `case_11_swap_view_used_by_worker`
- events: 31

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "case_11_swap_view_used_by_worker",
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

**tool** `schema.parse` (0.67 ms)

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

**tool** `migration.parse` (0.06 ms)

```json
{
 "args": {
  "sql": "DROP VIEW open_invoices;\nCREATE VIEW open_invoices_v2 AS\n  SELECT id, customer_id, invoice_number, amount_cents, status, issued_at\n  FROM invoices WHERE status IN ('draft','open');\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "drop_view",
  "table": null,
  "column": null,
  "detail": {
   "name": "open_invoices"
  },
  "sql": "DROP VIEW open_invoices",
  "index": 0
 },
 {
  "kind": "create_view",
  "table": null,
  "column": null,
  "detail": {
   "name": "open_invoices_v2",
   "select": "SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open')",
   "replace": false
  },
  "sql": "CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WH...",
  "index": 1
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
    "kind": "drop_view",
    "table": null,
    "column": null,
    "detail": {
     "name": "open_invoices"
    },
    "sql": "DROP VIEW open_invoices",
    "index": 0
   },
   {
    "kind": "create_view",
    "table": null,
    "column": null,
    "detail": {
     "name": "open_invoices_v2",
     "select": "SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open')",
     "replace": false
    },
    "sql": "CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WH...",
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
  "create_view",
  "drop_view"
 ],
 "tables_touched": [],
 "unmodelled": []
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "case_11_swap_view_used_by_worker",
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

**tool** `corpus.dependents` (0.15 ms)

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
  "query_id": "q_dunning_open",
  "service": "dunning-worker",
  "criticality": "critical",
  "matched": [
   "open_invoices"
  ],
  "uses_select_star": true,
  "label": "open invoice sweep"
 }
]
```

**tool** `corpus.blast_score` (0.01 ms)

```json
{
 "args": {
  "hits": [
   {
    "query_id": "q_dunning_open",
    "service": "dunning-worker",
    "criticality": "critical",
    "matched": [
     "open_invoices"
    ],
    "uses_select_star": true,
    "label": "open invoice sweep"
   }
  ]
 }
}
```

_tool responded_

```json
4
```

**tool** `shadow.replay` (3.69 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "drop_view",
    "table": null,
    "column": null,
    "detail": {
     "name": "open_invoices"
    },
    "sql": "DROP VIEW open_invoices",
    "index": 0
   },
   {
    "kind": "create_view",
    "table": null,
    "column": null,
    "detail": {
     "name": "open_invoices_v2",
     "select": "SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open')",
     "replace": false
    },
    "sql": "CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WH...",
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
   
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [],
 "broken": [
  {
   "query_id": "q_dunning_open",
   "service": "dunning-worker",
   "criticality": "critical",
   "label": "open invoice sweep",
   "error": "OperationalError: no such table: open_invoices",
   "sql": "SELECT * FROM open_invoices"
  },
  {
   "query_id": "__view__open_invoices",
   "service": "database",
   "criticality": "high",
   "label": "view open_invoices",
   "error": "object removed by migration (view or table no longer exists)",
   "sql": "SELECT * FROM \"open_invoices\" LIMIT 1"
  }
 ],
 "column_drift": [],
 "rowcount_drift": [],
 "data_loss": [],
 "queries_run": 16,
 "queries_ok_before": 16,
 "queries_ok_after": 15
}
```

_note (blast_radius)_: view open_invoices breakage folded into the corpus statement that reads it

**result**

```json
{
 "dependent_queries": 1,
 "blast_score": 4,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [],
  "broken": [
   {
    "query_id": "q_dunning_open",
    "service": "dunning-worker",
    "criticality": "critical",
    "label": "open invoice sweep",
    "error": "OperationalError: no such table: open_invoices",
    "sql": "SELECT * FROM open_invoices"
   },
   {
    "query_id": "__view__open_invoices",
    "service": "database",
    "criticality": "high",
    "label": "view open_invoices",
    "error": "object removed by migration (view or table no longer exists)",
    "sql": "SELECT * FROM \"open_invoices\" LIMIT 1"
   }
  ],
  "column_drift": [],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 16,
  "queries_ok_before": 16,
  "queries_ok_after": 15
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
 "case": "case_11_swap_view_used_by_worker",
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
  "table": "q_dunning_open"
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

**tool** `coverage.ledger` (0.21 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "drop_view",
    "table": null,
    "column": null,
    "detail": {
     "name": "open_invoices"
    },
    "sql": "DROP VIEW open_invoices",
    "index": 0
   },
   {
    "kind": "create_view",
    "table": null,
    "column": null,
    "detail": {
     "name": "open_invoices_v2",
     "select": "SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open')",
     "replace": false
    },
    "sql": "CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WH...",
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
    "service": "support-admin
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

**model** `scripted-v1` tag=`hazard_narrative` tokens=443/64 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `SELECT * FROM open_invoices` -> OperationalError: no such table: open_invoices Owning service(s): dunning-worker.

**model** `scripted-v1` tag=`hazard_narrative` tokens=433/62 cost=$0.0

> Impact lands on a service owned by another team. The fix needs a deploy the migration author does not control, so ordering must be agreed first. Evidence: corpus ownership of failing statements: ['dunning-worker'] Owning service(s): dunning-worker.

**model** `scripted-v1` tag=`hazard_narrative` tokens=406/30 cost=$0.0

> No rollback path supplied. Recovery at 3am should not require improvising DDL. Evidence: case field `rollback_sql` is empty

**result**

```json
{
 "verdict": "BLOCK",
 "counts": {
  "low": 0,
  "medium": 1,
  "high": 1,
  "blocker": 1
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
   "code": "CROSS_SERVICE_UNCOORDINATED",
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
 "case": "case_11_swap_view_used_by_worker",
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
  "MISSING_ROLLBACK"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=489/41 cost=$0.0

> - Which deploy lands first: the query change or the schema change?
> - Has the owning team agreed to the deploy order?
> - What is the accepted risk for MISSING_ROLLBACK?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 1,
 "phase2_statements": 1,
 "human_gates": 2
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "case_11_swap_view_used_by_worker",
 "attempt": 1,
 "phase1_statements": 1
}
```

</details>

**tool** `migration.parse` (0.06 ms)

```json
{
 "args": {
  "sql": "CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open');"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "create_view",
  "table": null,
  "column": null,
  "detail": {
   "name": "open_invoices_v2",
   "select": "SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open')",
   "replace": false
  },
  "sql": "CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WH...",
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
    "kind": "create_view",
    "table": null,
    "column": null,
    "detail": {
     "name": "open_invoices_v2",
     "select": "SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open')",
     "replace": false
    },
    "sql": "CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WH...",
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

**tool** `shadow.replay` (3.15 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "create_view",
    "table": null,
    "column": null,
    "detail": {
     "name": "open_invoices_v2",
     "select": "SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open')",
     "replace": false
    },
    "sql": "CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WH...",
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
     "mrr_cent
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
 "queries_ok_before": 16,
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
  "queries_ok_before": 16,
  "queries_ok_after": 17
 },
 "unmodelled": []
}
```

**model** `scripted-v1` tag=`executive_summary` tokens=38/60 cost=$0.0

> Do not ship this as written. 2 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 1 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
