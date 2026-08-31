# Baseline vs agent pipeline

12 cases, identical inputs, identical hazard vocabulary. Primary metric first.

| metric | Baseline A (prompt only) | Baseline B (prompt + schema) | Agent pipeline |
|---|---|---|---|
| **Unsafe approvals** (primary, lower is better) | 1/12 | 1/12 | 0/12 |
| **Blocking cases given a clean verdict** (primary, lower is better) | 1/9 | 1/9 | 0/9 |
| Hazard recall (strict code) | 0.545 | 0.606 | 0.97 |
| Hazard precision (strict code) | 0.947 | 0.69 | 0.97 |
| Hazard F1 (strict code) | 0.692 | 0.645 | 0.97 |
| Hazard recall (hazard family) | 0.636 | 0.864 | 0.955 |
| Hazard precision (hazard family) | 0.933 | 0.792 | 0.955 |
| Severity agreement on matched hazards | 0.611 | 0.55 | 0.969 |
| False alarms on the clean case | 1 | 1 | 0 |
| Findings backed by machine evidence | 0/19 | 0/29 | 35/35 |
| Verified expand/contract plans produced | 0/12 | 0/12 | 12/12 |
| **Coverage-gap cases cleared without a sign-off** (lower is better) | 0/2 | 0/2 | 0/2 |
| Blind spots named in the packet, with the object | 0 | 0 | 3 |
| Modelled reviewer minutes per case | 29.7 | 34.7 | 9.2 |
| Wall clock per case (ms, measured) | 0.3 | 0.2 | 9.7 |
| Model tokens for all cases (measured) | 5837 | 11577 | 25967 |

Reviewer minutes are **modelled**, not measured, from these assumptions: read_review_minutes=5, verify_unevidenced_claim_minutes=4, write_expand_contract_plan_minutes=20, decide_human_gate_minutes=3. Wall clock and tokens are measured.

## Per-case detail (agent pipeline)

| case | ground truth | verdict | missed | false alarms | attempts | plan verified | coverage gaps |
|---|---|---|---|---|---|---|---|
| `case_01_rename_with_compat_view` | blocking | BLOCK | - | - | 2 | yes | - |
| `case_02_drop_column_still_read` | blocking | BLOCK | - | - | 1 | yes | - |
| `case_03_index_on_hot_table` | blocking | BLOCK | - | - | 1 | yes | - |
| `case_04_not_null_without_default` | blocking | BLOCK | - | CROSS_SERVICE_UNCOORDINATED | 1 | yes | - |
| `case_05_unique_email_with_duplicates` | blocking | BLOCK | - | - | 1 | yes | - |
| `case_06_safe_unique_index` | non-blocking | SAFE | - | - | 1 | yes | - |
| `case_07_drop_check_constraint` | non-blocking | SAFE_WITH_PLAN | - | - | 1 | yes | - |
| `case_08_narrowing_country_code` | blocking | BLOCK | - | - | 1 | yes | - |
| `case_09_unbatched_backfill` | non-blocking | NEEDS_COVERAGE_SIGNOFF | CROSS_SERVICE_UNCOORDINATED | - | 1 | yes | value_class_erased |
| `case_10_add_fk_constraint` | blocking | BLOCK | - | - | 1 | yes | - |
| `case_11_swap_view_used_by_worker` | blocking | BLOCK | - | - | 1 | yes | - |
| `case_12_release_train` | blocking | BLOCK | - | - | 1 | yes | in_place_data_mutation, unmodelled_statement |

## Per-case detail (baseline B, prompt + schema)

| case | verdict | missed | false alarms |
|---|---|---|---|
| `case_01_rename_with_compat_view` | REQUEST_CHANGES | BREAKING_QUERY, CROSS_SERVICE_UNCOORDINATED, SELECT_STAR_DRIFT | VIEW_BREAKAGE |
| `case_02_drop_column_still_read` | REQUEST_CHANGES | BREAKING_QUERY, CROSS_SERVICE_UNCOORDINATED, SELECT_STAR_DRIFT | VIEW_BREAKAGE |
| `case_03_index_on_hot_table` | REQUEST_CHANGES | - | - |
| `case_04_not_null_without_default` | REQUEST_CHANGES | BREAKING_QUERY | VIEW_BREAKAGE |
| `case_05_unique_email_with_duplicates` | REQUEST_CHANGES | - | - |
| `case_06_safe_unique_index` | REQUEST_CHANGES | - | UNIQUE_VIOLATION_EXISTING_DATA |
| `case_07_drop_check_constraint` | REQUEST_CHANGES | - | VIEW_BREAKAGE |
| `case_08_narrowing_country_code` | REQUEST_CHANGES | TYPE_NARROWING_DATA_LOSS | VIEW_BREAKAGE |
| `case_09_unbatched_backfill` | REQUEST_CHANGES | CROSS_SERVICE_UNCOORDINATED | VIEW_BREAKAGE |
| `case_10_add_fk_constraint` | REQUEST_CHANGES | - | VIEW_BREAKAGE |
| `case_11_swap_view_used_by_worker` | APPROVE **(unsafe approval)** | BREAKING_QUERY, CROSS_SERVICE_UNCOORDINATED | - |
| `case_12_release_train` | REQUEST_CHANGES | BREAKING_QUERY, TABLE_REWRITE_LOCK | VIEW_BREAKAGE |
