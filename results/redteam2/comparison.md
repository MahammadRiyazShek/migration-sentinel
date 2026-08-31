# Baseline vs agent pipeline

6 cases, identical inputs, identical hazard vocabulary. Primary metric first.

| metric | Baseline A (prompt only) | Baseline B (prompt + schema) | Agent pipeline |
|---|---|---|---|
| **Unsafe approvals** (primary, lower is better) | 0/6 | 0/6 | 0/6 |
| **Blocking cases given a clean verdict** (primary, lower is better) | 0/3 | 0/3 | 0/3 |
| Hazard recall (strict code) | 0.375 | 0.375 | 0.75 |
| Hazard precision (strict code) | 0.5 | 0.25 | 1.0 |
| Hazard F1 (strict code) | 0.429 | 0.3 | 0.857 |
| Hazard recall (hazard family) | 0.429 | 0.714 | 0.714 |
| Hazard precision (hazard family) | 0.5 | 0.417 | 1.0 |
| Severity agreement on matched hazards | 1.0 | 1.0 | 1.0 |
| False alarms on the clean case | 1 | 3 | 0 |
| Findings backed by machine evidence | 0/6 | 0/12 | 6/6 |
| Verified expand/contract plans produced | 0/6 | 0/6 | 5/6 |
| **Coverage-gap cases cleared without a sign-off** (lower is better) | 0/2 | 0/2 | 0/2 |
| Blind spots named in the packet, with the object | 0 | 0 | 5 |
| Modelled reviewer minutes per case | 22.3 | 33.0 | 11.3 |
| Wall clock per case (ms, measured) | 0.2 | 0.2 | 11.5 |
| Model tokens for all cases (measured) | 3452 | 6513 | 7226 |

Reviewer minutes are **modelled**, not measured, from these assumptions: read_review_minutes=5, verify_unevidenced_claim_minutes=4, write_expand_contract_plan_minutes=20, decide_human_gate_minutes=3. Wall clock and tokens are measured.

## Per-case detail (agent pipeline)

| case | ground truth | verdict | missed | false alarms | attempts | plan verified | coverage gaps |
|---|---|---|---|---|---|---|---|
| `rt2_01_comment_marker_inside_literal` | blocking | BLOCK | - | - | 1 | yes | in_place_data_mutation |
| `rt2_02_do_block_hides_the_drop` | blocking | BLOCK | BREAKING_QUERY, DESTRUCTIVE_NO_EXPAND_CONTRACT | - | 1 | yes | procedural_body |
| `rt2_03_unterminated_literal` | blocking | BLOCK | - | - | 2 | NO - escalated | in_place_data_mutation, unreviewable_text |
| `rt2_04_nested_comment_phantom` | non-blocking | SAFE | - | - | 1 | yes | - |
| `rt2_05_function_body_no_ddl` | non-blocking | NEEDS_COVERAGE_SIGNOFF | - | - | 1 | yes | procedural_body |
| `rt2_06_ordinary_migration_with_quotes` | non-blocking | SAFE | - | - | 1 | yes | - |

## Per-case detail (baseline B, prompt + schema)

| case | verdict | missed | false alarms |
|---|---|---|---|
| `rt2_01_comment_marker_inside_literal` | REQUEST_CHANGES | BREAKING_QUERY, CROSS_SERVICE_UNCOORDINATED | VIEW_BREAKAGE |
| `rt2_02_do_block_hides_the_drop` | REQUEST_CHANGES | BREAKING_QUERY, PROCEDURAL_DDL_UNREVIEWED | VIEW_BREAKAGE |
| `rt2_03_unterminated_literal` | REQUEST_CHANGES | MIGRATION_TEXT_UNPARSED | DESTRUCTIVE_NO_EXPAND_CONTRACT, UNBATCHED_BACKFILL, VIEW_BREAKAGE |
| `rt2_04_nested_comment_phantom` | REQUEST_CHANGES | - | DESTRUCTIVE_NO_EXPAND_CONTRACT, VIEW_BREAKAGE |
| `rt2_05_function_body_no_ddl` | REQUEST_CHANGES | - | VIEW_BREAKAGE |
| `rt2_06_ordinary_migration_with_quotes` | REQUEST_CHANGES | - | VIEW_BREAKAGE |
