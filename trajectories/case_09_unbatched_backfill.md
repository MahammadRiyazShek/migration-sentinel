# Trajectory - case_09_unbatched_backfill

- run id: `eval-case_09_unbatched_backfill`
- case: `case_09_unbatched_backfill`
- events: 29

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "case_09_unbatched_backfill",
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

**tool** `schema.parse` (0.74 ms)

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
  "sql": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL;\nALTER TABLE invoices ALTER COLUMN currency SET NOT NULL;\n"
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
  "sql": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL",
  "index": 0
 },
 {
  "kind": "set_not_null",
  "table": "invoices",
  "column": "currency",
  "detail": {},
  "sql": "ALTER TABLE invoices ALTER COLUMN currency SET NOT NULL",
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
    "kind": "dml_update",
    "table": "invoices",
    "column": null,
    "detail": {
     "where": true,
     "batched": false
    },
    "sql": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL",
    "index": 0
   },
   {
    "kind": "set_not_null",
    "table": "invoices",
    "column": "currency",
    "detail": {},
    "sql": "ALTER TABLE invoices ALTER COLUMN currency SET NOT NULL",
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
  "set_not_null"
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
 "case": "case_09_unbatched_backfill",
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
   "currency",
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
     "currency",
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

**tool** `shadow.replay` (2.66 ms)

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
    "sql": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL",
    "index": 0
   },
   {
    "kind": "set_not_null",
    "table": "invoices",
    "column": "currency",
    "detail": {},
    "sql": "ALTER TABLE invoices ALTER COLUMN currency SET NOT NULL",
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
     "sig
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
 "case": "case_09_unbatched_backfill",
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

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "NOT_NULL_NO_DEFAULT",
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
    "sql": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL",
    "index": 0
   },
   {
    "kind": "set_not_null",
    "table": "invoices",
    "column": "currency",
    "detail": {},
    "sql": "ALTER TABLE invoices ALTER COLUMN currency SET NOT NULL",
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
    "id": "q_bi_summary
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "value_class_erased",
   "object": "invoices.currency",
   "statement_index": 0,
   "statement": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL",
   "why": "the backfill removes every NULL from invoices.currency and the following SET NOT NULL makes NULL unreachable; any consum...",
   "closes_with": "a reviewer confirms no consumer treats invoices.currency IS NULL as meaningful, and that the pre-backfill values are cap...",
   "irreversible": true
  }
 ],
 "gap_kinds": [
  "value_class_erased"
 ],
 "irreversible": [
  "invoices.currency"
 ],
 "corpus_statements": 14,
 "parser_notes": []
}
```

_note (risk_officer)_: verdict capped to NEEDS_COVERAGE_SIGNOFF: 1 coverage gap(s) on objects this migration touches (invoices.currency). No hazard was invented; the packet cannot certify what it did not see.

**model** `scripted-v1` tag=`hazard_narrative` tokens=430/48 cost=$0.0

> NOT NULL added without a usable default. Existing rows or in-flight inserts violate the constraint immediately. Evidence: statement 1: `ALTER TABLE invoices ALTER COLUMN currency SET NOT NULL`

**model** `scripted-v1` tag=`hazard_narrative` tokens=428/51 cost=$0.0

> Backfill runs as one unbounded statement. One long transaction holds locks and bloats WAL; it cannot be paused or resumed. Evidence: statement 0: `UPDATE invoices SET currency = 'usd' WHERE currency IS NULL`

**result**

```json
{
 "verdict": "NEEDS_COVERAGE_SIGNOFF",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 2,
  "blocker": 0
 },
 "coverage_gaps": [
  "value_class_erased:invoices.currency"
 ],
 "verdict_capped_by_coverage": true,
 "hazards": [
  {
   "code": "NOT_NULL_NO_DEFAULT",
   "severity": "high",
   "source": "static",
   "memory": []
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
 "case": "case_09_unbatched_backfill",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "NOT_NULL_NO_DEFAULT",
  "UNBATCHED_BACKFILL"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=483/28 cost=$0.0

> - What is the accepted risk for NOT_NULL_NO_DEFAULT?
> - What batch size and pause has this table tolerated before?

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
 "case": "case_09_unbatched_backfill",
 "attempt": 1,
 "phase1_statements": 2
}
```

</details>

**tool** `migration.parse` (0.06 ms)

```json
{
 "args": {
  "sql": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE currency IS NULL LIMIT 5000);"
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
  "sql": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE currency IS N...",
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
    "sql": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE currency IS N...",
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

**tool** `shadow.replay` (2.61 ms)

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
    "sql": "UPDATE invoices SET currency = 'usd' WHERE currency IS NULL AND \"id\" IN (SELECT \"id\" FROM \"invoices\" WHERE currency IS N...",
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

**model** `scripted-v1` tag=`executive_summary` tokens=43/77 cost=$0.0

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 2 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - coverage sign-off: **REQUIRED**

The verdict is capped at NEEDS_COVERAGE_SIGNOFF. The hazards found are not blocking, but this review has 1 declared blind spot(s) on objects the migration touches, and a packet must not certify what it did not see. Each gap is a human gate in the plan.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
