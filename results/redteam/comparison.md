# Baseline vs agent pipeline

7 cases, identical inputs, identical hazard vocabulary. Primary metric first.

| metric | Baseline A (prompt only) | Baseline B (prompt + schema) | Agent pipeline |
|---|---|---|---|
| **Unsafe approvals** (primary, lower is better) | 1/7 | 1/7 | 0/7 |
| **Blocking cases given a clean verdict** (primary, lower is better) | 1/3 | 1/3 | 0/3 |
| Hazard recall (strict code) | 1.0 | 1.0 | 1.0 |
| Hazard precision (strict code) | 0.5 | 0.375 | 1.0 |
| Hazard F1 (strict code) | 0.667 | 0.545 | 1.0 |
| Hazard recall (hazard family) | 1.0 | 1.0 | 1.0 |
| Hazard precision (hazard family) | 0.5 | 0.375 | 1.0 |
| Severity agreement on matched hazards | 0.667 | 0.667 | 1.0 |
| False alarms on the clean case | 2 | 4 | 0 |
| Findings backed by machine evidence | 0/6 | 0/8 | 4/4 |
| Verified expand/contract plans produced | 0/7 | 0/7 | 7/7 |
| **Coverage-gap cases cleared without a sign-off** (lower is better) | 3/3 | 1/3 | 0/3 |
| Blind spots named in the packet, with the object | 0 | 0 | 3 |
| Modelled reviewer minutes per case | 22.7 | 29.6 | 7.6 |
| Wall clock per case (ms, measured) | 0.2 | 0.2 | 10.3 |
| Model tokens for all cases (measured) | 3872 | 7324 | 6471 |

Reviewer minutes are **modelled**, not measured, from these assumptions: read_review_minutes=5, verify_unevidenced_claim_minutes=4, write_expand_contract_plan_minutes=20, decide_human_gate_minutes=3. Wall clock and tokens are measured.

## Per-case detail (agent pipeline)

| case | ground truth | verdict | missed | false alarms | attempts | plan verified | coverage gaps |
|---|---|---|---|---|---|---|---|
| `rt_01_drop_index_still_used` | blocking | BLOCK | - | - | 1 | yes | - |
| `rt_02_concurrently_inside_transaction` | blocking | BLOCK | - | - | 1 | yes | - |
| `rt_03_drop_index_no_corpus_user` | non-blocking | NEEDS_COVERAGE_SIGNOFF | - | - | 1 | yes | unused_access_path |
| `rt_04_change_signup_default` | non-blocking | NEEDS_COVERAGE_SIGNOFF | - | - | 1 | yes | unruled_statement |
| `rt_05_relax_country_not_null` | non-blocking | NEEDS_COVERAGE_SIGNOFF | - | - | 1 | yes | unruled_statement |
| `rt_06_index_swap_inside_transaction` | blocking | BLOCK | - | - | 1 | yes | - |
| `rt_07_index_swap_done_right` | non-blocking | SAFE | - | - | 1 | yes | - |

## Per-case detail (baseline B, prompt + schema)

| case | verdict | missed | false alarms |
|---|---|---|---|
| `rt_01_drop_index_still_used` | APPROVE **(unsafe approval)** | - | - |
| `rt_02_concurrently_inside_transaction` | REQUEST_CHANGES | - | - |
| `rt_03_drop_index_no_corpus_user` | APPROVE | - | ACCESS_PATH_REMOVED |
| `rt_04_change_signup_default` | REQUEST_CHANGES | - | VIEW_BREAKAGE |
| `rt_05_relax_country_not_null` | REQUEST_CHANGES | - | VIEW_BREAKAGE |
| `rt_06_index_swap_inside_transaction` | REQUEST_CHANGES | - | ACCESS_PATH_REMOVED |
| `rt_07_index_swap_done_right` | APPROVE | - | ACCESS_PATH_REMOVED |
