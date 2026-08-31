# Trajectory - rt2_02_do_block_hides_the_drop

- run id: `eval-rt2_02_do_block_hides_the_drop`
- case: `rt2_02_do_block_hides_the_drop`
- events: 30

## Agent: cartographer

**Goal** Convert the current schema DDL and the proposed migration into an exact, machine-checkable change set. Facts only, no risk opinions.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_02_do_block_hides_the_drop",
 "migration_statements": 3,
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

**tool** `schema.parse` (0.86 ms)

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

**tool** `migration.parse` (0.08 ms)

```json
{
 "args": {
  "sql": "DO $$\nBEGIN\n  IF EXISTS (SELECT 1 FROM information_schema.columns\n             WHERE table_name = 'invoices' AND column_name = 'tax_rate')\n  THEN\n    ALTER TABLE invoices DROP COLUMN tax_rate;\n  END IF;\nEND\n$$;\n"
 }
}
```

_tool responded_

```json
[
 {
  "kind": "procedural_block",
  "table": null,
  "column": null,
  "detail": {
   "head": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name",
   "bodies": [
    "$$"
   ]
  },
  "sql": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'tax_rat...",
  "index": 0
 }
]
```

**tool** `migration.audit` (0.29 ms)

```json
{
 "args": {
  "migration_sql": "DO $$\nBEGIN\n  IF EXISTS (SELECT 1 FROM information_schema.columns\n             WHERE table_name = 'invoices' AND column_name = 'tax_rate')\n  THEN\n    ALTER TABLE invoices DROP COLUMN tax_rate;\n  END IF;\nEND\n$$;\n",
  "ops": [
   {
    "kind": "procedural_block",
    "table": null,
    "column": null,
    "detail": {
     "head": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name",
     "bodies": [
      "$$"
     ]
    },
    "sql": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'tax_rat...",
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
 "procedural": [
  {
   "statement_index": 0,
   "tag": "$$",
   "head": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns W",
   "start": 3,
   "end": 209,
   "body_statements": 3,
   "inner": [
    {
     "excerpt": "ALTER TABLE invoices DROP COLUMN tax_rate",
     "keyword": "alter table",
     "text": "BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'tax_rate') TH...",
     "control_flow": false,
     "ddl_or_dml": true,
     "destructive": true
    },
    {
     "excerpt": "END IF",
     "keyword": "end",
     "text": "END IF",
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
   "ddl_inside": [
    "ALTER TABLE invoices DROP COLUMN tax_rate"
   ],
   "destructive_inside": [
    "ALTER TABLE invoices DROP COLUMN tax_rate"
   ]
  }
 ],
 "conservation": {
  "significant_chars": 157,
  "attributed_chars": 157,
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
    "kind": "procedural_block",
    "table": null,
    "column": null,
    "detail": {
     "head": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name",
     "bodies": [
      "$$"
     ]
    },
    "sql": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'tax_rat...",
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
 [
  "op 0 (procedural_block) not modelled structurally: DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.colu"
 ]
]
```

_note (cartographer)_: parse conservation: the scanner finds 1 statement(s) in this file and the parse produced 1 operation(s); 0 unterminated construct(s), 0 statement(s) no operation accounts for, 1 procedural body/bodies. Reported as findings or declared gaps rather than reviewed as a smaller migration.

_note (cartographer)_: Some statements could not be modelled structurally; they are passed to the risk officer as unknowns rather than silently assumed safe.

**result**

```json
{
 "op_kinds": [
  "procedural_block"
 ],
 "tables_touched": [],
 "unmodelled": [
  "op 0 (procedural_block) not modelled structurally: DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.colu"
 ]
}
```

## Agent: blast_radius

**Goal** Enumerate every application statement that depends on the touched objects and reproduce the failures in a shadow database before anyone deploys anything.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_02_do_block_hides_the_drop",
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

**tool** `corpus.dependents` (0.12 ms)

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
[]
```

**tool** `corpus.blast_score` (0.0 ms)

```json
{
 "args": {
  "hits": []
 }
}
```

_tool responded_

```json
0
```

**tool** `shadow.replay` (2.94 ms)

```json
{
 "args": {
  "pre_schema": "Schema",
  "post_schema": "Schema",
  "ops": [
   {
    "kind": "procedural_block",
    "table": null,
    "column": null,
    "detail": {
     "head": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name",
     "bodies": [
      "$$"
     ]
    },
    "sql": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'tax_rat...",
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
 "dependent_queries": 0,
 "blast_score": 0,
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
 "case": "rt2_02_do_block_hides_the_drop",
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
  "hazard_code": "PROCEDURAL_DDL_UNREVIEWED",
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
    "kind": "procedural_block",
    "table": null,
    "column": null,
    "detail": {
     "head": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name",
     "bodies": [
      "$$"
     ]
    },
    "sql": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'tax_rat...",
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
    "criticalit
```

_tool responded_

```json
{
 "gaps": [
  {
   "kind": "procedural_body",
   "object": "$$ body at statement 0",
   "object_inferred": false,
   "statement_index": 0,
   "statement": "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns W",
   "why": "the body holds 3 scanned statement(s) and nothing in this pipeline models a procedural block: the census below is a keyw...",
   "closes_with": "a reviewer reads the $$ body of statement 0 in full, including every branch, before phase 1",
   "irreversible": true
  }
 ],
 "gap_kinds": [
  "procedural_body"
 ],
 "irreversible": [
  "$$ body at statement 0"
 ],
 "corpus_statements": 17,
 "parser_notes": [
  "op 0 (procedural_block) not modelled structurally: DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.colu"
 ]
}
```

**model** `scripted-v1` tag=`hazard_narrative` tokens=517/92 cost=$0.0

> Schema change executes inside a procedural body. DDL inside DO or a function body runs on deploy but is invisible to the expand/contract analysis, the dependency map and the shadow replay, so the packet would otherwise certify a migration whose schema change it never modelled. Evidence: statement 0: `DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns W`

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
  "procedural_body:$$ body at statement 0"
 ],
 "verdict_capped_by_coverage": false,
 "hazards": [
  {
   "code": "PROCEDURAL_DDL_UNREVIEWED",
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
 "case": "rt2_02_do_block_hides_the_drop",
 "attempt": 1,
 "policy": {
  "include_view_changes": true,
  "expand_contract_type_change": true,
  "minimal_phase1": false,
  "notes": []
 },
 "hazard_codes": [
  "PROCEDURAL_DDL_UNREVIEWED"
 ]
}
```

</details>

**model** `scripted-v1` tag=`reviewer_questions` tokens=479/14 cost=$0.0

> - What is the accepted risk for PROCEDURAL_DDL_UNREVIEWED?

**result**

```json
{
 "attempt": 1,
 "phase1_statements": 0,
 "phase2_statements": 0,
 "human_gates": 2
}
```

## Agent: verifier

**Goal** Prove that phase 1 of the plan breaks nothing the application does today, or hand back the exact failure that stops it.

<details><summary>inputs</summary>

```json
{
 "case": "rt2_02_do_block_hides_the_drop",
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

**tool** `schema.apply_ops` (0.05 ms)

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

**tool** `shadow.replay` (2.94 ms)

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

**tool** `plan.audit` (0.19 ms)

```json
{
 "args": {
  "plan": {
   "attempt": 1,
   "phase1_sql": [],
   "phase2_sql": [],
   "rollback_sql": [],
   "code_steps": [],
   "human_gates": [
    "statement 0 (procedural_block) is outside the tool's model and needs manual review: DO $$ BEGIN IF EXISTS (SELECT 1 FROM...",
    "IRREVERSIBLE - coverage gap on `$$ body at statement 0` (procedural_body): a reviewer reads the $$ body of statement 0 i..."
   ],
   "questions": [
    "What is the accepted risk for PROCEDURAL_DDL_UNREVIEWED?"
   ],
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
    "
```

_tool responded_

```json
{
 "statements_audited": 0,
 "scripts": {
  "phase1": 0,
  "phase2": 0,
  "rollback": 0
 },
 "findings": [],
 "finding_codes": [],
 "gaps": [],
 "gap_kinds": [],
 "kind_inventory": [],
 "gates_trusted": 0,
 "replay": {
  "ran": true,
  "scripts": {},
  "note": "the generated phase 2 is expected to break today's statements - that is what the code steps are for. The number is publi..."
 },
 "clean": true
}
```

**model** `scripted-v1` tag=`executive_summary` tokens=38/53 cost=$0.0

> Do not ship this as written. 1 coverage gap(s) need a named sign-off before this can be called safe. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

### Human checkpoint - narrator provenance: **HEADLINE FROM TOOLS**

The sentence above the badge was rendered from the tool output. The model cannot write it in this build, so a lie in wording the guard has never seen cannot become the verdict sentence. The model's prose is printed below the evidence, labelled unverified.

### Human checkpoint - pre-execution approval: **REQUIRED**

Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
