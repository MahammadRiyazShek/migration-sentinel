"""Generate the 9 HELD-OUT cases: a second schema the pipeline has never seen.

SUPERVISOR LOG (v9) - THE FINDINGS THIS FILE EXISTS TO ACT ON
-------------------------------------------------------------
Three hidden assumptions in v5, in the order they hurt:

  A1  "recall 0.970 means the pipeline finds hazards."  It means the pipeline
      finds hazards *in the 12 cases whose ground truth I wrote while looking at
      the rules*.  Nine arms of ablation and 180 hostile-model reviews all vary
      the scaffolding; not one of them varies the data.  No published number in
      v5 could tell "this pipeline works" apart from "these rules memorised
      twelve migrations against one billing schema".
  A2  "the coverage ledger names what the review could not see."  It names four
      gap classes, and those four were derived from the same twelve cases.  The
      perimeter of the honesty layer was itself unaudited.
  A3  "unsafe approvals is the primary metric."  It counts APPROVE and SAFE.
      A packet that prints "shippable, but only as the staged plan below" over a
      migration that will fail in production scores zero on it.

Two radically different ways to attack A1/A2 were considered:

  V1  A held-out world: a second schema, a second corpus, new hazard shapes, new
      labels, written after hashing the decision code, run once with no rule
      edits allowed.  Directly measures out-of-sample behaviour; costs one
      authored world; only as strong as the freeze evidence.
  V2  A metamorphic fuzzer: mutate the 12 migrations mechanically (reorder,
      insert no-ops, rename identifiers, scale row estimates) and assert
      invariants instead of labels - a verdict must never get *safer* when a
      statement is added.  Needs no ground truth at all and scales to thousands
      of inputs, but it can only find inconsistency, never a missed hazard
      class, so it cannot answer A2.

V1 shipped, because A2 is the claim this project is actually built on and only
new hazard shapes can test it.  V2's central invariant is kept as a cheap test
(`tests/test_all.py::TestHoldoutInvariants`) rather than a whole harness.

RULES OF THIS FILE, so the word "held-out" means something
---------------------------------------------------------
  * `tools/freeze_attest.py --freeze` hashed every file under `sentinel/` before
    this schema, these corpora and these labels existed.  Every held-out report
    prints the freeze state, and `results/holdout/frozen_run.json` is the run
    made while it still read CLEAN.
  * Ground truth here is written from PostgreSQL semantics and this second team's
    risk policy, not from anything the pipeline printed.
  * `holdout_06` carries a hazard code that is deliberately NOT in the shared
    vocabulary (`TRIGGER_WRITE_AMPLIFICATION`).  A held-out set whose labels all
    fit the vocabulary tests the rules and quietly exempts the vocabulary, which
    is exactly the mistake A2 warns about.  Every held-out recall figure is
    therefore published twice: with it, and excluding the hazard no arm can name.
  * `memory/incidents.jsonl` is not extended to this world.  The incident log
    belongs to the billing team; a second team's tables have no incident history,
    and the honest out-of-sample value of a memory layer is whatever that is.

Run:  python3 eval/build_holdout.py
"""
from __future__ import annotations

import json
import pathlib

OUT = pathlib.Path(__file__).parent / "holdout"

# A regional freight/logistics platform. Deliberately unlike the billing world:
# composite natural keys, a JSONB column, NUMERIC precision on money, a
# self-referencing shipment tree, write paths in the corpus (not just reads), a
# table with no corpus coverage at all, and one view per read pattern.
SCHEMA = """
CREATE TABLE carriers (
  id SERIAL PRIMARY KEY,
  code TEXT NOT NULL,
  legal_name TEXT NOT NULL,
  region TEXT NOT NULL DEFAULT 'emea',
  active INTEGER NOT NULL DEFAULT 1,
  onboarded_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE vehicles (
  id SERIAL PRIMARY KEY,
  carrier_id INTEGER NOT NULL,
  plate TEXT NOT NULL,
  capacity_kg INTEGER NOT NULL DEFAULT 0,
  refrigerated INTEGER NOT NULL DEFAULT 0,
  last_service_on TEXT,
  CONSTRAINT vehicles_capacity_chk CHECK (capacity_kg >= 0)
);

CREATE TABLE drivers (
  id SERIAL PRIMARY KEY,
  carrier_id INTEGER NOT NULL,
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  licence_class TEXT NOT NULL DEFAULT 'C',
  employment_type TEXT NOT NULL DEFAULT 'contract',
  hired_on TEXT NOT NULL
);

CREATE TABLE shipments (
  id SERIAL PRIMARY KEY,
  carrier_id INTEGER NOT NULL,
  vehicle_id INTEGER,
  parent_shipment_id INTEGER,
  reference TEXT NOT NULL,
  legacy_ref TEXT,
  status TEXT NOT NULL DEFAULT 'planned',
  weight_kg INTEGER NOT NULL DEFAULT 0,
  promised_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  CONSTRAINT shipments_status_chk CHECK (status IN ('planned','in_transit','delivered','cancelled'))
);

CREATE TABLE shipment_stops (
  id SERIAL PRIMARY KEY,
  shipment_id INTEGER NOT NULL,
  sequence_no INTEGER NOT NULL,
  kind TEXT NOT NULL DEFAULT 'delivery',
  status TEXT NOT NULL DEFAULT 'pending',
  address_json JSONB,
  arrived_at TIMESTAMPTZ
);

CREATE TABLE carrier_invoices (
  id SERIAL PRIMARY KEY,
  carrier_id INTEGER NOT NULL,
  invoice_number TEXT NOT NULL,
  shipment_id INTEGER,
  amount NUMERIC(12,2) NOT NULL,
  currency TEXT NOT NULL DEFAULT 'eur',
  status TEXT NOT NULL DEFAULT 'received',
  received_on TEXT NOT NULL
);

CREATE TABLE geofence_events (
  id SERIAL PRIMARY KEY,
  shipment_id INTEGER NOT NULL,
  vehicle_id INTEGER,
  event_kind TEXT NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL
);

CREATE VIEW driver_roster AS SELECT * FROM drivers;

CREATE VIEW active_shipments AS
  SELECT id, carrier_id, reference, status, promised_at
  FROM shipments WHERE status IN ('planned','in_transit');

CREATE INDEX idx_shipments_carrier ON shipments (carrier_id);

CREATE INDEX idx_stops_shipment ON shipment_stops (shipment_id);
"""

ROWS = {
    "carriers": 4_200,
    "vehicles": 21_000,
    "drivers": 48_000,
    "shipments": 62_000_000,
    "shipment_stops": 310_000_000,
    "carrier_invoices": 9_400_000,
    "geofence_events": 1_200_000_000,
}

Q = [
    ("q_dispatch_create", "dispatch-api", "critical", "shipment creation",
     "INSERT INTO shipments (carrier_id, reference, status, weight_kg, promised_at) "
     "VALUES (7,'SHP-77001','planned',1200,'2026-03-02')"),
    ("q_dispatch_board", "dispatch-api", "critical", "dispatch board",
     "SELECT id, reference, status, promised_at FROM shipments WHERE status = 'in_transit'"),
    ("q_dispatch_stop_progress", "dispatch-api", "high", "mark a stop arrived",
     "UPDATE shipment_stops SET status = 'arrived' WHERE id = 1"),
    ("q_portal_track", "customer-portal", "critical", "public tracking page",
     "SELECT reference, status, promised_at, delivered_at FROM shipments "
     "WHERE reference = 'SHP-10001'"),
    ("q_ops_active", "ops-console", "high", "active shipment list",
     "SELECT * FROM active_shipments"),
    ("q_ops_vehicles", "ops-console", "medium", "fleet panel",
     "SELECT id, plate, capacity_kg, refrigerated FROM vehicles WHERE carrier_id = 7"),
    ("q_ops_carriers", "ops-console", "low", "carrier directory",
     "SELECT code, legal_name, region FROM carriers WHERE active = 1"),
    ("q_driver_stop_list", "driver-app", "critical", "today's stop list",
     "SELECT id, sequence_no, kind, status FROM shipment_stops WHERE shipment_id = 1 "
     "ORDER BY sequence_no"),
    ("q_driver_stop_arrive", "driver-app", "critical", "driver marks arrival",
     "INSERT INTO shipment_stops (shipment_id, sequence_no, kind, status, arrived_at) "
     "VALUES (1,4,'delivery','arrived','2026-03-02')"),
    ("q_driver_profile", "driver-app", "high", "driver profile in the app",
     "SELECT id, full_name, phone, licence_class FROM drivers WHERE id = 1"),
    ("q_etl_driver_roster", "bi-etl", "high", "warehouse load of the driver roster",
     "SELECT * FROM driver_roster"),
    ("q_etl_volume", "bi-etl", "medium", "shipment volume by status",
     "SELECT status, COUNT(*) AS n FROM shipments GROUP BY status"),
    ("q_finance_totals", "finance-ops", "high", "carrier spend rollup",
     "SELECT carrier_id, SUM(amount) AS total FROM carrier_invoices GROUP BY carrier_id"),
    ("q_finance_lookup", "finance-ops", "medium", "invoice lookup",
     "SELECT invoice_number, amount, currency, status FROM carrier_invoices WHERE carrier_id = 7"),
    ("q_telemetry_write", "telemetry-worker", "high", "geofence event ingest",
     "INSERT INTO geofence_events (shipment_id, vehicle_id, event_kind, recorded_at) "
     "VALUES (1,1,'depart','2026-03-02')"),
]

QUERIES = [{"id": qid, "service": svc, "criticality": crit, "label": label, "sql": sql}
           for qid, svc, crit, label, sql in Q]

SEED = {
    "carriers": [
        {"id": 7, "code": "NRDX", "legal_name": "Nordex Freight BV", "region": "emea",
         "active": 1, "onboarded_at": "2022-04-11"},
        {"id": 8, "code": "MRLN", "legal_name": "Merlin Road Ltd", "region": "emea",
         "active": 1, "onboarded_at": "2023-08-02"},
        {"id": 9, "code": "ATLS", "legal_name": "Atlas Logistica SA", "region": "latam",
         "active": 0, "onboarded_at": "2021-01-19"},
    ],
    "vehicles": [
        {"id": 1, "carrier_id": 7, "plate": "NL-14-BXR", "capacity_kg": 18000,
         "refrigerated": 1, "last_service_on": "2026-01-08"},
        {"id": 2, "carrier_id": 7, "plate": "NL-22-QQT", "capacity_kg": 7500,
         "refrigerated": 0, "last_service_on": "2025-11-30"},
        {"id": 3, "carrier_id": 8, "plate": "DE-91-KLM", "capacity_kg": 24000,
         "refrigerated": 0, "last_service_on": None},
    ],
    "drivers": [
        {"id": 1, "carrier_id": 7, "full_name": "Ines Duarte", "phone": "+31201234567",
         "licence_class": "CE", "employment_type": "employee", "hired_on": "2021-06-01"},
        {"id": 2, "carrier_id": 7, "full_name": "Tomas Bauer", "phone": "+4930123456",
         "licence_class": "C", "employment_type": "contract", "hired_on": "2024-02-17"},
        {"id": 3, "carrier_id": 8, "full_name": "Aiko Tanaka", "phone": "+819012345678",
         "licence_class": "CE", "employment_type": "agency", "hired_on": "2023-09-05"},
        {"id": 4, "carrier_id": 9, "full_name": "Rafael Souza", "phone": "+5511998877665",
         "licence_class": "C", "employment_type": "contract", "hired_on": "2020-03-23"},
    ],
    "shipments": [
        {"id": 1, "carrier_id": 7, "vehicle_id": 1, "parent_shipment_id": None,
         "reference": "SHP-10001", "legacy_ref": "OLD-4471", "status": "in_transit",
         "weight_kg": 8200, "promised_at": "2026-03-02", "delivered_at": None},
        {"id": 2, "carrier_id": 7, "vehicle_id": 2, "parent_shipment_id": 1,
         "reference": "SHP-10002", "legacy_ref": None, "status": "planned",
         "weight_kg": 1400, "promised_at": "2026-03-03", "delivered_at": None},
        {"id": 3, "carrier_id": 8, "vehicle_id": 3, "parent_shipment_id": None,
         "reference": "SHP-10003", "legacy_ref": "OLD-4480", "status": "delivered",
         "weight_kg": 19750, "promised_at": "2026-02-25", "delivered_at": "2026-02-25"},
        {"id": 4, "carrier_id": 9, "vehicle_id": None, "parent_shipment_id": None,
         "reference": "SHP-10004", "legacy_ref": None, "status": "cancelled",
         "weight_kg": 0, "promised_at": "2026-02-20", "delivered_at": None},
    ],
    "shipment_stops": [
        {"id": 1, "shipment_id": 1, "sequence_no": 1, "kind": "pickup", "status": "arrived",
         "address_json": "{\"city\": \"Rotterdam\"}", "arrived_at": "2026-03-01"},
        {"id": 2, "shipment_id": 1, "sequence_no": 2, "kind": "delivery", "status": "pending",
         "address_json": "{\"city\": \"Utrecht\"}", "arrived_at": None},
        {"id": 3, "shipment_id": 1, "sequence_no": 3, "kind": "delivery", "status": "missed",
         "address_json": "{\"city\": \"Arnhem\"}", "arrived_at": None},
        {"id": 4, "shipment_id": 2, "sequence_no": 1, "kind": "pickup", "status": "pending",
         "address_json": "{\"city\": \"Antwerp\"}", "arrived_at": None},
        {"id": 5, "shipment_id": 3, "sequence_no": 1, "kind": "delivery", "status": "arrived",
         "address_json": None, "arrived_at": "2026-02-25"},
    ],
    "carrier_invoices": [
        {"id": 1, "carrier_id": 7, "invoice_number": "NRDX-2026-0041", "shipment_id": 1,
         "amount": 1250.00, "currency": "eur", "status": "received", "received_on": "2026-03-01"},
        {"id": 2, "carrier_id": 7, "invoice_number": "NRDX-2026-0042", "shipment_id": 2,
         "amount": 24500.00, "currency": "eur", "status": "approved", "received_on": "2026-03-02"},
        {"id": 3, "carrier_id": 8, "invoice_number": "MRLN-88", "shipment_id": 3,
         "amount": 9990.50, "currency": "gbp", "status": "paid", "received_on": "2026-02-26"},
        {"id": 4, "carrier_id": 8, "invoice_number": "MRLN-89", "shipment_id": None,
         "amount": 410.75, "currency": "gbp", "status": "received", "received_on": "2026-02-27"},
        {"id": 5, "carrier_id": 9, "invoice_number": "ATLS-0007", "shipment_id": None,
         "amount": 3300.00, "currency": "usd", "status": "disputed", "received_on": "2026-01-14"},
    ],
    "geofence_events": [
        {"id": 1, "shipment_id": 1, "vehicle_id": 1, "event_kind": "depart",
         "recorded_at": "2026-03-01"},
        {"id": 2, "shipment_id": 1, "vehicle_id": 1, "event_kind": "arrive",
         "recorded_at": "2026-03-01"},
    ],
}


def hz(code: str, severity: str, note: str) -> dict:
    return {"code": code, "severity": severity, "note": note}


CASES = [
    {
        "id": "holdout_01_service_level_not_null",
        "title": "Add shipments.service_level as NOT NULL",
        "owner_service": "dispatch-api",
        "scenario": "Product wants an explicit service tier on every shipment and the migration adds "
                    "the column with the constraint in one statement.",
        "migration_sql": "ALTER TABLE shipments ADD COLUMN service_level TEXT NOT NULL;\n",
        "rollback_sql": "ALTER TABLE shipments DROP COLUMN service_level;\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("NOT_NULL_NO_DEFAULT", "blocker", "62M existing shipments have no value"),
                hz("BREAKING_QUERY", "blocker",
                   "the dispatch-api INSERT does not supply the new column"),
            ],
            "notes": "Same failure shape as the in-sample case_04, on a different schema. If the "
                     "pipeline is doing anything real, this must transfer.",
        },
    },
    {
        "id": "holdout_02_composite_unique_invoices",
        "title": "Enforce one invoice number per carrier",
        "owner_service": "finance-ops",
        "scenario": "Finance has been chasing duplicate carrier invoices for a quarter and adds the "
                    "constraint everyone assumes already holds.",
        "migration_sql": "CREATE UNIQUE INDEX idx_carrier_invoices_number "
                         "ON carrier_invoices (carrier_id, invoice_number);\n",
        "rollback_sql": "DROP INDEX CONCURRENTLY idx_carrier_invoices_number;\n",
        "seed_overrides": {"carrier_invoices": "duplicate_number"},
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("UNIQUE_VIOLATION_EXISTING_DATA", "blocker",
                   "carrier 8 has submitted MRLN-88 twice"),
                hz("INDEX_LOCK_NO_CONCURRENT", "blocker",
                   "9.4M rows, no CONCURRENTLY, and this is a write-heavy finance table"),
            ],
            "notes": "A composite natural key, which the in-sample set never contained: the "
                     "duplicate is only visible on the pair, not on either column alone.",
        },
    },
    {
        "id": "holdout_03_rename_table_behind_view",
        "title": "Rename shipment_stops to stops behind a compatibility view",
        "owner_service": "dispatch-api",
        "scenario": "A naming cleanup, shipped with a compatibility view so that nothing has to "
                    "change on the read side.",
        "migration_sql": """
ALTER TABLE shipment_stops RENAME TO stops;
CREATE VIEW shipment_stops AS
  SELECT id, shipment_id, sequence_no, kind, status, address_json, arrived_at FROM stops;
""",
        "rollback_sql": "",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("BREAKING_QUERY", "blocker",
                   "the driver app INSERTs into shipment_stops, and a view is not writable"),
                hz("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high", "the rename lands in a single deploy"),
                hz("CROSS_SERVICE_UNCOORDINATED", "high",
                   "the driver app is released through the app stores, not by this team"),
                hz("MISSING_ROLLBACK", "medium", "no rollback supplied"),
            ],
            "notes": "The compatibility view is the trap and it is a new one: reads keep working, so "
                     "every SELECT in review passes, and the write path is the thing that dies.",
        },
    },
    {
        "id": "holdout_04_safe_additive_language",
        "title": "Add drivers.preferred_language and index drivers.carrier_id concurrently",
        "owner_service": "dispatch-api",
        "scenario": "A careful engineer: nullable column, CONCURRENTLY on the index, rollback "
                    "shipped. This case exists to catch reviewers that cry wolf out of sample.",
        "migration_sql": """
ALTER TABLE drivers ADD COLUMN preferred_language TEXT;
CREATE INDEX CONCURRENTLY idx_drivers_carrier ON drivers (carrier_id);
""",
        "rollback_sql": """
DROP INDEX CONCURRENTLY idx_drivers_carrier;
ALTER TABLE drivers DROP COLUMN preferred_language;
""",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "notes": "Correct answer: no hazards. The warehouse ETL reads SELECT * off driver_roster "
                     "and does gain a column, which is a note and not a finding.",
        },
    },
    {
        "id": "holdout_05_drop_status_check",
        "title": "Drop the shipments status CHECK constraint",
        "owner_service": "dispatch-api",
        "scenario": "Operations need two new statuses this quarter and the constraint is in the way.",
        "migration_sql": "ALTER TABLE shipments DROP CONSTRAINT shipments_status_chk;\n",
        "rollback_sql": "ALTER TABLE shipments ADD CONSTRAINT shipments_status_chk "
                        "CHECK (status IN ('planned','in_transit','delivered','cancelled'));\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [
                hz("INTEGRITY_CONSTRAINT_REMOVED", "high",
                   "nothing breaks today; unvalidated statuses start accumulating, and the tracking "
                   "page renders whatever it is given"),
            ],
            "notes": "Intent-only hazard: execution can prove nothing here, out of sample either.",
        },
    },
    {
        "id": "holdout_06_audit_trigger",
        "title": "Add a stop-status audit trail with a row trigger",
        "owner_service": "dispatch-api",
        "scenario": "Compliance wants every stop status change recorded, so the migration adds an "
                    "audit table and an AFTER UPDATE trigger on a 310M-row table.",
        "migration_sql": """
CREATE TABLE stop_status_audit (
  id SERIAL PRIMARY KEY,
  stop_id INTEGER NOT NULL,
  old_status TEXT,
  new_status TEXT,
  changed_at TIMESTAMPTZ NOT NULL
);
CREATE TRIGGER trg_stop_status_audit AFTER UPDATE OF status ON shipment_stops
  FOR EACH ROW EXECUTE FUNCTION log_stop_status_change();
""",
        "rollback_sql": """
DROP TRIGGER trg_stop_status_audit ON shipment_stops;
DROP TABLE stop_status_audit;
""",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("TRIGGER_WRITE_AMPLIFICATION", "high",
                   "every UPDATE on a 310M-row table now writes a second row inside the same "
                   "transaction; the dispatch write path pays for it forever"),
            ],
            "notes": "The label no arm can name: this hazard code is deliberately outside the shared "
                     "vocabulary. The only honest thing the pipeline can do is refuse to certify a "
                     "statement it cannot model. Recall is published with and without this case.",
        },
    },
    {
        "id": "holdout_07_narrow_invoice_amount",
        "title": "Narrow carrier_invoices.amount to numeric(8,2)",
        "owner_service": "finance-ops",
        "scenario": "A modelling cleanup: nobody believes a single carrier invoice can exceed "
                    "999,999.99, and the fixture data agrees with them.",
        "migration_sql": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(8,2);\n",
        "rollback_sql": "ALTER TABLE carrier_invoices ALTER COLUMN amount TYPE numeric(12,2);\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("TYPE_NARROWING_DATA_LOSS", "blocker",
                   "annual haulage settlements above 1,000,000.00 exist in production and the "
                   "migration rejects them mid-flight; the rollback restores the type, never the "
                   "values"),
                hz("TABLE_REWRITE_LOCK", "high", "9.4M-row rewrite under an exclusive lock"),
            ],
            "notes": "The fixture is the world, again: the 5 seeded invoices are all small, so a "
                     "value scan over them finds nothing and says so with a straight face.",
        },
    },
    {
        "id": "holdout_08_release_train_fleet",
        "title": "Release train: six fleet changes in one migration",
        "owner_service": "dispatch-api",
        "scenario": "The hard case, second edition. A quarter of schema debt merged the day before a "
                    "peak week.",
        "migration_sql": """
ALTER TABLE drivers RENAME COLUMN phone TO phone_e164;
CREATE INDEX idx_geofence_events_shipment ON geofence_events (shipment_id);
ALTER TABLE shipments DROP COLUMN legacy_ref;
UPDATE shipment_stops SET status = 'skipped' WHERE status = 'missed';
ALTER TABLE carrier_invoices ADD CONSTRAINT carrier_invoices_shipment_fk
  FOREIGN KEY (shipment_id) REFERENCES shipments (id);
VACUUM FULL shipments;
""",
        "rollback_sql": "",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("BREAKING_QUERY", "blocker", "the driver app selects drivers.phone by name"),
                hz("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high",
                   "a rename and a drop, both single-step"),
                hz("SELECT_STAR_DRIFT", "high",
                   "the warehouse ETL reads SELECT * off driver_roster and the column is renamed "
                   "under it"),
                hz("INDEX_LOCK_NO_CONCURRENT", "blocker",
                   "1.2B-row geofence table, no CONCURRENTLY, on the ingest path"),
                hz("CONSTRAINT_VALIDATION_LOCK", "high",
                   "the foreign key validates 9.4M rows under a lock"),
                hz("UNBATCHED_BACKFILL", "high", "310M-row status flip in one statement"),
                hz("TABLE_REWRITE_LOCK", "high",
                   "VACUUM FULL rewrites shipments under an ACCESS EXCLUSIVE lock"),
                hz("CROSS_SERVICE_UNCOORDINATED", "high",
                   "driver-app and bi-etl are both other teams"),
                hz("MISSING_ROLLBACK", "medium", "no rollback supplied"),
            ],
            "notes": "Second-edition release train: same idea as case_12, none of the same "
                     "statements, and no incident log to lean on.",
        },
    },
    {
        "id": "holdout_09_drop_employment_type",
        "title": "Drop drivers.employment_type after the HR system took it over",
        "owner_service": "dispatch-api",
        "scenario": "The field moved to the HR system last quarter, so the column looks dead: nothing "
                    "in the application selects it by name.",
        "migration_sql": "ALTER TABLE drivers DROP COLUMN employment_type;\n",
        "rollback_sql": "",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("SELECT_STAR_DRIFT", "high",
                   "the warehouse ETL reads SELECT * off driver_roster and loses a column silently"),
                hz("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high", "single-step drop"),
                hz("CROSS_SERVICE_UNCOORDINATED", "high", "bi-etl is another team"),
                hz("MISSING_ROLLBACK", "medium",
                   "a dropped column cannot be restored from DDL alone"),
            ],
            "notes": "Nothing fails loudly. This is the failure mode that shows up three weeks later "
                     "in a report nobody trusts any more.",
        },
    },
]


def seed_for(case: dict) -> dict:
    seed = json.loads(json.dumps(SEED))
    if case.get("seed_overrides", {}).get("carrier_invoices") == "duplicate_number":
        # the duplicate finance has been chasing: same carrier, same invoice number
        seed["carrier_invoices"][3]["invoice_number"] = "MRLN-88"
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
    print(f"wrote {len(CASES)} held-out cases to {OUT}")


if __name__ == "__main__":
    main()
