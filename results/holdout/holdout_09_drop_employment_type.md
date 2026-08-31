# Migration review: Drop drivers.employment_type after the HR system took it over

**NOT CLEARED - coverage gap on an affected object**

Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches, or a defect in the plan it generated. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 3 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-holdout_09_drop_employment_type` · case `holdout_09_drop_employment_type` · owning service `dispatch-api` · 12.8 ms · model scripted-v1 (6 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

> **Not cleared on coverage.** The hazards found here are not blocking, but 1 object(s) this migration touches sit inside a blind spot of the review. The verdict is capped rather than clean: no hazard has been invented, and nothing has been certified either. See *Coverage ledger* below.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **HIGH** | Impact lands on a service owned by another team | `-` | static |
| 2 | **HIGH** | Destructive change shipped in a single step | `drivers.employment_type` | static |
| 3 | **HIGH** | SELECT * consumer receives a different column set | `q_etl_driver_roster` | replay |
| 4 | **MEDIUM** | No rollback path supplied | `-` | static |

### 1. [HIGH] Impact lands on a service owned by another team

the migration is owned by `dispatch-api` but breakage lands in bi-etl

- evidence: corpus ownership of failing statements: ['bi-etl']
- services affected: bi-etl

### 2. [HIGH] Destructive change shipped in a single step

drop column on drivers.employment_type lands in a single deploy

- evidence: statement 0: `ALTER TABLE drivers DROP COLUMN employment_type`
- prior incidents: INC-2023-09

### 3. [HIGH] SELECT * consumer receives a different column set

q_etl_driver_roster still runs but its column set changes (removed ['employment_type'], added none)

- evidence: shadow replay columns before=['id', 'carrier_id', 'full_name', 'phone', 'licence_class', 'employment_type', 'hired_on'] after=['id', 'carrier_id', 'full_name', 'phone', 'licence_class', 'hired_on']
- prior incidents: INC-2025-02
- services affected: bi-etl

### 4. [MEDIUM] No rollback path supplied

the change ships without a rollback script

- evidence: case field `rollback_sql` is empty

## Blast radius

- statements in the corpus that touch the changed objects: 2 (weighted score 6)
- shadow replay: 17/17 statements passed before, 17/17 after
- reproduced failures: 0 · silent column changes: 2 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 2 - contract (only after the code steps below)

```sql
ALTER TABLE "drivers" DROP COLUMN "employment_type";
```

### Application changes required between the phases

1. remove every read and write of drivers.employment_type, then wait one full deploy cycle

### Human decisions required (the tool will not decide these)

- confirm drivers.employment_type has had zero reads for the agreed observation window before phase 2
- no rollback could be generated automatically; write one before shipping
- coverage gap on `drivers.employment_type` (uncovered_object): a reviewer greps the real consumers for employment_type before phase 2

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Has the owning team agreed to the deploy order?
- What is the accepted risk for DESTRUCTIVE_NO_EXPAND_CONTRACT?
- What is the accepted risk for MISSING_ROLLBACK?
- Do any consumers read this result set positionally or serialise it whole?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 1 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.

What this audit trusted rather than checked:

- `drivers.employment_type` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `drivers.employment_type`; this audit read the name, not the question

- shadow replay of the generated phase2 script against the post-phase-1 schema: 0 of 17 corpus statement(s) break

## Coverage ledger

1 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `drivers.employment_type` | no statement in the corpus references this object | no statement in the 15-statement corpus references employment_type, so replay had nothing to run against it; that is silence, not a clean bill of health | a reviewer greps the real consumers for employment_type before phase 2 |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/holdout_09_drop_employment_type.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Not cleared: the hazards found are not blocking, but this review has a declared blind spot on an object the migration touches. 1 coverage gap(s) need a named sign-off before this can be called safe. 0 blocker, 3 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
