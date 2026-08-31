# Trajectory - rt2_03_unterminated_literal

- run id: `eval-rt2_03_unterminated_literal`
- case: `rt2_03_unterminated_literal`
- events: 43

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_03_unterminated_literal",
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

**tool** `migration.parse` (0.05 ms)

```json
{
 "args": {
  "sql": "UPDATE invoices SET status = 'open WHERE id = 1;\nALTER TABLE invoices DROP COLUMN tax_rate;\n"
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
  "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate;",
  "index": 0
 }
]
```

**tool** `migration.audit` (0.05 ms)

```json
{
 "args": {
  "migration_sql": "UPDATE invoices SET status = 'open WHERE id = 1;\nALTER TABLE invoices DROP COLUMN tax_rate;\n",
  "ops": [
   {
    "kind": "dml_update",
    "table": "invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": false
    },
    "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate;",
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
 "unterminated": [
  {
   "kind": "string",
   "start": 29,
   "end": 92,
   "text": "'open WHERE id = 1;\nALTER TABLE invoices DROP COLUMN tax_rate;\n",
   "why": "a single-quoted literal never closes, so Postgres rejects the script and everything after the quote was read as string c..."
  }
 ],
 "unaccounted": [],
 "procedural": [],
 "conservation": {
  "significant_chars": 74,
  "attributed_chars": 74,
  "unattributed_chars": 0
 },
 "clean": false
}
```

**tool** `schema.apply_ops` (0.05 ms)

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
    "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate;",
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

_note (cartographer)_: parse conservation: the scanner finds 1 statement(s) in this file and the parse produced 1 operation(s); 1 unterminated construct(s), 0 statement(s) no operation accounts for, 0 procedural body/bodies. Reported as findings or declared gaps rather than reviewed as a smaller migration.

**result**

```json
{
 "op_kinds": [
  "dml_update"
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
 "case": "rt2_03_unterminated_literal",
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

**tool** `shadow.replay` (3.44 ms)

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
    "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate;",
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
     "full_name": "Katherine Johnson",
     "company_name": "NASA",
 
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [
  "migration DML failed (stmt 0): unrecognized token: \"'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate;\" :: U..."
 ],
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
  "data_errors": [
   "migration DML failed (stmt 0): unrecognized token: \"'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate;\" :: UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate"
  ],
  "broken": [],
  "column_drift": [],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 19,
  "queries_ok_before": 19,
  "queries_ok_after": 19
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
 "case": "rt2_03_unterminated_literal",
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

### Human checkpoint - parse conservation: **SCRIPT DOES NOT PARSE**

Postgres will refuse this script, so no statement in it executes and any finding read off the mangled remainder would be a claim about text that never runs. Suppressed for that reason: BREAKING_QUERY, UNBATCHED_BACKFILL. The only honest output is the parse failure and the region nobody could read. Fix the script and resubmit for review.

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "MIGRATION_TEXT_UNPARSED",
  "table": "migration script"
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

**tool** `coverage.ledger` (0.19 ms)

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
    "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate;",
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
    "label": "dbt model stg_customers",
    "sql": "SELECT * FROM customer_billing_summary"
   },
   {
    "id
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "in_place_data_mutation",
   "object": "invoices.status",
   "object_inferred": false,
   "statement_index": 0,
   "statement": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate;",
   "why": "rows that already exist in invoices are rewritten; replay proves the corpus still executes, never that it still returns ...",
   "closes_with": "a reviewer confirms which consumers of invoices.status depend on the current values",
   "irreversible": false
  },
  {
   "kind": "unreviewable_text",
   "object": "characters 29 onward",
   "object_inferred": false,
   "statement_index": null,
   "statement": "'open WHERE id = 1;\nALTER TABLE invoices DROP COLUMN tax_rate;\n",
   "why": "an unterminated string starts at character 29; from there to the end of the file every character was read as string cont...",
   "closes_with": "the script is fixed and resubmitted; there is nothing here for a reviewer to sign off, because there is nothing here tha...",
   "irreversible": false
  }
 ],
 "gap_kinds": [
  "in_place_data_mutation",
  "unreviewable_text"
 ],
 "irreversible": [],
 "corpus_statements": 17,
 "parser_notes": []
}
```

**model** `scripted-v1` tag=`hazard_narrative` tokens=519/86 cost=$0.0

> Migration text no structural review covered. The reviewed artefact and the deployed artefact are not the same object: the scanner finds a statement or an unterminated construct that no parsed operation accounts for, so a rule never saw it and replay never ran it. Evidence: scanner: `'open WHERE id = 1;
> ALTER TABLE invoices DROP COLUMN tax_rate;`

**result**

```json
{
 "verdict": "BLOCK",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 0,
  "blocker": 1
 },
 "coverage_gaps": [
  "in_place_data_mutation:invoices.status",
  "unreviewable_text:characters 29 onward"
 ],
 "verdict_capped_by_coverage": false,
 "hazards": [
  {
   "code": "MIGRATION_TEXT_UNPARSED",
   "severity": "blocker",
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
 "case": "rt2_03_unterminated_literal",
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
  "MIGRATION_TEXT_UNPARSED"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=478/14 cost=$0.0

> - What is the accepted risk for MIGRATION_TEXT_UNPARSED?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 2,
 "phase2_statements": 0,
 "human_gates": 2
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_03_unterminated_literal",
 "attempt": 1,
 "phase1_statements": 2
}
```

</details>

**tool** `migration.parse` (0.07 ms)

```json
{
 "args": {
  "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);"
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
  "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM...",
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
    "kind": "dml_update",
    "table": "invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": true
    },
    "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM...",
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

**tool** `shadow.replay` (2.87 ms)

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
    "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM...",
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
     "full_name": "Katherine Johns
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [
  "migration DML failed (stmt 0): unrecognized token: \"'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"i..."
 ],
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
 "verified": false,
 "problems": [
  "phase-1 data step failed: migration DML failed (stmt 0): unrecognized token: \"'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);\" :: UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate"
 ],
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [
   "migration DML failed (stmt 0): unrecognized token: \"'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);\" :: UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate"
  ],
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

**feedback into next step (attempt 1)** phase 1 is not safe yet: phase-1 data step failed: migration DML failed (stmt 0): unrecognized token: "'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND "id" IN (SELECT "id" FROM "invoices" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);" :: UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate. Tightening the policy and regenerating.

**RETRY 2** because: phase-1 data step failed: migration DML failed (stmt 0): unrecognized token: "'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND "id" IN (SELECT "id" FROM "invoices" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);" :: UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate

## Agent: rollout_engineer

**Goal** Rewrite the migration as a phase-1 (expand, safe now) / phase-2 (contract, after the code deploy) plan with a rollback, and surface every step that needs a human decision.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_03_unterminated_literal",
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
  "MIGRATION_TEXT_UNPARSED"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=478/14 cost=$0.0

> - What is the accepted risk for MIGRATION_TEXT_UNPARSED?

**result**

```json
{
 "attempt": 2,
 "phase1_statements": 2,
 "phase2_statements": 0,
 "human_gates": 3
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_03_unterminated_literal",
 "attempt": 2,
 "phase1_statements": 2
}
```

</details>

**tool** `migration.parse` (0.08 ms)

```json
{
 "args": {
  "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);"
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
  "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM...",
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
    "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM...",
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

**tool** `shadow.replay` (2.9 ms)

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
    "sql": "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM...",
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
     "full_name": "Katherine Johns
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [
  "migration DML failed (stmt 0): unrecognized token: \"'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"i..."
 ],
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
 "verified": false,
 "problems": [
  "phase-1 data step failed: migration DML failed (stmt 0): unrecognized token: \"'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);\" :: UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate"
 ],
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [
   "migration DML failed (stmt 0): unrecognized token: \"'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);\" :: UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate"
  ],
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

**feedback into next step (attempt 2)** phase 1 is not safe yet: phase-1 data step failed: migration DML failed (stmt 0): unrecognized token: "'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND "id" IN (SELECT "id" FROM "invoices" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);" :: UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate. Tightening the policy and regenerating.

**tool** `plan.audit` (0.36 ms)

```json
{
 "args": {
  "plan": {
   "attempt": 2,
   "phase1_sql": [
    "-- repeat until zero rows are affected (batch size 5000):",
    "UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND \"id\" IN (SELECT \"id\" FROM..."
   ],
   "phase2_sql": [],
   "rollback_sql": [],
   "code_steps": [],
   "human_gates": [
    "phase 1 was reduced to additive statements only; the rest needs a human to choose the deploy order",
    "coverage gap on `invoices.status` (in_place_data_mutation): a reviewer confirms which consumers of invoices.status depen...",
    "coverage gap on `characters 29 onward` (unreviewable_text): the script is fixed and resubmitted; there is nothing here f..."
   ],
   "questions": [
    "What is the accepted risk for MIGRATION_TEXT_UNPARSED?"
   ],
   "questions_source": "model",
   "questions_dropped": [],
   "policy": {
    "include_view_changes": true,
    "expand_contract_type_change": true,
    "minimal_phase1": true,
    "notes": [
     "fell back to a minimal additive phase 1: everything not provably backwards compatible moved to phase 2"
    ]
   }
  },
  "schema": "Schema",
  "queries": [
   {
    "id": "q_web_profile",
   
```

_tool responded_

```json
{
 "statements_audited": 1,
 "scripts": {
  "phase1": 1,
  "phase2": 0,
  "rollback": 0
 },
 "findings": [
  {
   "code": "GENERATED_TEXT_UNPARSED",
   "title": "This pipeline emitted SQL it cannot itself read back",
   "script": "phase1",
   "statement_index": null,
   "statement": "{'kind': 'string', 'start': 29, 'end': 200, 'text': '\\'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND",
   "objects": [],
   "why": "an unterminated construct in the generated script, which Postgres would refuse, so this packet is printing SQL it did no...",
   "closes_with": "a reviewer reads the generated script by hand before running it",
   "evidence": [
    "tools/parse_audit.py on the generated phase1 script: an unterminated construct in the generated script, which Postgres w...",
    "statements lexed 1, ops produced 1"
   ]
  }
 ],
 "finding_codes": [
  "GENERATED_TEXT_UNPARSED"
 ],
 "gaps": [],
 "gap_kinds": [],
 "kind_inventory": [
  {
   "script": "phase1",
   "statement_index": 0,
   "kind": "dml_update",
   "bucket": "RULED"
  }
 ],
 "gates_trusted": 0,
 "replay": {
  "ran": true,
  "scripts": {},
  "note": "the generated phase 2 is expected to break today's statements - that is what the code steps are for. The number is publi..."
 },
 "clean": false
}
```

### Human checkpoint - plan self-audit: **PLAN DEFECT**

GENERATED_TEXT_UNPARSED in the generated phase1 script: an unterminated construct in the generated script, which Postgres would refuse, so this packet is printing SQL it did not fully model Closes when: a reviewer reads the generated script by hand before running it

### Human checkpoint - plan verification: **ESCALATED**

The pipeline could not produce a phase 1 it can prove is safe. A human must decide the sequencing. Remaining problems: phase-1 data step failed: migration DML failed (stmt 0): unrecognized token: "'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND "id" IN (SELECT "id" FROM "invoices" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);" :: UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate

**model** `scripted-v1` tag=`executive_summary` tokens=38/58 cost=$0.0

> Do not ship this as written. 2 coverage gap(s) need a named sign-off before this can be called safe. 1 blocker, 0 high, 0 medium, 0 low. The rewritten plan still breaks at least one statement, so a human has to decide the sequencing.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
