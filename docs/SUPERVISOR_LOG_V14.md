# Supervisor log, v14: the parse is a sample of the text

v13 audited what this pipeline *inspects* and published an arithmetic for it: enumerate
what your tool can parse, subtract what any part of it actually looks at, publish the
remainder as a named blind spot. `sentinel/rulebook.py` is that arithmetic and it is
exhaustive over the op list.

This pass audited what the pipeline *reads*, and the op list turned out not to be the
migration.

## The brief

Every previous pass, including the red-team pass, took the parse as the universe. Both
labelled sets, the rule inventory, the coverage ledger, the provenance narrator: all of
them operate on operations, and operations come out of `parse_migration`. So this pass
ran one question at the layer underneath: **is there text in the file that never becomes
an operation at all?**

Six probes. Two hits and one canary, and the first hit is the worst defect this
repository has had.

## R1: a double hyphen inside a string literal

```sql
UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL;
ALTER TABLE invoices DROP COLUMN tax_rate;
```

Legal Postgres. Ordinary human-written copy. `strip_comments` deleted from the `--` to
end of line unconditionally, including inside the literal; that left an unterminated
quote, and `split_statements` then read every remaining character in the file - the
`DROP COLUMN`, its semicolon, everything - as string content. `parse_migration` returned
one `dml_update`.

The `DROP COLUMN` that breaks `q_billing_tax` was not missed, mis-severitied, or cleared
over a declared gap. It was never presented to a rule, to shadow replay, or to the
coverage ledger. On `rt2_01` the v13 pipeline finds 2 of the 4 labelled hazards and
reports confidently on the half of the migration it could see.

## R2: DDL inside `DO $$ ... $$`

The idempotency guard every migration generator writes. The retired splitter had no
concept of dollar quoting, so it cut the body at each inner semicolon and produced
fragments; the fragments landed as `unsupported`, which is a declared gap, so the packet
was not *silent* - it was wrong about what it had read, and it said nothing at all about
the `DROP COLUMN` inside.

`procedural_block` is now its own op kind, `sentinel/rulebook.py` has to classify it, and
`PROCEDURAL_DDL_UNREVIEWED` is raised from a keyword census over the body. The census is
deliberately not a parse, and the label for `rt2_02` says so: it carries all three hazards
a Postgres reviewer would name, two of which the pipeline still cannot find. Published
recall on that case is 1 of 3. Naming the block is not modelling it; what protects the
reviewer is that the case is not cleared.

## R3: the same defect with the sign flipped

Postgres nests block comments. A non-greedy `/* ... */` regex does not. So a superseded
statement commented out with a nested comment inside it left a live
`ALTER TABLE ... DROP COLUMN` after the first `*/`, and v13 **blocked a migration whose
destructive statement is switched off**, citing a broken query and a cross-service
coordination hazard, both with machine evidence, both about text Postgres never executes.

That is the sentence to sit with: every finding in that packet cited machine evidence.
Evidence is not the same property as being about the right file. `rt2_04` and `rt2_06`
are canaries and carry no hazard at all, because a tool that invents a blocker out of a
comment gets switched off, and a switched-off tool has recall zero.

## What shipped

* `sentinel/tools/sql_lex.py` - a scanner Postgres would recognise: `''` and `E'\'`
  escapes, `"` identifiers, `$tag$` bodies, line comments, **nested** block comments,
  statement spans, and unterminated constructs reported as facts with offsets rather than
  handled in silence;
* `sentinel/tools/parse_audit.py` - the subtraction: statements the scanner finds, minus
  statements an operation accounts for, plus a literal-masked census of every procedural
  body;
* two hazards (`MIGRATION_TEXT_UNPARSED`, `PROCEDURAL_DDL_UNREVIEWED`), three gap classes
  (`unattributed_statement`, `procedural_body`, `unreviewable_text`), one op kind
  (`procedural_block`), one ablation arm (`no_text_conservation`, which reproduces v13
  exactly, retired splitter included), 6 cases, 25 tests and 10 claims;
* the retired splitter is kept in the tree as `legacy_split_statements`, because it is the
  artefact under test: `parse_audit.legacy_loss` recomputes what it does to each file
  rather than asserting it.

On the round-2 set: recall 0.25 -> 0.75, precision 0.222 -> 1.0, false alarms 2 -> 0,
modelled reviewer minutes 21.0 -> 11.3.

## The two experiments this pass removed

**Reporting the wreckage.** The first version raised the unterminated-literal blocker
*and* the two hazards inferred from the mangled remainder. Postgres refuses that script
outright, so those two were claims about text that never runs - `rt2_04`'s defect exactly,
in the opposite direction. Now a script the server refuses reports only that it is refused,
and `unreviewable_text` names the region nobody could read. That is the difference between
precision 1.0 and 0.6 on this set.

**Censusing the raw source.** The first census read the migration text directly, which
made a `RAISE NOTICE 'about to drop table invoices'` inside a `DO` block into a
destructive finding. Every census now runs over literal-masked, comment-blanked scanner
output. There is a test for the notice.

## The number to read first

`no_text_conservation` reproduces v13 exactly and is **identical to `full` on all 28
labelled cases** in `eval/cases`, `eval/holdout` and `eval/redteam`: same verdicts, same
hazards, same severities, same gap counts, computed per case by `eval/run_redteam2.py`
rather than asserted. A splitter swapped out underneath 28 labelled cases without moving
one number is a splitter that was wrong only where nothing had ever looked. That is the
whole argument that this layer was missing rather than retuned.

## The hot take this pass earned

Four releases have now found the same defect one level up: the corpus is a sample of the
consumers (v1), the fixture is a sample of the data (v6), the rule set is a sample of the
hazards (v13), the parse is a sample of the text (v14). Each time the previous fix was
correct and its perimeter was invisible from inside, and each time the layer that should
have caught the new hole was itself built on the assumption the hole violated.

The generalisable move is not another honesty layer. It is **conservation**. Every stage
that transforms your input is a place where input disappears, and an audit that starts
after that stage cannot see the loss. So count what went in, count what came out, publish
the difference, and put the count in the same command as the tests. v13's arithmetic
subtracted coverage from the parse. This one subtracts the parse from the file. The next
one subtracts the file from the pull request, and I do not know yet what that costs.

And the sharper half, because it indicts the metric rather than the parser: **every single
false finding in the v13 packet cited machine evidence.** "Findings backed by machine
evidence: 35/35" has been the headline reproducibility number in this repository for
twelve releases, and it is true of a review of a file that was two thirds string literal.
Provenance tells you a claim came from a tool. It does not tell you the tool was looking
at the artefact you are about to deploy.
