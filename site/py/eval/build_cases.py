"""Generate the 12 evaluation cases.

The cases share one synthetic world - a mid-size SaaS billing product - so that
the query corpus, the row estimates and the incident log stay consistent across
cases.  Everything here is invented; there is no customer data anywhere in this
repository.

Ground truth was written from the PostgreSQL semantics of each change and this
team's declared risk policy (see memory/incidents.jsonl), BEFORE running the
pipeline, and deliberately includes two hazards the pipeline cannot see:
  * case_09 CROSS_SERVICE_UNCOORDINATED - the affected consumer is a dbt model
    that is not in the query corpus
  * case_12 TABLE_REWRITE_LOCK from CLUSTER - a statement the parser does not model
Those stay in as documented misses.  A benchmark you cannot fail is not a
benchmark.

Run:  python eval/build_cases.py
"""
from __future__ import annotations

import json
import pathlib

OUT = pathlib.Path(__file__).parent / "cases"

SCHEMA = """
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  full_name TEXT,
  company_name TEXT,
  country_code TEXT NOT NULL DEFAULT 'US',
  plan TEXT NOT NULL DEFAULT 'free',
  mrr_cents INTEGER NOT NULL DEFAULT 0,
  signed_up_at TIMESTAMPTZ NOT NULL,
  CONSTRAINT customers_plan_chk CHECK (plan IN ('free','team','business','enterprise'))
);

CREATE TABLE subscriptions (
  id SERIAL PRIMARY KEY,
  customer_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  seats INTEGER NOT NULL DEFAULT 1,
  price_cents INTEGER NOT NULL,
  started_on TEXT NOT NULL,
  canceled_on TEXT,
  CONSTRAINT subscriptions_seats_chk CHECK (seats > 0)
);

CREATE TABLE invoices (
  id SERIAL PRIMARY KEY,
  customer_id INTEGER NOT NULL,
  subscription_id INTEGER,
  invoice_number TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  tax_rate REAL,
  currency TEXT NOT NULL DEFAULT 'usd',
  status TEXT NOT NULL DEFAULT 'draft',
  issued_at TIMESTAMPTZ,
  paid_at TIMESTAMPTZ
);

CREATE TABLE invoice_lines (
  id SERIAL PRIMARY KEY,
  invoice_id INTEGER NOT NULL,
  description TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  unit_price_cents INTEGER NOT NULL
);

CREATE TABLE usage_events (
  id SERIAL PRIMARY KEY,
  customer_id INTEGER NOT NULL,
  event_name TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  occurred_at TIMESTAMPTZ NOT NULL
);

CREATE VIEW customer_billing_summary AS SELECT * FROM customers;

CREATE VIEW open_invoices AS
  SELECT id, customer_id, invoice_number, amount_cents, status
  FROM invoices WHERE status IN ('draft','open');

CREATE INDEX idx_invoices_customer ON invoices (customer_id);
"""

ROWS = {
    "customers": 2_400_000,
    "subscriptions": 2_600_000,
    "invoices": 48_000_000,
    "invoice_lines": 190_000_000,
    "usage_events": 900_000_000,
}

Q = [
    ("q_web_profile", "web", "critical", "customer profile page",
     "SELECT id, email, full_name, plan FROM customers WHERE id = 1"),
    ("q_web_signup", "web", "critical", "signup insert",
     "INSERT INTO customers (email, full_name, signed_up_at) VALUES ('new@corp.example','New Person','2026-02-01')"),
    ("q_support_lookup", "support-admin", "high", "support customer lookup",
     "SELECT id, email, company_name FROM customers WHERE email = 'ada@corp.example'"),
    ("q_bi_summary", "bi", "high", "dbt model stg_customers",
     "SELECT * FROM customer_billing_summary"),
    ("q_bi_mrr", "bi", "medium", "MRR by plan",
     "SELECT plan, SUM(mrr_cents) AS mrr FROM customers GROUP BY plan"),
    ("q_bi_country", "bi", "low", "customers by country",
     "SELECT country_code, COUNT(*) AS n FROM customers GROUP BY country_code"),
    ("q_billing_invoice_create", "billing-api", "critical", "invoice creation",
     "INSERT INTO invoices (customer_id, invoice_number, amount_cents, issued_at) "
     "VALUES (1,'INV-9001',1000,'2026-02-01')"),
    ("q_billing_tax", "billing-api", "high", "invoice tax display",
     "SELECT invoice_number, amount_cents, tax_rate FROM invoices WHERE id = 1"),
    ("q_billing_currency", "billing-api", "medium", "currency rollup",
     "SELECT currency, COUNT(*) AS n FROM invoices GROUP BY currency"),
    ("q_dunning_open", "dunning-worker", "critical", "open invoice sweep",
     "SELECT * FROM open_invoices"),
    ("q_mobile_seats", "mobile-api", "high", "seat count for the app",
     "SELECT id, seats, status FROM subscriptions WHERE customer_id = 1"),
    ("q_web_line_items", "web", "high", "invoice line items",
     "SELECT description, quantity, unit_price_cents FROM invoice_lines WHERE invoice_id = 1"),
    ("q_analytics_usage", "bi", "medium", "usage rollup",
     "SELECT event_name, SUM(quantity) AS q FROM usage_events GROUP BY event_name"),
    ("q_billing_status_update", "billing-api", "high", "mark invoice open",
     "UPDATE invoices SET status = 'open' WHERE id = 1"),
]

QUERIES = [{"id": qid, "service": svc, "criticality": crit, "label": label, "sql": sql}
           for qid, svc, crit, label, sql in Q]

SEED = {
    "customers": [
        {"id": 1, "email": "ada@corp.example", "full_name": "Ada Lovelace", "company_name": "Corp",
         "country_code": "US", "plan": "business", "mrr_cents": 49900, "signed_up_at": "2024-01-04"},
        {"id": 2, "email": "grace@corp.example", "full_name": "Grace Hopper", "company_name": "Corp",
         "country_code": "USA", "plan": "team", "mrr_cents": 9900, "signed_up_at": "2024-03-11"},
        {"id": 3, "email": "alan@lab.example", "full_name": "Alan Turing", "company_name": None,
         "country_code": "GB", "plan": "free", "mrr_cents": 0, "signed_up_at": "2025-06-02"},
        {"id": 4, "email": "katherine@nasa.example", "full_name": "Katherine Johnson",
         "company_name": "NASA", "country_code": "US", "plan": "enterprise", "mrr_cents": 249900,
         "signed_up_at": "2023-11-20"},
    ],
    "subscriptions": [
        {"id": 1, "customer_id": 1, "status": "active", "seats": 12, "price_cents": 49900,
         "started_on": "2024-01-04", "canceled_on": None},
        {"id": 2, "customer_id": 1, "status": "canceled", "seats": 3, "price_cents": 9900,
         "started_on": "2023-02-01", "canceled_on": "2024-01-03"},
        {"id": 3, "customer_id": 4, "status": "active", "seats": 400, "price_cents": 249900,
         "started_on": "2023-11-20", "canceled_on": None},
    ],
    "invoices": [
        {"id": 1, "customer_id": 1, "subscription_id": 1, "invoice_number": "INV-1001",
         "amount_cents": 49900, "tax_rate": 0.2, "currency": "usd", "status": "open",
         "issued_at": "2026-01-01", "paid_at": None},
        {"id": 2, "customer_id": 4, "subscription_id": 3, "invoice_number": "INV-1002",
         "amount_cents": 249900, "tax_rate": 0.0, "currency": "usd", "status": "paid",
         "issued_at": "2026-01-01", "paid_at": "2026-01-05"},
        {"id": 3, "customer_id": 1, "subscription_id": 1, "invoice_number": "INV-1003",
         "amount_cents": 1200, "tax_rate": None, "currency": "eur", "status": "draft",
         "issued_at": None, "paid_at": None},
    ],
    "invoice_lines": [
        {"id": 1, "invoice_id": 1, "description": "Business plan", "quantity": 12,
         "unit_price_cents": 4158},
        {"id": 2, "invoice_id": 2, "description": "Enterprise plan", "quantity": 400,
         "unit_price_cents": 624},
    ],
    "usage_events": [
        {"id": 1, "customer_id": 1, "event_name": "api_call", "quantity": 900,
         "occurred_at": "2026-01-30"},
        {"id": 2, "customer_id": 4, "event_name": "seat_active", "quantity": 400,
         "occurred_at": "2026-01-30"},
    ],
}


def hz(code: str, severity: str, note: str) -> dict:
    return {"code": code, "severity": severity, "note": note}


CASES: list[dict] = [
    {
        "id": "case_01_rename_with_compat_view",
        "title": "Rename customers.full_name to name and refresh the BI view",
        "owner_service": "web",
        "scenario": "A product engineer standardises the column name and updates the reporting view "
                    "in the same migration, believing the view keeps everything else working.",
        "migration_sql": """
ALTER TABLE customers RENAME COLUMN full_name TO name;
CREATE OR REPLACE VIEW customer_billing_summary AS
  SELECT id, email, name, company_name, country_code, plan, mrr_cents, signed_up_at FROM customers;
""",
        "rollback_sql": "",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("BREAKING_QUERY", "blocker", "q_web_profile still selects full_name"),
                hz("SELECT_STAR_DRIFT", "high", "the dbt model reading the view loses full_name"),
                hz("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high", "rename lands in one deploy"),
                hz("CROSS_SERVICE_UNCOORDINATED", "high", "breakage lands in bi, owned by another team"),
                hz("MISSING_ROLLBACK", "medium", "no rollback supplied"),
            ],
            "notes": "The compatibility view is the trap: it makes the change look self-contained "
                     "while the application query and the BI column set both break.",
        },
    },
    {
        "id": "case_02_drop_column_still_read",
        "title": "Drop customers.company_name after the product decision to remove it",
        "owner_service": "web",
        "scenario": "The field was removed from the signup form last quarter, so it looks dead.",
        "migration_sql": "ALTER TABLE customers DROP COLUMN company_name;\n",
        "rollback_sql": "",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("BREAKING_QUERY", "blocker", "the support console still selects company_name"),
                hz("SELECT_STAR_DRIFT", "high", "the BI view loses a column"),
                hz("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high", "single-step drop"),
                hz("CROSS_SERVICE_UNCOORDINATED", "high", "support-admin and bi are other teams"),
                hz("MISSING_ROLLBACK", "medium", "a dropped column cannot be restored from DDL alone"),
            ],
            "notes": "Removed from the UI is not the same as unused.",
        },
    },
    {
        "id": "case_03_index_on_hot_table",
        "title": "Index invoices.status to speed up the dunning sweep",
        "owner_service": "billing-api",
        "scenario": "A slow query gets an index. The migration is one line and reviewers approve it "
                    "in seconds.",
        "migration_sql": "CREATE INDEX idx_invoices_status ON invoices (status);\n",
        "rollback_sql": "DROP INDEX CONCURRENTLY idx_invoices_status;\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("INDEX_LOCK_NO_CONCURRENT", "blocker",
                   "48M-row table, and this team has already had an outage from exactly this"),
            ],
            "notes": "Nothing breaks logically; the risk is entirely operational.",
        },
    },
    {
        "id": "case_04_not_null_without_default",
        "title": "Add customers.billing_email as NOT NULL",
        "owner_service": "billing-api",
        "scenario": "Billing wants a guaranteed address and adds the column with a NOT NULL "
                    "constraint in the same statement.",
        "migration_sql": "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL;\n",
        "rollback_sql": "ALTER TABLE customers DROP COLUMN billing_email;\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("NOT_NULL_NO_DEFAULT", "blocker", "2.4M existing rows have no value"),
                hz("BREAKING_QUERY", "blocker", "the signup INSERT does not supply the new column"),
            ],
            "notes": "Two different failures from one statement: the migration itself, and every "
                     "insert issued by code that does not know about the column yet.",
        },
    },
    {
        "id": "case_05_unique_email_with_duplicates",
        "title": "Enforce unique customer emails",
        "owner_service": "web",
        "scenario": "A long-standing data-quality ticket. The team assumes emails are already unique.",
        "migration_sql": "CREATE UNIQUE INDEX idx_customers_email ON customers (email);\n",
        "rollback_sql": "DROP INDEX CONCURRENTLY idx_customers_email;\n",
        "seed_overrides": {"customers": "duplicate_email"},
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("UNIQUE_VIOLATION_EXISTING_DATA", "blocker", "two customers share an email today"),
                hz("INDEX_LOCK_NO_CONCURRENT", "blocker", "2.4M rows, no CONCURRENTLY"),
            ],
            "notes": "The index build fails partway through and leaves the deploy half-applied.",
        },
    },
    {
        "id": "case_06_safe_unique_index",
        "title": "Add a concurrent unique index on invoices.invoice_number",
        "owner_service": "billing-api",
        "scenario": "A careful engineer already used CONCURRENTLY and shipped a rollback. This case "
                    "exists to catch reviewers that cry wolf.",
        "migration_sql": "CREATE UNIQUE INDEX CONCURRENTLY idx_invoices_number ON invoices (invoice_number);\n",
        "rollback_sql": "DROP INDEX CONCURRENTLY idx_invoices_number;\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "notes": "Correct answer: no hazards. Any finding here is a false alarm.",
        },
    },
    {
        "id": "case_07_drop_check_constraint",
        "title": "Drop the plan CHECK constraint to allow new plan names",
        "owner_service": "billing-api",
        "scenario": "Marketing invents a new plan tier and the constraint is in the way.",
        "migration_sql": "ALTER TABLE customers DROP CONSTRAINT customers_plan_chk;\n",
        "rollback_sql": "ALTER TABLE customers ADD CONSTRAINT customers_plan_chk "
                        "CHECK (plan IN ('free','team','business','enterprise'));\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [
                hz("INTEGRITY_CONSTRAINT_REMOVED", "high",
                   "nothing breaks today; unvalidated plan values start accumulating"),
            ],
            "notes": "Execution can prove nothing here. This hazard is purely about intent, which is "
                     "why the pipeline keeps a static intent layer next to the replay layer.",
        },
    },
    {
        "id": "case_08_narrowing_country_code",
        "title": "Narrow customers.country_code to varchar(2)",
        "owner_service": "web",
        "scenario": "A cleanup to enforce ISO-2 codes. Nobody checks what is in the column today.",
        "migration_sql": "ALTER TABLE customers ALTER COLUMN country_code TYPE varchar(2);\n",
        "rollback_sql": "ALTER TABLE customers ALTER COLUMN country_code TYPE text;\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("TYPE_NARROWING_DATA_LOSS", "blocker", "'USA' style values exist and get truncated"),
                hz("TABLE_REWRITE_LOCK", "high", "2.4M-row rewrite under an exclusive lock"),
            ],
            "notes": "The rollback DDL restores the type but not the truncated values.",
        },
    },
    {
        "id": "case_09_unbatched_backfill",
        "title": "Backfill invoices.currency and make it NOT NULL",
        "owner_service": "billing-api",
        "scenario": "A tidy-up migration written as two statements against a 48M-row table.",
        "migration_sql": """
UPDATE invoices SET currency = 'usd' WHERE currency IS NULL;
ALTER TABLE invoices ALTER COLUMN currency SET NOT NULL;
""",
        "rollback_sql": "ALTER TABLE invoices ALTER COLUMN currency DROP NOT NULL;\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [
                hz("UNBATCHED_BACKFILL", "high", "one statement over 48M rows"),
                hz("NOT_NULL_NO_DEFAULT", "high", "SET NOT NULL validates every row under a lock"),
                hz("CROSS_SERVICE_UNCOORDINATED", "high",
                   "a dbt model outside the query corpus reads currency IS NULL as 'legacy'"),
            ],
            "notes": "Known miss: the third hazard depends on a consumer that is not in the corpus, "
                     "so no amount of replay finds it. It stays in the ground truth on purpose.",
        },
    },
    {
        "id": "case_10_add_fk_constraint",
        "title": "Add the missing invoices -> customers foreign key",
        "owner_service": "billing-api",
        "scenario": "A data-integrity improvement everyone agrees with.",
        "migration_sql": "ALTER TABLE invoices ADD CONSTRAINT invoices_customer_fk "
                         "FOREIGN KEY (customer_id) REFERENCES customers (id);\n",
        "rollback_sql": "ALTER TABLE invoices DROP CONSTRAINT invoices_customer_fk;\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("CONSTRAINT_VALIDATION_LOCK", "blocker",
                   "validation scans 48M rows under a lock, and INC-2024-11 was exactly this"),
            ],
            "notes": "Severity is a blocker for this team specifically because of the incident log. "
                     "A reviewer without that memory calls it a high.",
        },
    },
    {
        "id": "case_11_swap_view_used_by_worker",
        "title": "Replace the open_invoices view with a v2 definition",
        "owner_service": "billing-api",
        "scenario": "The view is renamed as part of a modelling cleanup; the dunning worker is "
                    "maintained by another team.",
        "migration_sql": """
DROP VIEW open_invoices;
CREATE VIEW open_invoices_v2 AS
  SELECT id, customer_id, invoice_number, amount_cents, status, issued_at
  FROM invoices WHERE status IN ('draft','open');
""",
        "rollback_sql": "",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("BREAKING_QUERY", "blocker", "the dunning worker reads open_invoices every minute"),
                hz("CROSS_SERVICE_UNCOORDINATED", "high", "the worker is deployed by another team"),
                hz("MISSING_ROLLBACK", "medium", "no rollback supplied"),
            ],
            "notes": "A DROP VIEW is invisible to reviewers who scan for DROP TABLE and DROP COLUMN.",
        },
    },
    {
        "id": "case_12_release_train",
        "title": "Release train: six changes in one migration",
        "owner_service": "billing-api",
        "scenario": "The hard case. A sprint's worth of schema work merged as a single migration on "
                    "a Friday, with the usual explanation that each piece is small.",
        "migration_sql": """
ALTER TABLE subscriptions ADD COLUMN billing_interval TEXT NOT NULL DEFAULT 'monthly';
CREATE UNIQUE INDEX idx_subscriptions_customer ON subscriptions (customer_id);
ALTER TABLE invoices DROP COLUMN tax_rate;
CREATE INDEX idx_usage_events_name ON usage_events (event_name);
ALTER TABLE subscriptions DROP CONSTRAINT subscriptions_seats_chk;
UPDATE invoices SET status = 'open' WHERE status = 'draft';
CLUSTER invoices USING idx_invoices_customer;
""",
        "rollback_sql": "",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("UNIQUE_VIOLATION_EXISTING_DATA", "blocker",
                   "customer 1 has two subscription rows today"),
                hz("BREAKING_QUERY", "blocker", "the invoice tax display selects tax_rate"),
                hz("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high", "the tax_rate drop is single-step"),
                hz("INDEX_LOCK_NO_CONCURRENT", "blocker",
                   "900M-row usage_events index build with no CONCURRENTLY"),
                hz("INTEGRITY_CONSTRAINT_REMOVED", "high", "seats > 0 stops being enforced"),
                hz("UNBATCHED_BACKFILL", "high", "48M-row status flip in one statement"),
                hz("TABLE_REWRITE_LOCK", "high",
                   "CLUSTER rewrites invoices under an ACCESS EXCLUSIVE lock"),
                hz("MISSING_ROLLBACK", "medium", "no rollback supplied"),
            ],
            "notes": "Known miss: CLUSTER is outside the parser's model. The pipeline must at least "
                     "report it as an unmodelled statement instead of implying it is safe.",
        },
    },
]


def seed_for(case: dict) -> dict:
    seed = json.loads(json.dumps(SEED))
    if case.get("seed_overrides", {}).get("customers") == "duplicate_email":
        seed["customers"][2]["email"] = "ada@corp.example"  # the duplicate nobody knew about
    return seed


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        doc = {
            "id": case["id"],
            "title": case["title"],
            "owner_service": case["owner_service"],
            "scenario": case["scenario"],
            "schema_sql": SCHEMA.strip(),
            "row_estimates": ROWS,
            "queries": QUERIES,
            "seed": seed_for(case),
            "migration_sql": case["migration_sql"].strip() + "\n",
            "rollback_sql": case["rollback_sql"],
            "ground_truth": case["ground_truth"],
        }
        (OUT / f"{case['id']}.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {len(CASES)} cases to {OUT}")


if __name__ == "__main__":
    main()
