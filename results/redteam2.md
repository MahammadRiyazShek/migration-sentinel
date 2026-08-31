# Red team, round 2: migrations the parser gets wrong

Round 1 asked whether there was a hazard class nobody enumerated. The answer was yes, twice, and the fix was `sentinel/rulebook.py`: an exhaustive partition of every statement kind the parser can emit, with a test that fails when it learns a new one. Exhaustive over the op list.

This round asked whether the op list is the migration.

```sql
UPDATE invoices SET currency = 'usd -- legacy default' WHERE currency IS NULL;
ALTER TABLE invoices DROP COLUMN tax_rate;
```

Two statements in. One op out. `strip_comments` deleted from the `--` inside the string literal to end of line, the unterminated quote that left swallowed the rest of the file, and the `DROP COLUMN` that breaks a live billing query was never presented to a rule, to shadow replay or to the coverage ledger. It was not missed. It was not there.

Across these 6 files the retired splitter loses **2 statement(s)** outright and invents **6 statement(s)** that Postgres never executes, recomputed from the retired code itself by `sentinel.tools.parse_audit.legacy_loss`.

## The result

| metric | Baseline A | Baseline B | Sentinel v13 | Sentinel v14 |
|---|---|---|---|---|
| **Hazard recall** (primary) | 0.375 | 0.375 | **0.25** | **0.75** |
| **Hazard precision** (primary) | 0.5 | 0.25 | **0.222** | **1.0** |
| Unsafe approvals | 0/6 | 0/6 | 0/6 | 0/6 |
| Blocking cases given a clean verdict | 0/3 | 0/3 | 0/3 | 0/3 |
| False alarms on the three correct migrations | 1 | 3 | 2 | 0 |
| Findings backed by machine evidence | 0/6 | 0/12 | 17/17 | 6/6 |
| Blind spots named, with the object | 0 | 0 | 5 | 5 |
| Gap cases cleared without a sign-off | 0/2 | 0/2 | 0/2 | 0/2 |
| Modelled reviewer minutes per case | 22.3 | 33.0 | 21.0 | 11.3 |

`Sentinel v13` is the `no_text_conservation` ablation arm, which reproduces the shipped v13 pipeline exactly, retired splitter included. Note where its findings went: 17/17 of them, every one citing machine evidence, and 0.222 precision. Evidence is not the same property as being about the right file.

## The number to read first, because this set is in sample

The v14 scanner was written from these probes. The generalisation evidence runs the other way and is computed from the three ablation files rather than asserted here:

> `no_text_conservation` and `full` are identical on **28 of 28** labelled cases in `eval/cases`, `eval/holdout` and `eval/redteam`: same verdict, same true positives, same false positives, same misses, same gap count. Cases that moved: 0.

A splitter swapped out underneath 28 labelled cases without moving one number is a splitter that was wrong only where nothing had ever looked.

## Per case

| case | ground truth | v13 verdict | v14 verdict | v14 findings | v14 gaps | statements v13 saw |
|---|---|---|---|---|---|---|
| `rt2_01_comment_marker_inside_literal` | blocking | BLOCK | BLOCK | BREAKING_QUERY, CROSS_SERVICE_UNCOORDINATED, DESTRUCTIVE_NO_EXPAND_CONTRACT, UNBATCHED_BACKFILL | in_place_data_mutation | 1 of 2 |
| `rt2_02_do_block_hides_the_drop` | blocking | NEEDS_COVERAGE_SIGNOFF | BLOCK | PROCEDURAL_DDL_UNREVIEWED | procedural_body | 3 of 1 |
| `rt2_03_unterminated_literal` | blocking | BLOCK | BLOCK | MIGRATION_TEXT_UNPARSED | in_place_data_mutation, unreviewable_text | 1 of 1 |
| `rt2_04_nested_comment_phantom` | non-blocking | BLOCK | SAFE | - | - | 2 of 1 |
| `rt2_05_function_body_no_ddl` | non-blocking | NEEDS_COVERAGE_SIGNOFF | NEEDS_COVERAGE_SIGNOFF | - | procedural_body | 5 of 2 |
| `rt2_06_ordinary_migration_with_quotes` | non-blocking | BLOCK | SAFE | - | - | 1 of 2 |

## The two cases that make this a test rather than a demonstration

`rt2_02` is labelled with all three hazards a Postgres reviewer would name, including the two the pipeline still cannot find. A keyword census over a `DO $$ ... $$` body proves DDL is in there; it does not model what the block does with it, so `BREAKING_QUERY` and `DESTRUCTIVE_NO_EXPAND_CONTRACT` stay in the label as published misses. Recall on that case is 1 of 3. What protects the reviewer is that the case is not cleared: naming the block caps the verdict and names a human gate.

`rt2_04` and `rt2_06` are the canaries and carry no hazard at all. v13 blocks both: on `rt2_04` from a `DROP COLUMN` sitting inside a nested comment, on `rt2_06` from a string default containing a double hyphen. Three of its findings on those two files describe text Postgres never runs.

## What this cost

-9.7 modelled reviewer minutes per case against the v13 arm on this set, all of it in named sign-offs. On the 28 labelled cases it costs nothing, because it fires on nothing there.

Commands, from a clean clone, no key and no network:

```bash
python3 eval/build_redteam2.py           # regenerate the 6 round-2 cases
python3 eval/run_redteam2.py              # 6 cases x 10 arms + this report
```

