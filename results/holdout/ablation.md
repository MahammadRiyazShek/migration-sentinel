# Ablation: which component actually does the work

Same 9 cases, same scripted model, one component removed at a time.

| configuration | unsafe approvals | recall (strict) | precision (strict) | severity agreement | verified plans | gaps cleared without sign-off |
|---|---|---|---|---|---|---|
| `full` | 0/9 | 0.96 | 1.0 | 0.958 | 9/9 | 0/4 |
| `no_replay` | 0/9 | 0.56 | 1.0 | 1.0 | 0/9 | 0/4 |
| `no_static` | 0/9 | 0.32 | 1.0 | 0.875 | 9/9 | 0/4 |
| `no_memory` | 0/9 | 0.96 | 1.0 | 0.958 | 9/9 | 0/4 |
| `no_verify` | 0/9 | 0.96 | 1.0 | 0.958 | 0/9 | 0/4 |
| `no_coverage` | 1/9 | 0.96 | 1.0 | 0.958 | 9/9 | 3/4 |
| `no_rule_coverage` | 0/9 | 0.96 | 1.0 | 0.958 | 9/9 | 0/4 |

Note: `no_replay` also disables plan verification, because the Verifier is the same replay tool pointed at the generated plan.
