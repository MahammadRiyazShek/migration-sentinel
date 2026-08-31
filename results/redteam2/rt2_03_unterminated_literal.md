# Migration review: Mark the invoice open and drop the tax column, with one quote missing

**BLOCK - do not merge**

Do not ship this as written. 2 coverage gap(s) need a named sign-off before this can be called safe. 1 blocker, 0 high, 0 medium, 0 low. 1 defect(s) in the SQL this packet generated: see the plan self-audit before running any of it. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-rt2_03_unterminated_literal` · case `rt2_03_unterminated_literal` · owning service `platform` · 12.6 ms · model scripted-v1 (4 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

> **Escalated to a human.** The pipeline could not produce a phase 1 it can prove is backwards compatible. Do not proceed on automation alone.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Migration text no structural review covered | `migration script` | static |

### 1. [BLOCKER] Migration text no structural review covered

an unterminated string starts at character 29, so Postgres rejects this script and everything after that point was reviewed as string content rather than as SQL

- evidence: scanner: `'open WHERE id = 1;
ALTER TABLE invoices DROP COLUMN tax_rate;`
- evidence: a single-quoted literal never closes, so Postgres rejects the script and everything after the quote was read as string content

## Blast radius

- statements in the corpus that touch the changed objects: 8 (weighted score 25)
- shadow replay: 19/19 statements passed before, 19/19 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 1

## Recommended rollout

> **This is not runnable SQL and must not be treated as a recommendation.** The generated phase1 script contains a construct this pipeline cannot read back, which means it was built from a parse of the input that is already known to be unreliable. It is printed for the reviewer's information only. See *Plan self-audit*.

Plan generated on attempt 2 of 2; phase 1 **not verified** - see the escalation above.

### Phase 1 - expand (safe to run now)

```sql
-- repeat until zero rows are affected (batch size 5000):
UPDATE invoices SET status = 'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND "id" IN (SELECT "id" FROM "invoices" WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate LIMIT 5000);
```

### Human decisions required (the tool will not decide these)

- phase 1 was reduced to additive statements only; the rest needs a human to choose the deploy order
- coverage gap on `invoices.status` (in_place_data_mutation): a reviewer confirms which consumers of invoices.status depend on the current values
- coverage gap on `characters 29 onward` (unreviewable_text): the script is fixed and resubmitted; there is nothing here for a reviewer to sign off, because there is nothing here that runs
- PLAN DEFECT (GENERATED_TEXT_UNPARSED) in the generated phase1 script: a reviewer reads the generated script by hand before running it

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the accepted risk for MIGRATION_TEXT_UNPARSED?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 1 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

| # | defect | script | statement |
|---|---|---|---|
| 1 | **GENERATED_TEXT_UNPARSED** | phase1 | `{'kind': 'string', 'start': 29, 'end': 200, 'text': '\'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND` |

### 1. This pipeline emitted SQL it cannot itself read back

an unterminated construct in the generated script, which Postgres would refuse, so this packet is printing SQL it did not fully model.

- evidence: tools/parse_audit.py on the generated phase1 script: an unterminated construct in the generated script, which Postgres would refuse
- evidence: statements lexed 1, ops produced 1
- closes when: a reviewer reads the generated script by hand before running it


## Coverage ledger

2 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `invoices.status` | existing rows rewritten; replay cannot see changed answers | rows that already exist in invoices are rewritten; replay proves the corpus still executes, never that it still returns the same answer | a reviewer confirms which consumers of invoices.status depend on the current values |
| `characters 29 onward` | unreviewable_text | an unterminated string starts at character 29; from there to the end of the file every character was read as string content, so nothing in that region was parsed, ruled or replayed, and no finding about it would be about anything Postgres executes | the script is fixed and resubmitted; there is nothing here for a reviewer to sign off, because there is nothing here that runs |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/rt2_03_unterminated_literal.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 2 coverage gap(s) need a named sign-off before this can be called safe. 1 blocker, 0 high, 0 medium, 0 low. The rewritten plan still breaks at least one statement, so a human has to decide the sequencing.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
