# Trajectory - case_02_drop_column_still_read

- run id: `eval-case_02_drop_column_still_read`
- case: `case_02_drop_column_still_read`
- events: 33

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "case_02_drop_column_still_read",
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

**tool** `schema.parse` (0.72 ms)

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

**tool** `migration.parse` (0.03 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE customers DROP COLUMN company_name;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "drop_column",
  "table": "customers",
  "column": "company_name",
  "detail": {},
  "sql": "ALTER TABLE customers DROP COLUMN company_name",
  "index": 0
 }
]
```

**tool** `schema.apply_ops` (0.14 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "drop_column",
    "table": "customers",
    "column": "company_name",
    "detail": {},
    "sql": "ALTER TABLE customers DROP COLUMN company_name",
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
  "drop_column"
 ],
 "tables_touched": [
  "customers"
 ],
 "unmodelled": []
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "case_02_drop_column_still_read",
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

**tool** `corpus.dependents` (0.21 ms)

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
  "query_id": "q_web_profile",
  "service": "web",
  "criticality": "critical",
  "matched": [
   "customers"
  ],
  "uses_select_star": false,
  "label": "customer profile page"
 },
 {
  "query_id": "q_web_signup",
  "service": "web",
  "criticality": "critical",
  "matched": [
   "customers"
  ],
  "uses_select_star": false,
  "label": "signup insert"
 },
 {
  "query_id": "q_support_lookup",
  "service": "support-admin",
  "criticality": "high",
  "matched": [
   "company_name",
   "customers"
  ],
  "uses_select_star": false,
  "label": "support customer lookup"
 },
 {
  "query_id": "q_bi_summary",
  "service": "bi",
  "criticality": "high",
  "matched": [
   "customer_billing_summary"
  ],
  "uses_select_star": true,
  "label": "dbt model stg_customers"
 },
 {
  "query_id": "q_bi_mrr",
  "service": "bi",
  "criticality": "medium",
  "matched": [
   "customers"
  ],
  "uses_select_star": false,
  "label": "MRR by plan"
 },
 {
  "query_id": "q_bi_country",
  "service": "bi",
  "criticality": "low",
  "matched": [
   "customers"
  ],
  "uses_select_star": false,
  "label": "customers by country"
 }
]
```

**tool** `corpus.blast_score` (0.05 ms)

```json
{
 "args": {
  "hits": [
   {
    "query_id": "q_web_profile",
    "service": "web",
    "criticality": "critical",
    "matched": [
     "customers"
    ],
    "uses_select_star": false,
    "label": "customer profile page"
   },
   {
    "query_id": "q_web_signup",
    "service": "web",
    "criticality": "critical",
    "matched": [
     "customers"
    ],
    "uses_select_star": false,
    "label": "signup insert"
   },
   {
    "query_id": "q_support_lookup",
    "service": "support-admin",
    "criticality": "high",
    "matched": [
     "company_name",
     "customers"
    ],
    "uses_select_star": false,
    "label": "support customer lookup"
   },
   {
    "query_id": "q_bi_summary",
    "service": "bi",
    "criticality": "high",
    "matched": [
     "customer_billing_summary"
    ],
    "uses_select_star": true,
    "label": "dbt model stg_customers"
   },
   {
    "query_id": "q_bi_mrr",
    "service": "bi",
    "criticality": "medium",
    "matched": [
     "customers"
    ],
    "uses_select_star": false,
    "label": "MRR by plan"
   },
   {
    "query_id": "q_bi_country",
    "service": "bi",
    "criticality": "low",
    "matched": [
     "customers"
    ],
    "
```

_tool responded_

```json
17
```

**tool** `shadow.replay` (4.49 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "drop_column",
    "table": "customers",
    "column": "company_name",
    "detail": {},
    "sql": "ALTER TABLE customers DROP COLUMN company_name",
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
     "country_code": "US",
     "plan": "enterprise",
     "mrr_cents": 249900,
 
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [],
 "broken": [
  {
   "query_id": "q_support_lookup",
   "service": "support-admin",
   "criticality": "high",
   "label": "support customer lookup",
   "error": "OperationalError: no such column: company_name",
   "sql": "SELECT id, email, company_name FROM customers WHERE email = 'ada@corp.example'"
  }
 ],
 "column_drift": [
  {
   "query_id": "q_bi_summary",
   "service": "bi",
   "criticality": "high",
   "before": [
    "id",
    "email",
    "full_name",
    "company_name",
    "country_code",
    "plan",
    "mrr_cents",
    "signed_up_at"
   ],
   "after": [
    "id",
    "email",
    "full_name",
    "country_code",
    "plan",
    "mrr_cents",
    "signed_up_at"
   ],
   "removed": [
    "company_name"
   ],
   "added": [],
   "sql": "SELECT * FROM customer_billing_summary"
  },
  {
   "query_id": "__view__customer_billing_summary",
   "service": "database",
   "criticality": "high",
   "before": [
    "id",
    "email",
    "full_name",
    "company_name",
    "country_code",
    "plan",
    "mrr_cents",
    "signed_up_at"
   ],
   "after": [
    "id",
    "email",
    "full_name",
    "country_code",
    "plan",
    "mrr_cents",
    "signed_up_at"
   ],
   "removed": [
    "company_name"
   ],
   "added": [],
   "sql": "SELECT * FROM \"customer_billing_summary\" LIMIT 1"
  }
 ],
 "rowcount_drift": [],
 "data_loss": [],
 "queries_run": 16,
 "queries_ok_before": 16,
 "queries_ok_after": 15
}
```

**result**

```json
{
 "dependent_queries": 6,
 "blast_score": 17,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [],
  "broken": [
   {
    "query_id": "q_support_lookup",
    "service": "support-admin",
    "criticality": "high",
    "label": "support customer lookup",
    "error": "OperationalError: no such column: company_name",
    "sql": "SELECT id, email, company_name FROM customers WHERE email = 'ada@corp.example'"
   }
  ],
  "column_drift": [
   {
    "query_id": "q_bi_summary",
    "service": "bi",
    "criticality": "high",
    "before": [
     "id",
     "email",
     "full_name",
     "company_name",
     "country_code",
     "plan",
     "mrr_cents",
     "signed_up_at"
    ],
    "after": [
     "id",
     "email",
     "full_name",
     "country_code",
     "plan",
     "mrr_cents",
     "signed_up_at"
    ],
    "removed": [
     "company_name"
    ],
    "added": [],
    "sql": "SELECT * FROM customer_billing_summary"
   },
   {
    "query_id": "__view__customer_billing_summary",
    "service": "database",
    "criticality": "high",
    "before": [
     "id",
     "email",
     "full_name",
     "company_name",
     "country_code",
     "plan",
     "mrr_cents",
     "signed_up_at"
    ],
    "after": [
     "id",
     "email",
     "full_name",
     "country_code",
     "plan",
     "mrr_cents",
     "signed_up_at"
    ],
    "removed": [
     "company_name"
    ],
    "added": [],
    "sql": "SELECT * FROM \"customer_billing_summary\" LIMIT 1"
   }
  ],
  "rowcount_drift": [],
  "data_loss": [],
  "queries_run": 16,
  "queries_ok_before": 16,
  "queries_ok_after": 15
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
 "case": "case_02_drop_column_still_read",
 "row_estimates": {
  "customers": 2400000,
  "subscriptions": 2600000,
  "invoices": 48000000,
  "invoice_lines": 190000000,
  "usage_events": 900000000
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
  "table": "q_support_lookup"
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
  "table": "customers"
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

**tool** `memory.escalation` (0.01 ms)

```json
{
 "args": {
  "hazard_code": "SELECT_STAR_DRIFT",
  "table": "q_bi_summary"
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

**tool** `coverage.ledger` (0.14 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "drop_column",
    "table": "customers",
    "column": "company_name",
    "detail": {},
    "sql": "ALTER TABLE customers DROP COLUMN company_name",
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
    "id": "q_bi_mrr",
    "service": "bi",
    "criticality": "medium",
    "label": "M
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

**model** `scripted-v1` tag=`hazard_narrative` tokens=456/76 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `SELECT id, email, company_name FROM customers WHERE email = 'ada@corp.example'` -> OperationalError: no such column: company_name Owning service(s): support-admin.

**model** `scripted-v1` tag=`hazard_narrative` tokens=434/64 cost=$0.0

> Impact lands on a service owned by another team. The fix needs a deploy the migration author does not control, so ordering must be agreed first. Evidence: corpus ownership of failing statements: ['bi', 'support-admin'] Owning service(s): bi, support-admin.

**model** `scripted-v1` tag=`hazard_narrative` tokens=435/59 cost=$0.0

> Destructive change shipped in a single step. Dropping or renaming in one deploy means old and new application code cannot both work. Evidence: statement 0: `ALTER TABLE customers DROP COLUMN company_name` Previously bit us in INC-2023-09.

**model** `scripted-v1` tag=`hazard_narrative` tokens=477/106 cost=$0.0

> SELECT * consumer receives a different column set. The query still runs, so tests pass, but downstream code indexing by position or key breaks. Evidence: shadow replay columns before=['id', 'email', 'full_name', 'company_name', 'country_code', 'plan', 'mrr_cents', 'signed_up_at'] after=['id', 'email', 'full_name', 'country_code', 'plan', 'mrr_cents', 'signed_up_at'] Owning service(s): bi. Previously bit us in INC-2025-02.

**model** `scripted-v1` tag=`hazard_narrative` tokens=406/30 cost=$0.0

> No rollback path supplied. Recovery at 3am should not require improvising DDL. Evidence: case field `rollback_sql` is empty

**result**

```json
{
 "verdict": "BLOCK",
 "counts": {
  "low": 0,
  "medium": 1,
  "high": 3,
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
 "case": "case_02_drop_column_still_read",
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
  "MISSING_ROLLBACK",
  "SELECT_STAR_DRIFT"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=503/76 cost=$0.0

> - Which deploy lands first: the query change or the schema change?
> - Has the owning team agreed to the deploy order?
> - What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
> - What is the accepted risk for MISSING_ROLLBACK?
> - Do any consumers read this result set positionally or serialise it whole?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 0,
 "phase2_statements": 1,
 "human_gates": 2
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "case_02_drop_column_still_read",
 "attempt": 1,
 "phase1_statements": 0
}
```

</details>

**tool** `migration.parse` (0.01 ms)

```json
{
 "args": {
  "sql": ""
 }
}
```

_tool responded_

```json
[]
```

**tool** `schema.apply_ops` (0.06 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": []
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

**tool** `shadow.replay` (3.11 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [],
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
     "country_code": "US",
     "plan": "enterprise",
     "mrr_cents": 249900,
     "signed_up_at": "2023-11-20"
    }
   ],
   "subscriptions": [
    {
     "id": 1,
     "customer_id": 1,
     "status": "active",
     "seats": 12,
     "price_cents": 49900,
     "star
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

**model** `scripted-v1` tag=`executive_summary` tokens=38/60 cost=$0.0

> Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 3 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
