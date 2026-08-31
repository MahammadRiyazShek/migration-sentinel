# Trajectory - case_07_drop_check_constraint

- run id: `eval-case_07_drop_check_constraint`
- case: `case_07_drop_check_constraint`
- events: 27

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "case_07_drop_check_constraint",
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

**tool** `schema.parse` (0.6 ms)

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
  "sql": "ALTER TABLE customers DROP CONSTRAINT customers_plan_chk;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "drop_constraint",
  "table": "customers",
  "column": null,
  "detail": {
   "constraint": "customers_plan_chk"
  },
  "sql": "ALTER TABLE customers DROP CONSTRAINT customers_plan_chk",
  "index": 0
 }
]
```

**tool** `migration.audit` (0.03 ms)

```json
{
 "args": {
  "migration_sql": "ALTER TABLE customers DROP CONSTRAINT customers_plan_chk;\n",
  "ops": [
   {
    "kind": "drop_constraint",
    "table": "customers",
    "column": null,
    "detail": {
     "constraint": "customers_plan_chk"
    },
    "sql": "ALTER TABLE customers DROP CONSTRAINT customers_plan_chk",
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
  "significant_chars": 51,
  "attributed_chars": 51,
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
    "kind": "drop_constraint",
    "table": "customers",
    "column": null,
    "detail": {
     "constraint": "customers_plan_chk"
    },
    "sql": "ALTER TABLE customers DROP CONSTRAINT customers_plan_chk",
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
  "drop_constraint"
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
 "case": "case_07_drop_check_constraint",
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

**tool** `corpus.dependents` (0.11 ms)

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

**tool** `shadow.replay` (2.04 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "drop_constraint",
    "table": "customers",
    "column": null,
    "detail": {
     "constraint": "customers_plan_chk"
    },
    "sql": "ALTER TABLE customers DROP CONSTRAINT customers_plan_chk",
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
 "dependent_queries": 6,
 "blast_score": 17,
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
 "case": "case_07_drop_check_constraint",
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

**tool** `memory.escalation` (0.0 ms)

```json
{
 "args": {
  "hazard_code": "INTEGRITY_CONSTRAINT_REMOVED",
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

**tool** `coverage.ledger` (0.13 ms)

```json
{
 "args": {
  "ops": [
   {
    "kind": "drop_constraint",
    "table": "customers",
    "column": null,
    "detail": {
     "constraint": "customers_plan_chk"
    },
    "sql": "ALTER TABLE customers DROP CONSTRAINT customers_plan_chk",
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
    "service": "
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

**model** `scripted-v1` tag=`hazard_narrative` tokens=458/51 cost=$0.0

> Data-integrity constraint removed. Nothing breaks today; invalid rows start accumulating and are expensive to clean up later. Evidence: statement 0: `ALTER TABLE customers DROP CONSTRAINT customers_plan_chk`

**result**

```json
{
 "verdict": "SAFE_WITH_PLAN",
 "counts": {
  "low": 0,
  "medium": 0,
  "high": 1,
  "blocker": 0
 },
 "coverage_gaps": [],
 "verdict_capped_by_coverage": false,
 "hazards": [
  {
   "code": "INTEGRITY_CONSTRAINT_REMOVED",
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
 "case": "case_07_drop_check_constraint",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "INTEGRITY_CONSTRAINT_REMOVED"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=480/14 cost=$0.0

> - What enforces this invariant once the constraint is gone?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 0,
 "phase2_statements": 1,
 "human_gates": 1
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "case_07_drop_check_constraint",
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

**tool** `schema.apply_ops` (0.04 ms)

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

**tool** `shadow.replay` (1.96 ms)

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

**model** `scripted-v1` tag=`executive_summary` tokens=41/39 cost=$0.0

> Shippable, but only as the staged plan below. 0 blocker, 1 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
