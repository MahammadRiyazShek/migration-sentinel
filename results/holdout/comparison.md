# Baseline vs agent pipeline

9 cases, identical inputs, identical hazard vocabulary. Primary metric first.

| metric | Baseline A (prompt only) | Baseline B (prompt + schema) | Agent pipeline |
|---|---|---|---|
| **Unsafe approvals** (primary, lower is better) | 1/9 | 1/9 | 0/9 |
| **Blocking cases given a clean verdict** (primary, lower is better) | 1/7 | 1/7 | 0/7 |
| Hazard recall (strict code) | 0.52 | 0.56 | 0.96 |
| Hazard precision (strict code) | 1.0 | 0.737 | 1.0 |
| Hazard F1 (strict code) | 0.684 | 0.636 | 0.98 |
| Hazard recall (hazard family) | 0.533 | 0.8 | 0.933 |
| Hazard precision (hazard family) | 1.0 | 0.857 | 1.0 |
| Severity agreement on matched hazards | 0.769 | 0.714 | 0.958 |
| False alarms on the clean case | 0 | 1 | 0 |
| Findings backed by machine evidence | 0/13 | 0/19 | 26/26 |
| Verified expand/contract plans produced | 0/9 | 0/9 | 9/9 |
| **Coverage-gap cases cleared without a sign-off** (lower is better) | 1/4 | 1/4 | 0/4 |
| Blind spots named in the packet, with the object | 0 | 0 | 6 |
| Modelled reviewer minutes per case | 26.3 | 33.4 | 10.7 |
| Wall clock per case (ms, measured) | 0.2 | 0.2 | 11.1 |
| Model tokens for all cases (measured) | 4468 | 10093 | 19134 |

Reviewer minutes are **modelled**, not measured, from these assumptions: read_review_minutes=5, verify_unevidenced_claim_minutes=4, write_expand_contract_plan_minutes=20, decide_human_gate_minutes=3. Wall clock and tokens are measured.

## Per-case detail (agent pipeline)

| case | ground truth | verdict | missed | false alarms | attempts | plan verified | coverage gaps |
|---|---|---|---|---|---|---|---|
| `holdout_01_service_level_not_null` | blocking | BLOCK | - | - | 1 | yes | - |
| `holdout_02_composite_unique_invoices` | blocking | BLOCK | - | - | 1 | yes | - |
| `holdout_03_rename_table_behind_view` | blocking | BLOCK | - | - | 1 | yes | - |
| `holdout_04_safe_additive_language` | non-blocking | SAFE | - | - | 1 | yes | - |
| `holdout_05_drop_status_check` | non-blocking | SAFE_WITH_PLAN | - | - | 1 | yes | - |
| `holdout_06_audit_trigger` | blocking | NEEDS_COVERAGE_SIGNOFF | TRIGGER_WRITE_AMPLIFICATION | - | 1 | yes | unmodelled_statement |
| `holdout_07_narrow_invoice_amount` | blocking | NEEDS_COVERAGE_SIGNOFF | - | - | 1 | yes | fixture_bounded_value_scan |
| `holdout_08_release_train_fleet` | blocking | BLOCK | - | - | 1 | yes | uncovered_object, in_place_data_mutation, unmodelled_statement |
| `holdout_09_drop_employment_type` | blocking | NEEDS_COVERAGE_SIGNOFF | - | - | 1 | yes | uncovered_object |

## Per-case detail (baseline B, prompt + schema)

| case | verdict | missed | false alarms |
|---|---|---|---|
| `holdout_01_service_level_not_null` | REQUEST_CHANGES | BREAKING_QUERY | VIEW_BREAKAGE |
| `holdout_02_composite_unique_invoices` | REQUEST_CHANGES | - | - |
| `holdout_03_rename_table_behind_view` | REQUEST_CHANGES | BREAKING_QUERY, CROSS_SERVICE_UNCOORDINATED | - |
| `holdout_04_safe_additive_language` | REQUEST_CHANGES | - | VIEW_BREAKAGE |
| `holdout_05_drop_status_check` | REQUEST_CHANGES | - | VIEW_BREAKAGE |
| `holdout_06_audit_trigger` | APPROVE **(unsafe approval)** | TRIGGER_WRITE_AMPLIFICATION | - |
| `holdout_07_narrow_invoice_amount` | REQUEST_CHANGES | TYPE_NARROWING_DATA_LOSS | - |
| `holdout_08_release_train_fleet` | REQUEST_CHANGES | BREAKING_QUERY, CROSS_SERVICE_UNCOORDINATED, SELECT_STAR_DRIFT, TABLE_REWRITE_LOCK | VIEW_BREAKAGE |
| `holdout_09_drop_employment_type` | REQUEST_CHANGES | CROSS_SERVICE_UNCOORDINATED, SELECT_STAR_DRIFT | VIEW_BREAKAGE |
