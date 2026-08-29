"""Stdlib-only test suite:  python -m unittest discover -s tests -v"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sentinel import cli  # noqa: E402
from sentinel.llm import get_llm  # noqa: E402
from sentinel.orchestrator import review  # noqa: E402
from sentinel.tools import shadow_db, sql_parse  # noqa: E402
from sentinel.tools.incident_memory import IncidentMemory  # noqa: E402

CASES = ROOT / "eval" / "cases"
INCIDENTS = ROOT / "memory" / "incidents.jsonl"


def case(name: str) -> dict:
    return json.loads((CASES / f"{name}.json").read_text())


def run(name: str, **kwargs):
    return review(case(name), get_llm("scripted"), incidents_path=str(INCIDENTS),
                  learned_path=None, trace=True, run_id="test", **kwargs)


class TestParser(unittest.TestCase):
    def test_multiword_types_do_not_swallow_constraints(self):
        s = sql_parse.parse_schema(
            "CREATE TABLE t (a TIMESTAMPTZ NOT NULL, b character varying(10) UNIQUE, "
            "c double precision DEFAULT 1.5);")
        cols = s.tables["t"].columns
        self.assertEqual(cols["a"].type, "TIMESTAMPTZ")
        self.assertFalse(cols["a"].nullable)
        self.assertEqual(cols["b"].type, "character varying(10)")
        self.assertTrue(cols["b"].unique)
        self.assertEqual(cols["c"].default, "1.5")

    def test_compound_alter_is_split_into_ops(self):
        ops = sql_parse.parse_migration(
            "ALTER TABLE t ADD COLUMN x TEXT NOT NULL DEFAULT 'a', ALTER COLUMN y TYPE integer, "
            "DROP COLUMN z;")
        self.assertEqual([o.kind for o in ops], ["add_column", "alter_type", "drop_column"])
        self.assertTrue(ops[0].detail["not_null"])
        self.assertEqual(ops[0].detail["default"], "'a'")

    def test_unsupported_statement_is_flagged_not_ignored(self):
        ops = sql_parse.parse_migration("CLUSTER invoices USING idx_invoices_customer;")
        self.assertEqual(ops[0].kind, "unsupported")
        schema = sql_parse.parse_schema("CREATE TABLE invoices (id SERIAL PRIMARY KEY);")
        _, notes = sql_parse.apply_ops(schema, ops)
        self.assertTrue(notes, "an unmodelled statement must surface as a coverage note")


class TestShadowReplay(unittest.TestCase):
    def setUp(self):
        self.pre = sql_parse.parse_schema(
            "CREATE TABLE t (id SERIAL PRIMARY KEY, email TEXT NOT NULL, note TEXT);")
        self.seed = {"t": [{"id": 1, "email": "a@b.c", "note": "x"},
                           {"id": 2, "email": "a@b.c", "note": "y"}]}
        self.queries = [{"id": "q1", "service": "web", "criticality": "high",
                         "sql": "SELECT id, note FROM t"}]

    def _replay(self, migration: str):
        ops = sql_parse.parse_migration(migration)
        post, _ = sql_parse.apply_ops(self.pre, ops)
        return shadow_db.replay(self.pre, post, ops, self.seed, self.queries)

    def test_dropped_column_breaks_a_live_query(self):
        rep = self._replay("ALTER TABLE t DROP COLUMN note;")
        self.assertEqual([b["query_id"] for b in rep.broken], ["q1"])
        self.assertIn("no such column", rep.broken[0]["error"])

    def test_unique_index_fails_on_existing_duplicates(self):
        rep = self._replay("CREATE UNIQUE INDEX t_email_key ON t (email);")
        self.assertTrue(any("UNIQUE constraint failed" in e for e in rep.data_errors))

    def test_narrowing_type_finds_the_offending_rows(self):
        pre = sql_parse.parse_schema("CREATE TABLE c (id SERIAL PRIMARY KEY, code TEXT);")
        ops = sql_parse.parse_migration("ALTER TABLE c ALTER COLUMN code TYPE varchar(2);")
        post, _ = sql_parse.apply_ops(pre, ops)
        rep = shadow_db.replay(pre, post, ops, {"c": [{"id": 1, "code": "USA"},
                                                     {"id": 2, "code": "GB"}]}, [])
        self.assertEqual(rep.data_loss[0]["offending_rows"], 1)
        self.assertEqual(rep.data_loss[0]["offending_samples"], ["USA"])


class TestMemory(unittest.TestCase):
    def test_memory_raises_and_cites_but_never_clears(self):
        mem = IncidentMemory(INCIDENTS)
        bump, refs = mem.escalation("INDEX_LOCK_NO_CONCURRENT", "invoices")
        self.assertEqual(bump, 1)
        self.assertIn("INC-2024-07", refs)
        bump_other, _ = mem.escalation("INDEX_LOCK_NO_CONCURRENT", "usage_events")
        self.assertEqual(bump_other, 0, "an unrelated table must not inherit the bump")
        self.assertGreaterEqual(bump, 0, "escalation is never negative")


class TestPipeline(unittest.TestCase):
    def test_blocking_case_blocks_and_verifies_a_plan(self):
        out = run("case_01_rename_with_compat_view")
        r = out["report"]
        self.assertEqual(r["verdict"], "BLOCK")
        self.assertTrue(r["plan_verification"]["verified"])
        self.assertEqual(r["attempts"], 2, "the view lever should trigger exactly one retry")
        self.assertTrue(all(h["evidence"] for h in r["hazards"]),
                        "every hazard must cite evidence")

    def test_clean_case_stays_clean(self):
        r = run("case_06_safe_unique_index")["report"]
        self.assertEqual(r["verdict"], "SAFE")
        self.assertEqual(r["hazards"], [])

    def test_coverage_gap_is_reported_for_unmodelled_statement(self):
        r = run("case_12_release_train")["report"]
        self.assertTrue(any("CLUSTER" in gap for gap in r["coverage_gaps"]))

    def test_escalates_instead_of_shipping_an_unproven_plan(self):
        r = run("case_01_rename_with_compat_view", max_attempts=1)["report"]
        self.assertTrue(r["escalated_to_human"])
        self.assertFalse(r["plan_verification"]["verified"])

    def test_run_is_deterministic(self):
        a = run("case_12_release_train")["report"]
        b = run("case_12_release_train")["report"]
        self.assertEqual(json.dumps(a["hazards"], sort_keys=True),
                         json.dumps(b["hazards"], sort_keys=True))
        self.assertEqual(a["plan"], b["plan"])


class TestApprovalGate(unittest.TestCase):
    def setUp(self):
        self.case_path = str(CASES / "case_06_safe_unique_index.json")
        out = run("case_06_safe_unique_index")
        self.report_path = ROOT / "results" / "test_gate.json"
        self.report_path.parent.mkdir(exist_ok=True)
        self.report_path.write_text(json.dumps(out["report"], default=str))

    def tearDown(self):
        self.report_path.unlink(missing_ok=True)

    def test_execute_refuses_without_human_approval(self):
        code = cli.main(["execute", "--report", str(self.report_path), "--case", self.case_path])
        self.assertEqual(code, 2)

    def test_execute_runs_in_the_sandbox_once_approved(self):
        code = cli.main(["execute", "--report", str(self.report_path), "--case", self.case_path,
                         "--i-approve", "--reviewer", "test reviewer"])
        self.assertEqual(code, 0)

    def test_execute_refuses_a_blocked_review(self):
        out = run("case_02_drop_column_still_read")
        path = ROOT / "results" / "test_gate_block.json"
        path.write_text(json.dumps(out["report"], default=str))
        try:
            code = cli.main(["execute", "--report", str(path),
                             "--case", str(CASES / "case_02_drop_column_still_read.json"),
                             "--i-approve", "--reviewer", "test reviewer"])
            self.assertEqual(code, 3)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
