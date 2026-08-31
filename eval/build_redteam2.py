"""Generate the 6 RED-TEAM ROUND 2 cases: migrations the *parser* gets wrong.

WHY A SECOND RED-TEAM SET
-------------------------
Round 1 (`eval/redteam`) probed statement *kinds*: is there a hazard class nobody
enumerated?  It found two, and the fix was `sentinel/rulebook.py`, an exhaustive
partition of every kind `parse_migration` can emit.  Exhaustive over the op list.

This round probed one level up: **is the op list the migration?**  It is not.

    UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL;
    ALTER TABLE invoices DROP COLUMN tax_rate;

Two statements in, one op out.  `strip_comments` deleted from the `--` inside the
string literal to end of line, the resulting unterminated quote swallowed the rest of
the file, and the DROP COLUMN was never presented to a rule, to replay or to the
coverage ledger.  Not a wrong severity - an absent statement.  Every honesty layer in
this repository sits downstream of the parse, so none of them could see it: a rule
inventory cannot inventory a statement that never became an op.

THIS SET IS IN SAMPLE. SAID PLAINLY.
------------------------------------
The v14 scanner was written *from* these probes.  They prove specific holes are closed,
not that the pipeline generalises.  The generalisation evidence runs the other way and
is computed rather than asserted: `no_text_conservation` - v13 behaviour exactly,
retired splitter included - is **identical to `full` on all 28 labelled cases** in
`eval/cases`, `eval/holdout` and `eval/redteam`.  Same verdicts, same hazards, same
severities, same gap counts.  A layer that moves no number that was already being
measured is a layer that was missing rather than one retuned to fit what it was shown.

WHAT EACH CASE IS FOR
---------------------
  rt2_01  the hit.  A `--` inside a string literal costs v13 the second half of the
          migration, including a DROP COLUMN a live billing query reads.  Note what the
          ground truth is NOT: this SQL is perfectly legal Postgres, so there is no
          `MIGRATION_TEXT_UNPARSED` hazard in the label.  The hazards are the ordinary
          ones - and v13 finds almost none of them, because it never saw the statement
          they come from.  The improvement shows up as recall on the existing
          vocabulary, which is the strongest form this evidence can take.
  rt2_02  DDL inside `DO $$ ... $$`.  Executes on deploy, invisible to expand/contract,
          to the dependency map and to replay.  The label carries all three hazards a
          Postgres reviewer would name, including the two the pipeline still cannot
          find, so the published recall on this case is 1 of 3.  It is labelled that way
          on purpose: naming the block is not the same as modelling it, and a set that
          only labels what the tool can do is not a test.
  rt2_03  an unterminated literal.  Postgres rejects the script, so the deploy fails on
          the statement itself and the reviewed artefact was never the deployed one.
          Here the label IS `MIGRATION_TEXT_UNPARSED`, because the defect is in the
          migration rather than in the reader.
  rt2_04  THE CANARY, and the reason this pass was not just "add a scanner".  Postgres
          nests block comments; the retired regex did not, so a commented-out
          `DROP COLUMN` behind a nested `*/` became a live statement and v13 blocked a
          migration whose destructive statement is switched off.  Ground truth: no
          hazard at all.  Any finding here is a false alarm, and a tool that invents a
          blocker out of a comment gets switched off - which makes its recall zero.
  rt2_05  a trigger function whose body is full of semicolons and contains no DDL.
          Ground truth: no hazard.  The honest output is one declared `procedural_body`
          gap and a sign-off, not a finding - and not the four fictional `unsupported`
          statements v13 reported after shredding the body at its inner semicolons.
  rt2_06  the second canary: an ordinary migration with a real line comment, an escaped
          apostrophe and a `--` inside a string default.  Everything the scanner exists
          for is present and none of it is a defect.  Ground truth: no hazard, no gap
          from this layer.

Ground truth was written from PostgreSQL semantics before the fixed pipeline was run.

Run:  python3 eval/build_redteam2.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.build_cases import ROWS, SCHEMA, SEED, hz  # noqa: E402
from eval.build_redteam import QUERIES_RT, SCHEMA_RT  # noqa: E402

OUT = pathlib.Path(__file__).parent / "redteam2"

CASES = [
    {
        "id": "rt2_01_comment_marker_inside_literal",
        "title": "Normalise the invoice currency default, then retire the unused tax column",
        "owner_service": "platform",
        "scenario": "A two-statement cleanup PR. The backfill note is a string literal that happens "
                    "to contain a double hyphen, which is legal Postgres and completely ordinary in "
                    "human-written copy. billing-api still selects invoices.tax_rate.",
        "migration_sql": "UPDATE invoices SET currency = 'usd -- legacy default' "
                         "WHERE currency IS NULL;\n"
                         "ALTER TABLE invoices DROP COLUMN tax_rate;\n",
        "rollback_sql": "ALTER TABLE invoices ADD COLUMN tax_rate REAL;\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("BREAKING_QUERY", "blocker",
                   "q_billing_tax selects invoices.tax_rate and fails against the post-migration "
                   "schema."),
                hz("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high",
                   "The column is dropped in the same deploy that still ships the code reading it."),
                hz("UNBATCHED_BACKFILL", "high",
                   "One unbounded UPDATE over a 48M-row table holds locks and bloats WAL for the "
                   "length of the statement."),
                hz("CROSS_SERVICE_UNCOORDINATED", "high",
                   "The migration is owned by platform and the breakage lands in billing-api, "
                   "whose deploy the author does not control."),
            ],
            "notes": "The SQL is valid Postgres. Nothing here is a syntax defect, which is why the "
                     "label carries no MIGRATION_TEXT_UNPARSED: the defect was in the reader. v13 "
                     "parsed one statement out of two and reported on the half it could see.",
        },
    },
    {
        "id": "rt2_02_do_block_hides_the_drop",
        "title": "Idempotent column cleanup wrapped in a DO block, as the framework generates it",
        "owner_service": "platform",
        "scenario": "The team's migration generator wraps destructive DDL in an idempotency guard so "
                    "reruns are safe. The guard is a procedural block, and the DDL inside it is the "
                    "same drop as rt2_01.",
        "migration_sql": "DO $$\n"
                         "BEGIN\n"
                         "  IF EXISTS (SELECT 1 FROM information_schema.columns\n"
                         "             WHERE table_name = 'invoices' AND column_name = 'tax_rate')\n"
                         "  THEN\n"
                         "    ALTER TABLE invoices DROP COLUMN tax_rate;\n"
                         "  END IF;\n"
                         "END\n"
                         "$$;\n",
        "rollback_sql": "ALTER TABLE invoices ADD COLUMN tax_rate REAL;\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("PROCEDURAL_DDL_UNREVIEWED", "blocker",
                   "A schema change executes inside the $$ body; the expand/contract analysis, the "
                   "dependency map and the shadow replay all ran on the outer statement only."),
                hz("BREAKING_QUERY", "blocker",
                   "q_billing_tax selects invoices.tax_rate and fails after the block runs."),
                hz("DESTRUCTIVE_NO_EXPAND_CONTRACT", "high",
                   "The drop still lands in a single deploy; wrapping it in a guard makes the rerun "
                   "safe, not the deploy."),
            ],
            "notes": "Two of these three are labelled knowing the pipeline cannot find them: a "
                     "keyword census over a procedural body is not a parse, so the packet can say "
                     "that DDL is in there and not what it does. Published recall on this case is "
                     "1 of 3, and the case is not cleared, which is the only property that "
                     "protects the reviewer.",
        },
    },
    {
        "id": "rt2_03_unterminated_literal",
        "title": "Mark the invoice open and drop the tax column, with one quote missing",
        "owner_service": "platform",
        "scenario": "A hand-edited migration where a closing quote was lost in a rebase. Postgres "
                    "refuses the script outright, so the deploy fails on the first statement and "
                    "the reviewed artefact was never the deployed one.",
        "migration_sql": "UPDATE invoices SET status = 'open WHERE id = 1;\n"
                         "ALTER TABLE invoices DROP COLUMN tax_rate;\n",
        "rollback_sql": "ALTER TABLE invoices ADD COLUMN tax_rate REAL;\n",
        "ground_truth": {
            "blocking": True,
            "hazards": [
                hz("MIGRATION_TEXT_UNPARSED", "blocker",
                   "The literal opened at `'open` never closes, so Postgres rejects the script and "
                   "everything after that quote is string content rather than SQL."),
            ],
            "notes": "Here the defect is in the migration rather than in the reader, so the label "
                     "is the scanner's own hazard code. v13 reported a medium-severity note about "
                     "a status update and said nothing about the rest of the file.",
        },
    },
    {
        "id": "rt2_04_nested_comment_phantom",
        "title": "Superseded drop, commented out with a nested comment, plus one concurrent index",
        "owner_service": "platform",
        "scenario": "The destructive statement was superseded and commented out. The comment "
                    "contains a comment, which Postgres nests and a non-greedy regex does not. The "
                    "only live statement is a correct concurrent index build.",
        "migration_sql": "/* superseded by 2026_02_02_tax_rate_v2:\n"
                         "   /* original attempt */ ALTER TABLE invoices DROP COLUMN tax_rate;\n"
                         "*/\n"
                         "CREATE INDEX CONCURRENTLY idx_invoices_status ON invoices (status);\n",
        "rollback_sql": "DROP INDEX CONCURRENTLY idx_invoices_status;\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "notes": "The canary for this pass, and the reason the fix is a scanner rather than a "
                     "rule. Every arm has to stay quiet here. v13 raised a destructive-change "
                     "hazard and a broken query out of text Postgres never executes, which is the "
                     "same defect as rt2_01 with the sign flipped.",
        },
    },
    {
        "id": "rt2_05_function_body_no_ddl",
        "title": "Add a dunning audit trigger function and the column it stamps",
        "owner_service": "platform",
        "scenario": "A correct additive migration whose function body is full of semicolons. No DDL "
                    "runs inside the body: it writes a row and returns.",
        "migration_sql": "ALTER TABLE invoices ADD COLUMN dunning_stamped_at TIMESTAMPTZ;\n"
                         "CREATE OR REPLACE FUNCTION stamp_dunning() RETURNS trigger AS $fn$\n"
                         "BEGIN\n"
                         "  NEW.dunning_stamped_at := now();\n"
                         "  RETURN NEW;\n"
                         "END;\n"
                         "$fn$ LANGUAGE plpgsql;\n",
        "rollback_sql": "DROP FUNCTION IF EXISTS stamp_dunning();\n"
                        "ALTER TABLE invoices DROP COLUMN dunning_stamped_at;\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "notes": "No finding is correct here and a declared gap is: nothing in this pipeline "
                     "models a procedural body, so the honest output is one named sign-off on the "
                     "$fn$ block. v13 shredded the body at its inner semicolons into four "
                     "`unsupported` fragments and filed four gaps against statements that do not "
                     "exist.",
        },
    },
    {
        "id": "rt2_06_ordinary_migration_with_quotes",
        "title": "Add a dunning note column whose default contains a double hyphen",
        "owner_service": "platform",
        "scenario": "Every lexical feature this pass added a scanner for, all of it legitimate: a "
                    "real line comment, an escaped apostrophe, and a double hyphen inside a string "
                    "default. Nothing here is a defect.",
        "migration_sql": "-- dunning copy for the retry email, PLAT-4471\n"
                         "ALTER TABLE invoices ADD COLUMN dunning_note TEXT "
                         "DEFAULT 'not attempted -- see runbook';\n"
                         "CREATE INDEX CONCURRENTLY idx_invoices_dunning_note "
                         "ON invoices (dunning_note);\n",
        "rollback_sql": "DROP INDEX CONCURRENTLY idx_invoices_dunning_note;\n"
                        "ALTER TABLE invoices DROP COLUMN dunning_note;\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "notes": "The second canary. A scanner that turns legal SQL into a finding is worse "
                     "than the splitter it replaced, so this case exists to price that. v13 lost "
                     "the index build entirely here and still returned a clean verdict, which is "
                     "the quiet version of the same bug.",
        },
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for spec in CASES:
        case = dict(spec)
        case["schema_sql"] = SCHEMA_RT.strip()
        case["row_estimates"] = dict(ROWS)
        case["queries"] = [dict(q) for q in QUERIES_RT]
        case["seed"] = {k: [dict(r) for r in v] for k, v in SEED.items()}
        path = OUT / f"{case['id']}.json"
        path.write_text(json.dumps(case, indent=1) + "\n")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
