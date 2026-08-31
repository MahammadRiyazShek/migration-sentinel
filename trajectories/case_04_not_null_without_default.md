# Trajectory - case_04_not_null_without_default

- run id: `eval-case_04_not_null_without_default`
- case: `case_04_not_null_without_default`
- events: 32

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "case_04_not_null_without_default",
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

**tool** `migration.parse` (0.03 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "customers",
  "column": "billing_email",
  "detail": {
   "type": "TEXT",
   "not_null": true,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL",
  "index": 0
 }
]
```

**tool** `migration.audit` (0.03 ms)

```json
{
 "args": {
  "migration_sql": "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL;\n",
  "ops": [
   {
    "kind": "add_column",
    "table": "customers",
    "column": "billing_email",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL",
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
  "significant_chars": 52,
  "attributed_chars": 52,
  "unattributed_chars": 0
 },
 "clean": true
}
```

**tool** `schema.apply_ops` (0.04 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "customers",
    "column": "billing_email",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL",
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
 "case": "case_04_not_null_without_default",
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

**tool** `corpus.dependents` (0.1 ms)

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

**tool** `corpus.blast_score` (0.02 ms)

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
    "uses_select_star": fa
```

_tool responded_

```json
17
```

**tool** `shadow.replay` (2.05 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "customers",
    "column": "billing_email",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL",
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
    
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [
  "backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 1, 'email': 'ada@corp.example', 'ful...",
  "backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 2, 'email': 'grace@corp.example', 'f...",
  "backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 3, 'email': 'alan@lab.example', 'ful...",
  "backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 4, 'email': 'katherine@nasa.example'..."
 ],
 "broken": [
  {
   "query_id": "q_web_signup",
   "service": "web",
   "criticality": "critical",
   "label": "signup insert",
   "error": "IntegrityError: NOT NULL constraint failed: customers.billing_email",
   "sql": "INSERT INTO customers (email, full_name, signed_up_at) VALUES ('new@corp.example','New Person','2026-02-01')"
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
    "company_name",
    "country_code",
    "plan",
    "mrr_cents",
    "signed_up_at",
    "...+1 more"
   ],
   "removed": [],
   "added": [
    "billing_email"
   ],
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
    "company_name",
    "country_code",
    "plan",
    "mrr_cents",
    "signed_up_at",
    "...+1 more"
   ],
   "removed": [],
   "added": [
    "billing_email"
   ],
   "sql": "SELECT * FROM \"customer_billing_summary\" LIMIT 1"
  }

```

_note (blast_radius)_: q_bi_summary gains column(s) ['billing_email']; recorded as a note, not a hazard, because nothing is removed from the result set

**result**

```json
{
 "dependent_queries": 6,
 "blast_score": 17,
 "replay": {
  "materialised": true,
  "schema_errors": [],
  "data_errors": [
   "backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 1, 'email': 'ada@corp.example', 'full_name': 'Ada Lovelace', 'company_name': 'Corp', 'country_code': 'US', 'plan': 'business', 'mrr_cents': 49900, 'signed_up_at': '2024-01-04'})",
   "backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 2, 'email': 'grace@corp.example', 'full_name': 'Grace Hopper', 'company_name': 'Corp', 'country_code': 'USA', 'plan': 'team', 'mrr_cents': 9900, 'signed_up_at': '2024-03-11'})",
   "backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 3, 'email': 'alan@lab.example', 'full_name': 'Alan Turing', 'company_name': None, 'country_code': 'GB', 'plan': 'free', 'mrr_cents': 0, 'signed_up_at': '2025-06-02'})",
   "backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 4, 'email': 'katherine@nasa.example', 'full_name': 'Katherine Johnson', 'company_name': 'NASA', 'country_code': 'US', 'plan': 'enterprise', 'mrr_cents': 249900, 'signed_up_at': '2023-11-20'})"
  ],
  "broken": [
   {
    "query_id": "q_web_signup",
    "service": "web",
    "criticality": "critical",
    "label": "signup insert",
    "error": "IntegrityError: NOT NULL constraint failed: customers.billing_email",
    "sql": "INSERT INTO customers (email, full_name, signed_up_at) VALUES ('new@corp.example','New Person','2026-02-01')"
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
     "company_name",
     "country_code",
     "plan",
     "mrr_cents",
     "signed_up_at",
     "billing_email"
    ],
   
```

## Agent: risk_officer

**Goal** Add lock, volume and intent hazards that execution cannot observe, weight every hazard by table size and past incidents, then issue a verdict.

<details><summary>inputs</summary>

```json
{
 "case": "case_04_not_null_without_default",
 "row_estimates": {
  "customers": 2400000,
  "subscriptions": 2600000,
  "invoices": 48000000,
  "invoice_lines": 190000000,
  "usage_events": 900000000
 },
 "inherited_hazards": [
  "BREAKING_QUERY",
  "NOT_NULL_NO_DEFAULT",
  "NOT_NULL_NO_DEFAULT",
  "NOT_NULL_NO_DEFAULT",
  "NOT_NULL_NO_DEFAULT"
 ]
}
```

</details>

**tool** `memory.escalation` (0.0 ms)

```json
{
 "args": {
  "hazard_code": "BREAKING_QUERY",
  "table": "q_web_signup"
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
  "hazard_code": "NOT_NULL_NO_DEFAULT",
  "table": "customers"
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

**tool** `coverage.ledger` (0.1 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "add_column",
    "table": "customers",
    "column": "billing_email",
    "detail": {
     "type": "TEXT",
     "not_null": true,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL",
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
    "sql": "SELECT * FROM customer_billing_s
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

**model** `scripted-v1` tag=`hazard_narrative` tokens=470/86 cost=$0.0

> Live query breaks after migration. A statement the application issues today fails against the post-migration schema. Evidence: shadow replay: `INSERT INTO customers (email, full_name, signed_up_at) VALUES ('new@corp.example','New Person','2026-02-01')` -> IntegrityError: NOT NULL constraint failed: customers.billing_email Owning service(s): web.

**model** `scripted-v1` tag=`hazard_narrative` tokens=654/84 cost=$0.0

> NOT NULL added without a usable default. Existing rows or in-flight inserts violate the constraint immediately. Evidence: shadow backfill: backfill customers: NOT NULL constraint failed: customers.billing_email (row={'id': 1, 'email': 'ada@corp.example', 'full_name': 'Ada Lovelace', 'company_name': 'Corp', 'country_code': 'US', 'plan': '

**model** `scripted-v1` tag=`hazard_narrative` tokens=424/56 cost=$0.0

> Impact lands on a service owned by another team. The fix needs a deploy the migration author does not control, so ordering must be agreed first. Evidence: corpus ownership of failing statements: ['web'] Owning service(s): web.

**result**

```json
{
 "verdict": "BLOCK",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 1,
  "blocker": 2
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
   "code": "NOT_NULL_NO_DEFAULT",
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
 "case": "case_04_not_null_without_default",
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
  "NOT_NULL_NO_DEFAULT"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=490/42 cost=$0.0

> - Which deploy lands first: the query change or the schema change?
> - Has the owning team agreed to the deploy order?
> - What is the accepted risk for NOT_NULL_NO_DEFAULT?

**result**

```json
{
 "attempt": 1,
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
 "case": "case_04_not_null_without_default",
 "attempt": 1,
 "phase1_statements": 1
}
```

</details>

**tool** `migration.parse` (0.05 ms)

```json
{
 "args": {
  "sql": "ALTER TABLE \"customers\" ADD COLUMN \"billing_email\" TEXT;"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "add_column",
  "table": "customers",
  "column": "billing_email",
  "detail": {
   "type": "TEXT",
   "not_null": false,
   "default": null,
   "unique": false
  },
  "sql": "ALTER TABLE \"customers\" ADD COLUMN \"billing_email\" TEXT",
  "index": 0
 }
]
```

**tool** `schema.apply_ops` (0.04 ms)

```json
{
 "args": {
  "schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "customers",
    "column": "billing_email",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"customers\" ADD COLUMN \"billing_email\" TEXT",
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

**tool** `shadow.replay` (2.0 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "add_column",
    "table": "customers",
    "column": "billing_email",
    "detail": {
     "type": "TEXT",
     "not_null": false,
     "default": null,
     "unique": false
    },
    "sql": "ALTER TABLE \"customers\" ADD COLUMN \"billing_email\" TEXT",
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
    
```

_tool responded_

```json
{
 "materialised": true,
 "schema_errors": [],
 "data_errors": [],
 "broken": [],
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
    "company_name",
    "country_code",
    "plan",
    "mrr_cents",
    "signed_up_at",
    "...+1 more"
   ],
   "removed": [],
   "added": [
    "billing_email"
   ],
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
    "company_name",
    "country_code",
    "plan",
    "mrr_cents",
    "signed_up_at",
    "...+1 more"
   ],
   "removed": [],
   "added": [
    "billing_email"
   ],
   "sql": "SELECT * FROM \"customer_billing_summary\" LIMIT 1"
  }
 ],
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
     "company_name",
     "country_code",
     "plan",
     "mrr_cents",
     "signed_up_at",
     "billing_email"
    ],
    "removed": [],
    "added": [
     "billing_email"
    ],
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
     "company_name",
     "country_code",
     "plan",
     "mrr_cents",
     "signed_up_at",
     "billing_email"
    ],
    "removed": [],
    "added": [
     "billing_email"
    ],
    "sql": "SELECT * FROM \"customer_billing_summary\" LIMIT 1"
   }
  ],
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

> Do not ship this as written. 1 statement(s) the application issues today fail against the post-migration schema in shadow replay. 2 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
