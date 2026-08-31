# Red team: migrations written to make this pipeline approve an outage

`eval/cases` asks whether the pipeline finds the hazards I thought of. `eval/holdout` asks whether it finds them on a schema the rules were never written against. Neither can ask whether there is a class of hazard **nobody enumerated**, because both were labelled from the same hazard vocabulary, and a vocabulary is a list of what you already know.

So this set was written the other way round: find a migration a Postgres primary would call an outage and this pipeline calls SAFE. Six probes, two hits. Neither hit was a wrong rule. Both were absent rules that nothing in this repository was counting.

## The result

| metric | Baseline A | Baseline B | Sentinel v12 | Sentinel v13 |
|---|---|---|---|---|
| **Unsafe approvals** (primary) | 1/7 | 1/7 | **3/7** | **0/7** |
| **Blocking cases given a clean verdict** (primary) | 1/3 | 1/3 | **3/3** | **0/3** |
| Hazard recall (strict code) | 1.0 | 1.0 | 0.0 | 1.0 |
| Hazard precision (strict code) | 0.5 | 0.375 | 1.0 | 1.0 |
| False alarms on the two correct migrations | 2 | 4 | 0 | 0 |
| Findings backed by machine evidence | 0/6 | 0/8 | 0/0 | 4/4 |
| Blind spots named, with the object | 0 | 0 | 0 | 3 |
| Gap cases cleared without a sign-off | 3/3 | 1/3 | 3/3 | 0/3 |
| Modelled reviewer minutes per case | 22.7 | 29.6 | 5.9 | 7.6 |

`Sentinel v12` is the `no_rule_coverage` ablation arm, which reproduces the shipped v12 pipeline exactly. It approved every one of these 7 migrations.

## The number to read first, because this set is in sample

The v13 rules were written from these probes, so these seven cases prove two holes are closed - not that the pipeline generalises. The generalisation evidence runs the other way, and it is computed from the two ablation files rather than asserted here:

> `no_rule_coverage` and `full` are identical on **21 of 21** labelled cases in `eval/cases` and `eval/holdout`: same verdict, same true positives, same false positives, same misses, same gap count. Cases that moved: 0.

A layer that moves no number that was already being measured is a layer that was missing. A layer tuned to fit the cases it was shown would have moved several.

## What the baseline did better than the v12 pipeline, and why that is the point

On `rt_02` and `rt_06` the text-only baseline names `CONCURRENT_DDL_IN_TRANSACTION` and the v12 pipeline does not. `BEGIN` and `CONCURRENTLY` in one file is a famous string, and a reviewer who reads the diff sees both. The v12 pipeline could not, and the reason is structural rather than accidental: every rule in `agents/risk_officer.py` was written to cover something *shadow replay is blind to*, so the rule set inherited the shape of replay's blind spots instead of the shape of the hazard space. Locks, volume, intent - all three are properties of one statement. Nothing in the design ever asked about a property of two.

Baseline B pays for that reach on `rt_03`: it flags the index drop nothing uses, at `medium`, with no evidence and no way to tell the difference. That is the whole trade in one pair of cases. Naming a hazard is cheap; deciding is what costs.

## Per case

| case | ground truth | v12 verdict | v13 verdict | v13 findings | v13 coverage gaps |
|---|---|---|---|---|---|
| `rt_01_drop_index_still_used` | blocking | SAFE | BLOCK | ACCESS_PATH_REMOVED | - |
| `rt_02_concurrently_inside_transaction` | blocking | SAFE | BLOCK | CONCURRENT_DDL_IN_TRANSACTION | - |
| `rt_03_drop_index_no_corpus_user` | non-blocking | SAFE | NEEDS_COVERAGE_SIGNOFF | - | unused_access_path |
| `rt_04_change_signup_default` | non-blocking | SAFE | NEEDS_COVERAGE_SIGNOFF | - | unruled_statement |
| `rt_05_relax_country_not_null` | non-blocking | SAFE | NEEDS_COVERAGE_SIGNOFF | - | unruled_statement |
| `rt_06_index_swap_inside_transaction` | blocking | SAFE | BLOCK | CONCURRENT_DDL_IN_TRANSACTION | - |
| `rt_07_index_swap_done_right` | non-blocking | SAFE | SAFE | - | - |

`rt_07` is the canary. It is a correct migration, and every arm has to stay quiet on it; the first version of the v13 rules did not, and neither did the first version of the residual-gap class, which flagged `case_06` as well. Both failures are recorded in `sentinel/rulebook.py` rather than deleted.

## What this cost

The two new rules and the two new gap classes cost 1.7 modelled reviewer minutes per case on this set, all of it in named human sign-offs on the three cases where the honest answer is a gap rather than a finding. On the 21 labelled cases it costs nothing at all, because it fires on nothing there.

Commands, from a clean clone, no key and no network:

```bash
python3 eval/build_redteam.py            # regenerate the 7 red-team cases
python3 eval/run_redteam.py               # 7 cases x 9 arms + this report
```

