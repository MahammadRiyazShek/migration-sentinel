# Trajectory - rt2_05_function_body_no_ddl

- run id: `eval-rt2_05_function_body_no_ddl`
- case: `rt2_05_function_body_no_ddl`
- events: 29

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_05_function_body_no_ddl",
 "migration_statements": 5,
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

**tool** `schema.parse` (0.82 ms)

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

**tool** `migration.parse` (0.13 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE invoices ADD COLUMN dunning_stamped_at TIMESTAMPTZ;\nCREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$\nBEGIN\n  NEW.dunning_stamped_at := now();\n  RETURN NEW;\nEND;\n$fn$ LANGUAGE plpgsql;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "invoices",
  "column": "dunning_stamped_at",
  "detail": {
   "type": "TIMESTAMPTZ",
   "not_null": false,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE invoices ADD COLUMN dunning_stamped_at TIMESTAMPTZ",
  "index": 0
 },
 {
  "kind": "procedural_block",
  "table": null,
  "column": null,
  "detail": {
   "head": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dun",
   "bodies": [
    "$fn$"
   ]
  },
  "sql": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dunning_stamped_at := now(); RETURN NEW; EN...",
  "index": 1
 }
]
```

**tool** `migration.audit` (0.17 ms)

```json
{
 "args": {
  "migration_sql": "ALTER TABLE invoices ADD COLUMN dunning_stamped_at TIMESTAMPTZ;\nCREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$\nBEGIN\n  NEW.dunning_stamped_at := now();\n  RETURN NEW;\nEND;\n$fn$ LANGUAGE plpgsql;\n",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_stamped_at",
    "detail": {
     "type": "TIMESTAMPTZ",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN dunning_stamped_at TIMESTAMPTZ",
    "index": 0
   },
   {
    "kind": "procedural_block",
    "table": null,
    "column": null,
    "detail": {
     "head": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dun",
     "bodies": [
      "$fn$"
     ]
    },
    "sql": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dunning_stamped_at := now(); RETURN NEW; EN...",
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
 "procedural": [
  {
   "statement_index": 1,
   "tag": "$fn$",
   "head": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.",
   "start": 126,
   "end": 195,
   "body_statements": 3,
   "inner": [
    {
     "excerpt": "BEGIN NEW.dunning_stamped_at := now()",
     "keyword": "begin",
     "text": "BEGIN NEW.dunning_stamped_at := now()",
     "control_flow": true,
     "ddl_or_dml": false,
     "destructive": false
    },
    {
     "excerpt": "RETURN NEW",
     "keyword": "return new",
     "text": "RETURN NEW",
     "control_flow": true,
     "ddl_or_dml": false,
     "destructive": false
    },
    {
     "excerpt": "END",
     "keyword": "end",
     "text": "END",
     "control_flow": true,
     "ddl_or_dml": false,
     "destructive": false
    }
   ],
   "ddl_inside": [],
   "destructive_inside": []
  }
 ],
 "conservation": {
  "significant_chars": 179,
  "attributed_chars": 179,
  "unattributed_chars": 0
 },
 "clean": false
}
```

**tool** `schema.apply_ops` (0.09 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_stamped_at",
    "detail": {
     "type": "TIMESTAMPTZ",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN dunning_stamped_at TIMESTAMPTZ",
    "index": 0
   },
   {
    "kind": "procedural_block",
    "table": null,
    "column": null,
    "detail": {
     "head": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dun",
     "bodies": [
      "$fn$"
     ]
    },
    "sql": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dunning_stamped_at := now(); RETURN NEW; EN...",
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
 [
  "op 1 (procedural_block) not modelled structurally: CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger A"
 ]
]
```

_note (cartographer)_: parse conservation: the scanner finds 2 statement(s) in this file and the parse produced 2 operation(s); 0 unterminated construct(s), 0 statement(s) no operation accounts for, 1 procedural body/bodies. Reported as findings or declared gaps rather than reviewed as a smaller migration.

_note (cartographer)_: Some statements could not be modelled structurally; they are passed to the risk officer as unknowns rather than silently assumed safe.

**result**

```json
{
 "op_kinds": [
  "add_column",
  "procedural_block"
 ],
 "tables_touched": [
  "invoices"
 ],
 "unmodelled": [
  "op 1 (procedural_block) not modelled structurally: CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger A"
 ]
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_05_function_body_no_ddl",
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

**tool** `corpus.dependents` (0.13 ms)

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

**tool** `shadow.replay` (3.04 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_stamped_at",
    "detail": {
     "type": "TIMESTAMPTZ",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN dunning_stamped_at TIMESTAMPTZ",
    "index": 0
   },
   {
    "kind": "procedural_block",
    "table": null,
    "column": null,
    "detail": {
     "head": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dun",
     "bodies": [
      "$fn$"
     ]
    },
    "sql": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dunning_stamped_at := now(); RETURN NEW; EN...",
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
     "p
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
 "case": "rt2_05_function_body_no_ddl",
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

**tool** `coverage.ledger` (0.19 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_stamped_at",
    "detail": {
     "type": "TIMESTAMPTZ",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE invoices ADD COLUMN dunning_stamped_at TIMESTAMPTZ",
    "index": 0
   },
   {
    "kind": "procedural_block",
    "table": null,
    "column": null,
    "detail": {
     "head": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dun",
     "bodies": [
      "$fn$"
     ]
    },
    "sql": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.dunning_stamped_at := now(); RETURN NEW; EN...",
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
    "sql": "INSERT INTO customers (email, full_name, signed_up_at) VALUES ('new@corp.example','New Person','2026-02-0
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "procedural_body",
   "object": "$fn$ body at statement 1",
   "object_inferred": false,
   "statement_index": 1,
   "statement": "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$ BEGIN NEW.",
   "why": "the body holds 3 scanned statement(s) and nothing in this pipeline models a procedural block: the census below is a keyw...",
   "closes_with": "a reviewer reads the $fn$ body of statement 1 in full, including every branch, before phase 1",
   "irreversible": false
  }
 ],
 "gap_kinds": [
  "procedural_body"
 ],
 "irreversible": [],
 "corpus_statements": 17,
 "parser_notes": [
  "op 1 (procedural_block) not modelled structurally: CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger A"
 ]
}
```

_note (risk_officer)_: verdict capped to NEEDS_COVERAGE_SIGNOFF: 1 coverage gap(s) on objects this migration touches ($fn$ body at statement 1). No hazard was invented; the packet cannot certify what it did not see.

**result**

```json
{
 "verdict": "NEEDS_COVERAGE_SIGNOFF",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 0,
  "blocker": 0
 },
 "coverage_gaps": [
  "procedural_body:$fn$ body at statement 1"
 ],
 "verdict_capped_by_coverage": true,
 "hazards": []
}
```

## Agent: rollout_engineer

**Goal** Rewrite the migration as a phase-1 (expand, safe now) / phase-2 (contract, after the code deploy) plan with a rollback, and surface every step that needs a human decision.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_05_function_body_no_ddl",
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
 "human_gates": 2
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_05_function_body_no_ddl",
 "attempt": 1,
 "phase1_statements": 1
}
```

</details>

**tool** `migration.parse` (0.06 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"dunning_stamped_at\" TIMESTAMPTZ;"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "invoices",
  "column": "dunning_stamped_at",
  "detail": {
   "type": "TIMESTAMPTZ",
   "not_null": false,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"dunning_stamped_at\" TIMESTAMPTZ",
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
    "column": "dunning_stamped_at",
    "detail": {
     "type": "TIMESTAMPTZ",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"dunning_stamped_at\" TIMESTAMPTZ",
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

**tool** `shadow.replay` (2.88 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "invoices",
    "column": "dunning_stamped_at",
    "detail": {
     "type": "TIMESTAMPTZ",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"invoices\" ADD COLUMN \"dunning_stamped_at\" TIMESTAMPTZ",
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
     "full_name": "Ka
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

**model** `scripted-v1` tag=`executive_summary` tokens=43/77 cost=$0.0

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - coverage sign-off: **REQUIRED**

The verdict is capped at NEEDS_COVERAGE_SIGNOFF. The hazards found are not blocking, but this review has 1 declared blind spot(s) on objects the migration touches, and a packet must not certify what it did not see. Each gap is a human gate in the plan.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
