# Trajectory - p2_add_col_volatile_default

- run id: `run-3b461ff0`
- case: `p2_add_col_volatile_default`
- events: 51

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "p2_add_col_volatile_default",
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

**tool** `schema.parse` (2.16 ms)

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

**tool** `migration.parse` (0.86 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE invoices ADD COLUMN public_token TEXT NOT NULL DEFAULT gen_random_uuid()::text;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "invoices",
  "column": "public_token",
  "detail": {
   "type": "TEXT",
   "not_null": true,
   "default": "gen_random_uuid()::text",
   "unique": false
  },
  "sql": "ALTER TABLE invoices ADD COLUMN public_token TEXT NOT NULL DEFAULT gen_random_uuid()::text",
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
    "kind": "add_column",
    "table": "invoices",
    "column": "public_token",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": "gen_random_uuid()::text",
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN public_token TEXT NOT NULL DEFAULT gen_random_uuid()::text",
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
 "case": "p2_add_col_volatile_default",
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
   }
  ]
 }
}
```

_tool responded_

```json
16
```

**tool** `shadow.replay` (3.21 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "public_token",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": "gen_random_uuid()::text",
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN public_token TEXT NOT NULL DEFAULT gen_random_uuid()::text",
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
     "email": "katherine@nasa.exam
```

_tool responded_

```json
{
 "materialised": false,
 "schema_errors": [
  "OperationalError: near \"(\": syntax error while running: CREATE TABLE \"invoices\" (",
  "OperationalError: no such table: main.invoices while running: CREATE INDEX \"idx_invoices_customer\" ON \"invoices\" (\"custo..."
 ],
 "data_errors": [
  "backfill invoices: no such table: invoices (row={'id': 1, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV...",
  "backfill invoices: no such table: invoices (row={'id': 2, 'customer_id': 4, 'subscription_id': 3, 'invoice_number': 'INV...",
  "backfill invoices: no such table: invoices (row={'id': 3, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV..."
 ],
 "broken": [
  {
   "query_id": "q_billing_invoice_create",
   "service": "billing-api",
   "criticality": "critical",
   "label": "invoice creation",
   "error": "OperationalError: no such table: invoices",
   "sql": "INSERT INTO invoices (customer_id, invoice_number, amount_cents, issued_at) VALUES (1,'INV-9001',1000,'2026-02-01')"
  },
  {
   "query_id": "q_billing_tax",
   "service": "billing-api",
   "criticality": "high",
   "label": "invoice tax display",
   "error": "OperationalError: no such table: invoices",
   "sql": "SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1"
  },
  {
   "query_id": "q_billing_currency",
   "service": "billing-api",
   "criticality": "medium",
   "label": "currency rollup",
   "error": "OperationalError: no such table: invoices",
   "sql": "SELECT currency, COUNT(*) AS n FROM invoices GROUP BY currency"
  },
  {
   "query_id": "q_dunning_open",
   "service": "dunning-worker",
   "criticality": "critical",
   "label": "open invoice sweep",
   "error": "OperationalError: no such table: main.invoices",
   "sql": "SELECT * FROM open_invoices"
  },
  {
   "query_id": "q_billing_status_update",
   "service": "billing-api",
   "criticality": "high",
   "label": "mark invoice open",
   "error": "OperationalError: no such table: invoices",
   "sql
```

_note (blast_radius)_: view open_invoices breakage folded into the corpus statement that reads it

**result**

```json
{
 "dependent_queries": 5,
 "blast_score": 16,
 "replay": {
  "materialised": false,
  "schema_errors": [
   "OperationalError: near \"(\": syntax error while running: CREATE TABLE \"invoices\" (",
   "OperationalError: no such table: main.invoices while running: CREATE INDEX \"idx_invoices_customer\" ON \"invoices\" (\"customer_id\")"
  ],
  "data_errors": [
   "backfill invoices: no such table: invoices (row={'id': 1, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV-1001', 'amount_cents': 49900, 'tax_rate': 0.2, 'currency': 'usd', 'status': 'open', 'issued_at': '2026-01-01', 'paid_at': None})",
   "backfill invoices: no such table: invoices (row={'id': 2, 'customer_id': 4, 'subscription_id': 3, 'invoice_number': 'INV-1002', 'amount_cents': 249900, 'tax_rate': 0.0, 'currency': 'usd', 'status': 'paid', 'issued_at': '2026-01-01', 'paid_at': '2026-01-05'})",
   "backfill invoices: no such table: invoices (row={'id': 3, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV-1003', 'amount_cents': 1200, 'tax_rate': None, 'currency': 'eur', 'status': 'draft', 'issued_at': None, 'paid_at': None})"
  ],
  "broken": [
   {
    "query_id": "q_billing_invoice_create",
    "service": "billing-api",
    "criticality": "critical",
    "label": "invoice creation",
    "error": "OperationalError: no such table: invoices",
    "sql": "INSERT INTO invoices (customer_id, invoice_number, amount_cents, issued_at) VALUES (1,'INV-9001',1000,'2026-02-01')"
   },
   {
    "query_id": "q_billing_tax",
    "service": "billing-api",
    "criticality": "high",
    "label": "invoice tax display",
    "error": "OperationalError: no such table: invoices",
    "sql": "SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1"
   },
   {
    "query_id": "q_billing_currency",
    "service": "billing-api",
    "criticality": "medium",
    "label": "currency rollup",
    "error": "OperationalError: no such table: invoices",
    "sql": "SELECT currency, COUNT(*) AS 
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "p2_add_col_volatile_default",
 "row_estimates": {
  "customers": 2400000,
  "subscriptions": 2600000,
  "invoices": 48000000,
  "invoice_lines": 190000000,
  "usage_events": 900000000
 },
 "inherited_hazards": [
  "BREAKING_QUERY",
  "BREAKING_QUERY",
  "BREAKING_QUERY",
  "BREAKING_QUERY",
  "BREAKING_QUERY",
  "BREAKING_QUERY",
  "BREAKING_QUERY",
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
  "table": "q_billing_invoice_create"
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
  "hazard_code": "BREAKING_QUERY",
  "table": "q_billing_currency"
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
  "hazard_code": "BREAKING_QUERY",
  "table": "q_billing_status_update"
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
  "hazard_code": "BREAKING_QUERY",
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

**tool** `coverage.ledger` (0.14 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "public_token",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": "gen_random_uuid()::text",
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN public_token TEXT NOT NULL DEFAULT gen_random_uuid()::text",
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
    "label": "dbt model stg_custome
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

**model** `scripted-v1` tag=`hazard_narrative` tokens=466/84 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `INSERT INTO invoices (customer_id, invoice_number, amount_cents, issued_at) VALUES (1,'INV-9001',1000,'2026-02-01')` -> OperationalError: no such table: invoices Owning service(s): billing-api.

**model** `scripted-v1` tag=`hazard_narrative` tokens=450/73 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1` -> OperationalError: no such table: invoices Owning service(s): billing-api.

**model** `scripted-v1` tag=`hazard_narrative` tokens=450/70 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `SELECT currency, COUNT(*) AS n FROM invoices GROUP BY currency` -> OperationalError: no such table: invoices Owning service(s): billing-api.

**model** `scripted-v1` tag=`hazard_narrative` tokens=443/64 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `SELECT * FROM open_invoices` -> OperationalError: no such table: main.invoices Owning service(s): dunning-worker.

**model** `scripted-v1` tag=`hazard_narrative` tokens=449/67 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `UPDATE invoices SET status = 'open' WHERE id = 1` -> OperationalError: no such table: invoices Owning service(s): billing-api.

**model** `scripted-v1` tag=`hazard_narrative` tokens=621/91 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: backfill invoices: no such table: invoices (row={'id': 1, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV-1001', 'amount_cents': 49900, 'tax_rate': 0.2, 'currency': 'usd', 'status': 'open', 'issued_at': '2026-01-01', 'paid_at

**model** `scripted-v1` tag=`hazard_narrative` tokens=433/62 cost=$0.0

> Impact lands on a service owned by another team. The fix needs a deploy the migration author does not control, so ordering must be agreed first. Evidence: corpus ownership of failing statements: ['dunning-worker'] Owning service(s): dunning-worker.

**result**

```json
{
 "verdict": "BLOCK",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 1,
  "blocker": 6
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
   "code": "BREAKING_QUERY",
   "severity": "blocker",
   "source": "replay",
   "memory": []
  },
  {
   "code": "BREAKING_QUERY",
   "severity": "blocker",
   "source": "replay",
   "memory": []
  },
  {
   "code": "BREAKING_QUERY",
   "severity": "blocker",
   "source": "replay",
   "memory": []
  },
  {
   "code": "BREAKING_QUERY",
   "severity": "blocker",
   "source": "replay",
   "memory": []
  },
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
  }
 ]
}
```

## Agent: rollout_engineer

**Goal** Rewrite the migration as a phase-1 (expand, safe now) / phase-2 (contract, after the code deploy) plan with a rollback, and surface every step that needs a human decision.

<details><summary>inputs</summary>

```json
{
 "case": "p2_add_col_volatile_default",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": true,
  "notes": [
   "fell back to a minimal additive phase 1: everything not provably backwards compatible moved to phase 2"
  ]
 },
 "hazard_codes": [
  "BREAKING_QUERY",
  "CROSS_SERVICE_UNCOORDINATED"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=484/29 cost=$0.0

> - Which deploy lands first: the query change or the schema change?
> - Has the owning team agreed to the deploy order?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 1,
 "phase2_statements": 1,
 "human_gates": 0
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "p2_add_col_volatile_default",
 "attempt": 1,
 "phase1_statements": 1
}
```

</details>

**tool** `migration.parse` (0.09 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"public_token\" TEXT DEFAULT gen_random_uuid()::text;"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "invoices",
  "column": "public_token",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": "gen_random_uuid()::text",
   "unique": false
  },
  "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"public_token\" TEXT DEFAULT gen_random_uuid()::text",
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
    "table": "invoices",
    "column": "public_token",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "gen_random_uuid()::text",
     "unique": false
    },
    "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"public_token\" TEXT DEFAULT gen_random_uuid()::text",
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

**tool** `shadow.replay` (2.71 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "public_token",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "gen_random_uuid()::text",
     "unique": false
    },
    "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"public_token\" TEXT DEFAULT gen_random_uuid()::text",
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
     "email": "katherine@nasa.exam
```

_tool responded_

```json
{
 "materialised": false,
 "schema_errors": [
  "OperationalError: near \"(\": syntax error while running: CREATE TABLE \"invoices\" (",
  "OperationalError: no such table: main.invoices while running: CREATE INDEX \"idx_invoices_customer\" ON \"invoices\" (\"custo..."
 ],
 "data_errors": [
  "backfill invoices: no such table: invoices (row={'id': 1, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV...",
  "backfill invoices: no such table: invoices (row={'id': 2, 'customer_id': 4, 'subscription_id': 3, 'invoice_number': 'INV...",
  "backfill invoices: no such table: invoices (row={'id': 3, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV..."
 ],
 "broken": [
  {
   "query_id": "q_billing_invoice_create",
   "service": "billing-api",
   "criticality": "critical",
   "label": "invoice creation",
   "error": "OperationalError: no such table: invoices",
   "sql": "INSERT INTO invoices (customer_id, invoice_number, amount_cents, issued_at) VALUES (1,'INV-9001',1000,'2026-02-01')"
  },
  {
   "query_id": "q_billing_tax",
   "service": "billing-api",
   "criticality": "high",
   "label": "invoice tax display",
   "error": "OperationalError: no such table: invoices",
   "sql": "SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1"
  },
  {
   "query_id": "q_billing_currency",
   "service": "billing-api",
   "criticality": "medium",
   "label": "currency rollup",
   "error": "OperationalError: no such table: invoices",
   "sql": "SELECT currency, COUNT(*) AS n FROM invoices GROUP BY currency"
  },
  {
   "query_id": "q_dunning_open",
   "service": "dunning-worker",
   "criticality": "critical",
   "label": "open invoice sweep",
   "error": "OperationalError: no such table: main.invoices",
   "sql": "SELECT * FROM open_invoices"
  },
  {
   "query_id": "q_billing_status_update",
   "service": "billing-api",
   "criticality": "high",
   "label": "mark invoice open",
   "error": "OperationalError: no such table: invoices",
   "sql
```

**result**

```json
{
 "verified": false,
 "problems": [
  "q_billing_invoice_create (billing-api): OperationalError: no such table: invoices",
  "q_billing_tax (billing-api): OperationalError: no such table: invoices",
  "q_billing_currency (billing-api): OperationalError: no such table: invoices",
  "q_dunning_open (dunning-worker): OperationalError: no such table: main.invoices",
  "q_billing_status_update (billing-api): OperationalError: no such table: invoices",
  "__view__open_invoices (database): OperationalError: no such table: main.invoices",
  "phase-1 data step failed: backfill invoices: no such table: invoices (row={'id': 1, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV-1001', 'amount_cents': 49900, 'tax_rate': 0.2, 'currency': 'usd', 'status': 'open', 'issued_at': '2026-01-01', 'paid_at': None})",
  "phase-1 data step failed: backfill invoices: no such table: invoices (row={'id': 2, 'customer_id': 4, 'subscription_id': 3, 'invoice_number': 'INV-1002', 'amount_cents': 249900, 'tax_rate': 0.0, 'currency': 'usd', 'status': 'paid', 'issued_at': '2026-01-01', 'paid_at': '2026-01-05'})",
  "phase-1 data step failed: backfill invoices: no such table: invoices (row={'id': 3, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV-1003', 'amount_cents': 1200, 'tax_rate': None, 'currency': 'eur', 'status': 'draft', 'issued_at': None, 'paid_at': None})"
 ],
 "replay": {
  "materialised": false,
  "schema_errors": [
   "OperationalError: near \"(\": syntax error while running: CREATE TABLE \"invoices\" (",
   "OperationalError: no such table: main.invoices while running: CREATE INDEX \"idx_invoices_customer\" ON \"invoices\" (\"customer_id\")"
  ],
  "data_errors": [
   "backfill invoices: no such table: invoices (row={'id': 1, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV-1001', 'amount_cents': 49900, 'tax_rate': 0.2, 'currency': 'usd', 'status': 'open', 'issued_at': '2026-01-01', 'paid_at': None})",
   "backfill invoices: no such table: invoi
```

**feedback into next step (attempt 1)** phase 1 is not safe yet: q_billing_invoice_create (billing-api): OperationalError: no such table: invoices; q_billing_tax (billing-api): OperationalError: no such table: invoices; q_billing_currency (billing-api): OperationalError: no such table: invoices. Tightening the policy and regenerating.

**RETRY 2** because: q_billing_invoice_create (billing-api): OperationalError: no such table: invoices; q_billing_tax (billing-api): OperationalError: no such table: invoices; q_billing_currency (billing-api): OperationalError: no such table: invoices

## Agent: rollout_engineer

**Goal** Rewrite the migration as a phase-1 (expand, safe now) / phase-2 (contract, after the code deploy) plan with a rollback, and surface every step that needs a human decision.

<details><summary>inputs</summary>

```json
{
 "case": "p2_add_col_volatile_default",
 "attempt": 2,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": true,
  "notes": [
   "fell back to a minimal additive phase 1: everything not provably backwards compatible moved to phase 2"
  ]
 },
 "hazard_codes": [
  "BREAKING_QUERY",
  "CROSS_SERVICE_UNCOORDINATED"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=484/29 cost=$0.0

> - Which deploy lands first: the query change or the schema change?
> - Has the owning team agreed to the deploy order?

**result**

```json
{
 "attempt": 2,
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
 "case": "p2_add_col_volatile_default",
 "attempt": 2,
 "phase1_statements": 1
}
```

</details>

**tool** `migration.parse` (0.06 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"public_token\" TEXT DEFAULT gen_random_uuid()::text;"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "invoices",
  "column": "public_token",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": "gen_random_uuid()::text",
   "unique": false
  },
  "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"public_token\" TEXT DEFAULT gen_random_uuid()::text",
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
    "kind": "add_column",
    "table": "invoices",
    "column": "public_token",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "gen_random_uuid()::text",
     "unique": false
    },
    "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"public_token\" TEXT DEFAULT gen_random_uuid()::text",
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

**tool** `shadow.replay` (2.63 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "public_token",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": "gen_random_uuid()::text",
     "unique": false
    },
    "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"public_token\" TEXT DEFAULT gen_random_uuid()::text",
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
     "email": "katherine@nasa.exam
```

_tool responded_

```json
{
 "materialised": false,
 "schema_errors": [
  "OperationalError: near \"(\": syntax error while running: CREATE TABLE \"invoices\" (",
  "OperationalError: no such table: main.invoices while running: CREATE INDEX \"idx_invoices_customer\" ON \"invoices\" (\"custo..."
 ],
 "data_errors": [
  "backfill invoices: no such table: invoices (row={'id': 1, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV...",
  "backfill invoices: no such table: invoices (row={'id': 2, 'customer_id': 4, 'subscription_id': 3, 'invoice_number': 'INV...",
  "backfill invoices: no such table: invoices (row={'id': 3, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV..."
 ],
 "broken": [
  {
   "query_id": "q_billing_invoice_create",
   "service": "billing-api",
   "criticality": "critical",
   "label": "invoice creation",
   "error": "OperationalError: no such table: invoices",
   "sql": "INSERT INTO invoices (customer_id, invoice_number, amount_cents, issued_at) VALUES (1,'INV-9001',1000,'2026-02-01')"
  },
  {
   "query_id": "q_billing_tax",
   "service": "billing-api",
   "criticality": "high",
   "label": "invoice tax display",
   "error": "OperationalError: no such table: invoices",
   "sql": "SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1"
  },
  {
   "query_id": "q_billing_currency",
   "service": "billing-api",
   "criticality": "medium",
   "label": "currency rollup",
   "error": "OperationalError: no such table: invoices",
   "sql": "SELECT currency, COUNT(*) AS n FROM invoices GROUP BY currency"
  },
  {
   "query_id": "q_dunning_open",
   "service": "dunning-worker",
   "criticality": "critical",
   "label": "open invoice sweep",
   "error": "OperationalError: no such table: main.invoices",
   "sql": "SELECT * FROM open_invoices"
  },
  {
   "query_id": "q_billing_status_update",
   "service": "billing-api",
   "criticality": "high",
   "label": "mark invoice open",
   "error": "OperationalError: no such table: invoices",
   "sql
```

**result**

```json
{
 "verified": false,
 "problems": [
  "q_billing_invoice_create (billing-api): OperationalError: no such table: invoices",
  "q_billing_tax (billing-api): OperationalError: no such table: invoices",
  "q_billing_currency (billing-api): OperationalError: no such table: invoices",
  "q_dunning_open (dunning-worker): OperationalError: no such table: main.invoices",
  "q_billing_status_update (billing-api): OperationalError: no such table: invoices",
  "__view__open_invoices (database): OperationalError: no such table: main.invoices",
  "phase-1 data step failed: backfill invoices: no such table: invoices (row={'id': 1, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV-1001', 'amount_cents': 49900, 'tax_rate': 0.2, 'currency': 'usd', 'status': 'open', 'issued_at': '2026-01-01', 'paid_at': None})",
  "phase-1 data step failed: backfill invoices: no such table: invoices (row={'id': 2, 'customer_id': 4, 'subscription_id': 3, 'invoice_number': 'INV-1002', 'amount_cents': 249900, 'tax_rate': 0.0, 'currency': 'usd', 'status': 'paid', 'issued_at': '2026-01-01', 'paid_at': '2026-01-05'})",
  "phase-1 data step failed: backfill invoices: no such table: invoices (row={'id': 3, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV-1003', 'amount_cents': 1200, 'tax_rate': None, 'currency': 'eur', 'status': 'draft', 'issued_at': None, 'paid_at': None})"
 ],
 "replay": {
  "materialised": false,
  "schema_errors": [
   "OperationalError: near \"(\": syntax error while running: CREATE TABLE \"invoices\" (",
   "OperationalError: no such table: main.invoices while running: CREATE INDEX \"idx_invoices_customer\" ON \"invoices\" (\"customer_id\")"
  ],
  "data_errors": [
   "backfill invoices: no such table: invoices (row={'id': 1, 'customer_id': 1, 'subscription_id': 1, 'invoice_number': 'INV-1001', 'amount_cents': 49900, 'tax_rate': 0.2, 'currency': 'usd', 'status': 'open', 'issued_at': '2026-01-01', 'paid_at': None})",
   "backfill invoices: no such table: invoi
```

**feedback into next step (attempt 2)** phase 1 is not safe yet: q_billing_invoice_create (billing-api): OperationalError: no such table: invoices; q_billing_tax (billing-api): OperationalError: no such table: invoices; q_billing_currency (billing-api): OperationalError: no such table: invoices. Tightening the policy and regenerating.

### Human checkpoint - plan verification: **ESCALATED**

The pipeline could not produce a phase 1 it can prove is safe. A human must decide the sequencing. Remaining problems: q_billing_invoice_create (billing-api): OperationalError: no such table: invoices; q_billing_tax (billing-api): OperationalError: no such table: invoices; q_billing_currency (billing-api): OperationalError: no such table: invoices; q_dunning_open (dunning-worker): OperationalError: no such table: main.invoices; q_billing_status_update (billing-api): OperationalError: no such table: invoices

**model** `scripted-v1` tag=`executive_summary` tokens=38/65 cost=$0.0

> Do not ship this as written. 6 statement(s) the application issues today fail against the post-migration schema in shadow replay. 6 blocker, 1 high, 0 medium, 0 low. The rewritten plan still breaks at least one statement, so a human has to decide the sequencing.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
