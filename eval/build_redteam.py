"""Generate the 7 RED-TEAM cases: migrations written to make this pipeline approve an outage.

WHY THIS SET EXISTS, AND WHAT IT IS NOT
---------------------------------------
`eval/cases` asks "does the pipeline find the hazards I thought of?"  `eval/holdout`
asks "does it find them on a schema the rules were never written against?"  Neither can
ask the question that matters most for a safety tool: **is there a class of hazard
nobody enumerated?**  Both sets were labelled from a hazard vocabulary, and a
vocabulary is a list of the things you already know.

So this set was written the other way round.  It is the output of an adversarial pass
whose brief was: find a migration a Postgres primary would call an outage and this
pipeline calls SAFE.  Six probes, two hits, and the two hits were not wrong rules -
they were absent rules that nothing in the repository was counting.  `rt_01` and
`rt_02` are those two.  `rt_03` to `rt_05` are the statement kinds the same audit found
in the same condition but which cannot be turned into a hazard honestly, so they become
declared gaps instead.  `rt_06` and `rt_07` exist to stop the fix from becoming worse
than the bug.

THIS SET IS IN SAMPLE. SAID PLAINLY, SO NOBODY HAS TO WORK IT OUT.
------------------------------------------------------------------
The v13 rules were written *from* these probes.  These cases are not evidence that the
pipeline generalises; they are evidence that two specific holes are closed and that
closing them cost nothing elsewhere.  The generalisation evidence for v13 is the
opposite direction and it is the number to read first: `no_rule_coverage` - v12
behaviour exactly - is **identical to `full` on all 21 labelled cases** in
`eval/cases` and `eval/holdout`.  A layer that changes no existing number is a layer
that was missing, not a layer retuned to fit the cases it was shown.

WHAT EACH CASE IS FOR
---------------------
  rt_01  the hit.  DROP INDEX on a 48M-row table three live statements filter by.
         Every statement still executes, so replay is silent, and no rule mentioned
         `drop_index`.  v12 verdict: SAFE, zero hazards, zero gaps.
  rt_02  the other hit.  CONCURRENTLY inside BEGIN/COMMIT.  Postgres refuses it and
         every major framework opens that transaction by default.  v12: SAFE.  The
         text-only baseline gets this one, because it is a famous string - which is
         published rather than excluded.
  rt_03  the same statement kind as rt_01 on an index no statement in the corpus uses.
         The honest answer is not "safe": a sample of the consumers proves nothing
         about a query plan.  Expected NEEDS_COVERAGE_SIGNOFF, no hazard.
  rt_04  `SET DEFAULT`.  Nothing that runs today can fail; every future signup gets a
         different plan.  Residual: declared, not flagged.
  rt_05  `DROP NOT NULL`.  Readers that assume non-null live in application code, which
         is not in any corpus.  Residual: declared, not flagged.
  rt_06  the challenging case.  The commonest correct index migration - drop the narrow
         index, create the composite that covers it - wrapped in the transaction from
         rt_02.  Ground truth is the transaction hazard ONLY.  A tool that also raises
         ACCESS_PATH_REMOVED here is crying wolf, because a B-tree on (customer_id,
         status) still serves a lookup on customer_id.
  rt_07  the same migration with the transaction wrapper removed: a correct migration.
         Expected SAFE, no hazard, no gap.  This is the canary for the v13 rules,
         exactly as `case_06` is the canary for the v1 rules.  The first version of the
         residual-gap class failed this and flagged `case_06` too; see
         `sentinel/rulebook.py`.

Ground truth was written from PostgreSQL semantics before running the fixed pipeline.

Run:  python3 eval/build_redteam.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.build_cases import ROWS, SCHEMA, SEED, Q, hz  # noqa: E402

OUT = pathlib.Path(__file__).parent / "redteam"

# Two more indexes on the shared world. `idx_customers_company` is the one nothing in
# the corpus looks rows up by - it exists so rt_03 can ask what "unused" is evidence of.
SCHEMA_RT = SCHEMA.rstrip() + """

CREATE INDEX idx_customers_company ON customers (company_name);
CREATE INDEX idx_usage_events_occurred ON usage_events (occurred_at);
"""

# Three statements that use invoices(customer_id) as an access path rather than as a
# projection. This is why the index in rt_01 exists, and it is the evidence the packet
# quotes when it blocks the drop.
Q_RT = list(Q) + [
    ("q_billing_customer_invoices", "billing-api", "critical", "customer invoice list",
     "SELECT id, invoice_number, amount_cents, status FROM invoices WHERE customer_id = 1 "
     "ORDER BY issued_at DESC LIMIT 50"),
    ("q_support_open_for_customer", "support-admin", "high", "open invoices for a customer",
     "SELECT invoice_number, status FROM invoices WHERE customer_id = 1 AND status = 'open'"),
    ("q_bi_revenue_by_customer", "bi", "medium", "revenue per customer",
     "SELECT customer_id, SUM(amount_cents) AS revenue FROM invoices GROUP BY customer_id"),
]
QUERIES_RT = [{"id": qid, "service": svc, "criticality": crit, "label": label, "sql": sql}
              for qid, svc, crit, label, sql in Q_RT]

CASES = [
    {
        "id": "rt_01_drop_index_still_used",
        "title": "Drop the customer index on invoices during an unused-index cleanup",
        "owner_service": "platform",
        "scenario": "A quarterly index-cleanup PR. The author read a dashboard that said the index "
                    "was unused, and the dashboard was reset when the primary was last failed over. "
                    "Three services still look invoices up by customer_id, one of them on the "
                    "checkout path.",
        "migration_sql": "DROP INDEX idx_invoices_customer;",
        "rollback_sql": "CREATE INDEX CONCURRENTLY idx_invoices_customer ON invoices (customer_id);\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [hz("ACCESS_PATH_REMOVED", "blocker",
                           "Three corpus statements filter invoices by customer_id, one critical, on "
                           "48M rows. Removing the only index on that column turns each of them "
                           "into a sequential scan.")],
            "notes": "Every statement still executes after this migration, which is exactly why "
                     "shadow replay cannot see it. The hazard is in the plan, not the result.",
        },
    },
    {
        "id": "rt_02_concurrently_inside_transaction",
        "title": "Add a concurrent index from inside the framework's DDL transaction",
        "owner_service": "platform",
        "scenario": "The author did the careful thing and used CONCURRENTLY. The migration framework "
                    "wraps every migration in a transaction by default and nobody disabled it, so "
                    "Postgres will refuse the statement and the deploy fails half-applied.",
        "migration_sql": "BEGIN;\n"
                         "CREATE INDEX CONCURRENTLY idx_usage_events_customer ON usage_events "
                         "(customer_id);\n"
                         "COMMIT;",
        "rollback_sql": "DROP INDEX CONCURRENTLY idx_usage_events_customer;\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [hz("CONCURRENT_DDL_IN_TRANSACTION", "blocker",
                           "CREATE INDEX CONCURRENTLY cannot run inside a transaction block. "
                           "Postgres raises an error on the statement itself.")],
            "notes": "The hazard is a correlation between two statements, so no single-statement "
                     "rule could find it. The text-only baseline does find it, because BEGIN and "
                     "CONCURRENTLY in one file is a famous string.",
        },
    },
    {
        "id": "rt_03_drop_index_no_corpus_user",
        "title": "Drop the company-name index nothing in the corpus looks up by",
        "owner_service": "platform",
        "scenario": "The same cleanup PR, second statement. This time the corpus really has no "
                    "statement that filters, joins or sorts by company_name - it only ever selects "
                    "it. The question is what that silence is worth.",
        "migration_sql": "DROP INDEX idx_customers_company;",
        "rollback_sql": "CREATE INDEX CONCURRENTLY idx_customers_company ON customers "
                        "(company_name);\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "notes": "Correct answer: no hazard, and no clean bill of health either. The corpus is a "
                     "declared sample of the consumers and shadow replay has no query planner, so "
                     "the review has no evidence the index is unused - only no evidence that it is "
                     "used. Expected verdict NEEDS_COVERAGE_SIGNOFF with an unused_access_path gap "
                     "that closes on pg_stat_user_indexes.",
        },
    },
    {
        "id": "rt_04_change_signup_default",
        "title": "Change the default plan for new signups",
        "owner_service": "billing-api",
        "scenario": "A growth experiment. Every row that exists is untouched and every statement in "
                    "the corpus still executes; every signup after the deploy lands on a different "
                    "plan, and the plan column drives billing.",
        "migration_sql": "ALTER TABLE customers ALTER COLUMN plan SET DEFAULT 'team';",
        "rollback_sql": "ALTER TABLE customers ALTER COLUMN plan SET DEFAULT 'free';\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "notes": "No hazard in the vocabulary fits, and inventing one would be a false alarm. "
                     "`set_default` is RESIDUAL in sentinel/rulebook.py: no rule inspects it and "
                     "replay cannot execute a future write. Expected NEEDS_COVERAGE_SIGNOFF with an "
                     "unruled_statement gap.",
        },
    },
    {
        "id": "rt_05_relax_country_not_null",
        "title": "Make country_code nullable again",
        "owner_service": "billing-api",
        "scenario": "Relaxing a constraint to unblock a signup form. Nothing breaks in the database; "
                    "the tax service dereferences country_code without a null check and lives in "
                    "application code, which is not in any SQL corpus.",
        "migration_sql": "ALTER TABLE customers ALTER COLUMN country_code DROP NOT NULL;",
        "rollback_sql": "ALTER TABLE customers ALTER COLUMN country_code SET NOT NULL;\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "notes": "Same shape as rt_04 and the same honest answer. Relaxing nullability is "
                     "RESIDUAL: the readers that assume non-null are not SQL. Expected "
                     "NEEDS_COVERAGE_SIGNOFF with an unruled_statement gap.",
        },
    },
    {
        "id": "rt_06_index_swap_inside_transaction",
        "title": "Swap the narrow index for the composite one, inside a transaction",
        "owner_service": "platform",
        "scenario": "The commonest correct index migration there is: drop the single-column index, "
                    "create the composite that covers it. Shipped inside the framework's default "
                    "DDL transaction, which is the one thing wrong with it.",
        "migration_sql": "BEGIN;\n"
                         "DROP INDEX CONCURRENTLY idx_invoices_customer;\n"
                         "CREATE INDEX CONCURRENTLY idx_invoices_customer_status ON invoices "
                         "(customer_id, status);\n"
                         "COMMIT;",
        "rollback_sql": "DROP INDEX CONCURRENTLY idx_invoices_customer_status;\n"
                        "CREATE INDEX CONCURRENTLY idx_invoices_customer ON invoices "
                        "(customer_id);\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [hz("CONCURRENT_DDL_IN_TRANSACTION", "blocker",
                           "Both CONCURRENTLY statements sit inside the transaction opened at "
                           "statement 0; Postgres refuses each of them.")],
            "notes": "ACCESS_PATH_REMOVED is DELIBERATELY ABSENT from this ground truth. A B-tree on "
                     "(customer_id, status) serves a lookup on customer_id, so the access path "
                     "survives and raising the hazard here would be a false alarm on the correct "
                     "version of the change. This is the case that makes the rt_01 rule usable "
                     "instead of switched off.",
        },
    },
    {
        "id": "rt_07_index_swap_done_right",
        "title": "The same index swap, outside a transaction: a correct migration",
        "owner_service": "platform",
        "scenario": "Nothing is wrong with this migration. It exists so the v13 rules have to prove "
                    "they can stay quiet, the same job case_06 does for the v1 rules.",
        "migration_sql": "DROP INDEX CONCURRENTLY idx_invoices_customer;\n"
                         "CREATE INDEX CONCURRENTLY idx_invoices_customer_status ON invoices "
                         "(customer_id, status);",
        "rollback_sql": "DROP INDEX CONCURRENTLY idx_invoices_customer_status;\n"
                        "CREATE INDEX CONCURRENTLY idx_invoices_customer ON invoices "
                        "(customer_id);\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "notes": "Correct answer: no hazards, no coverage gaps, verdict SAFE. Any finding here "
                     "is a false alarm and any gap here is the residual class over-reaching.",
        },
    },
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        doc = {
            "id": case["id"],
            "title": case["title"],
            "owner_service": case["owner_service"],
            "scenario": case["scenario"],
            "schema_sql": SCHEMA_RT.strip(),
            "row_estimates": ROWS,
            "queries": QUERIES_RT,
            "seed": json.loads(json.dumps(SEED)),
            "migration_sql": case["migration_sql"].strip() + "\n",
            "rollback_sql": case["rollback_sql"],
            "ground_truth": case["ground_truth"],
        }
        (OUT / f"{case['id']}.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {len(CASES)} red-team cases to {OUT}")


if __name__ == "__main__":
    main()
