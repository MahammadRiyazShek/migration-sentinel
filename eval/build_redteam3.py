"""Generate the 3 RED-TEAM ROUND 3 cases: migrations whose danger is in the plan we write.

WHY THIS SET EXISTS
-------------------
Round 1 asked whether there was a hazard class nobody enumerated: two hits, fixed in
`sentinel/rulebook.py`.  Round 2 asked whether the op list is the migration: one hit,
fixed in `sentinel/tools/parse_audit.py`.  Both rounds pointed the adversarial pass at
the input file, because every layer in this repository points at the input file.

This round pointed it at the output.  The pipeline emits three SQL scripts on every
run - phase 1, phase 2, a rollback - and until v16 the packet printed all three and
checked one, with replay, which `results/ablation.md` has said since v2 is the weaker
half of the design on its own.

WHAT EACH CASE IS FOR
---------------------
  rt3_01  the hit.  `ADD COLUMN ... NOT NULL DEFAULT ''` on customers: a migration that
          is genuinely safe as written, and v15 says so - SAFE, zero hazards, "phase 1
          verified".  The plan it hands the reviewer contains a code step ("start
          writing customers.billing_email") and a rollback that drops that column, with
          no statement of the order the two are valid in, plus an ungated SET NOT NULL
          in phase 2.  Shadow replay of the rollback breaks zero corpus statements,
          which is exactly why replay could never find it: the statements that break are
          the ones this packet is asking someone to deploy tomorrow.
  rt3_02  `ADD CONSTRAINT ... CHECK` on a small table.  The migration is correctly
          split into `NOT VALID` in phase 1 and `VALIDATE CONSTRAINT` in phase 2, and
          `sentinel/rulebook.py` has carried the sentence "no rule prices it against the
          row estimate" about that second statement since v13.  The plan generator has
          been emitting one with no human gate ever since.
  rt3_03  the canary, and the reason this set has three cases instead of two.
          `ADD COLUMN nickname TEXT` with no code step and no contract phase.  Its
          rollback also drops a column this pipeline just added, and the correct answer
          is silence: a rollback nothing depends on yet is the normal, safe case.  A
          layer that flags every generated DROP COLUMN would cap every additive
          migration in the world, which is the `case_06` failure with a new name.

THIS SET IS IN SAMPLE. SAID PLAINLY.
------------------------------------
`sentinel/plan_audit.py` was written from these three probes and from the 21 labelled
cases already in the repository.  The generalisation evidence runs the other way and
is computed in `eval/run_redteam3.py`: the audit cannot move a hazard, a severity or an
input verdict on any of the 34 labelled cases by construction, and it finds 6 defects
in plans this repository has been shipping since v2 - on cases nobody wrote for it.

The corpus, schema, fixtures and row estimates are copied verbatim from
`eval/cases/case_10_add_fk_constraint.json`, so nothing about the world changes between
this set and the in-sample set except the migration under review.
"""
from __future__ import annotations

import copy
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "redteam3"
BASE = ROOT / "eval" / "cases" / "case_10_add_fk_constraint.json"

PROBES = [
    {
        "id": "rt3_01_additive_column_with_dependent_rollback",
        "title": "A genuinely safe additive column, and the rollback the tool writes for it",
        "owner_service": "billing-api",
        "scenario": "Nothing is wrong with this migration. Everything wrong is in the plan the "
                    "pipeline generates for it: a code step that asks the team to start writing the "
                    "new column, and a rollback that drops it, printed in the same packet with no "
                    "statement of the order they are valid in.",
        "migration_sql": "ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL DEFAULT '';\n",
        "rollback_sql": "ALTER TABLE customers DROP COLUMN billing_email;\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "plan_defects": ["ROLLBACK_WINDOW_UNSTATED", "CONTRACT_STEP_UNGATED"],
            "notes": "Correct answer on the migration: no hazards. Correct answer on the plan: two "
                     "defects, so the packet must not print a clean verdict over SQL nothing "
                     "reviewed. v15: SAFE, phase 1 verified, both defects shipped.",
        },
    },
    {
        "id": "rt3_02_validate_constraint_ungated",
        "title": "A correctly split CHECK constraint, and the unpriced lock in phase 2",
        "owner_service": "billing-api",
        "row_estimates_override": {"subscriptions": 9000},
        "scenario": "The pipeline does the textbook thing: ADD CONSTRAINT ... NOT VALID in phase 1, "
                    "VALIDATE CONSTRAINT in phase 2. The rule inventory has said in writing since "
                    "v13 that nothing prices that second statement against the row estimate, and "
                    "the plan generator has been emitting it with no human gate ever since.",
        "migration_sql": "ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_price_positive "
                         "CHECK (price_cents >= 0);\n",
        "rollback_sql": "ALTER TABLE subscriptions DROP CONSTRAINT subscriptions_price_positive;\n",
        "ground_truth": {
            "blocking": False,
            "hazards": ["CONSTRAINT_VALIDATION_LOCK"],
            "plan_defects": ["CONTRACT_STEP_UNGATED"],
            "notes": "Correct answer on the migration: one non-blocking lock hazard. Correct answer "
                     "on the plan: the generated VALIDATE CONSTRAINT needs a named human decision "
                     "before anyone runs phase 2. v15: SAFE, phase 1 verified, defect shipped.",
        },
    },
    {
        "id": "rt3_03_additive_column_nobody_depends_on",
        "title": "The canary: an additive column, no code step, and a rollback that is fine",
        "owner_service": "billing-api",
        "scenario": "The same shape as rt3_01 with the dependency removed. The generated rollback "
                    "still drops a column this pipeline just added, and the correct answer is "
                    "silence. A layer that flags every generated DROP COLUMN caps every additive "
                    "migration in the world, which is case_06's failure mode with a new name.",
        "migration_sql": "ALTER TABLE customers ADD COLUMN nickname TEXT;\n",
        "rollback_sql": "ALTER TABLE customers DROP COLUMN nickname;\n",
        "ground_truth": {
            "blocking": False,
            "hazards": [],
            "plan_defects": [],
            "notes": "Correct answer: SAFE, no hazards, no plan defects, no coverage gaps. Any "
                     "defect reported here is the plan audit over-reaching.",
        },
    },
]


def build() -> list[pathlib.Path]:
    base = json.loads(BASE.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for probe in PROBES:
        case = copy.deepcopy(base)
        case["id"] = probe["id"]
        case["title"] = probe["title"]
        case["owner_service"] = probe["owner_service"]
        case["scenario"] = probe["scenario"]
        case["migration_sql"] = probe["migration_sql"]
        case["rollback_sql"] = probe["rollback_sql"]
        case["ground_truth"] = probe["ground_truth"]
        if probe.get("row_estimates_override"):
            case["row_estimates"] = dict(case["row_estimates"], **probe["row_estimates_override"])
        path = OUT / f"{probe['id']}.json"
        path.write_text(json.dumps(case, indent=2) + "\n")
        written.append(path)
    return written


if __name__ == "__main__":
    for p in build():
        print(f"wrote {p.relative_to(ROOT)}")
