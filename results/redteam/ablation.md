# Ablation: which component actually does the work

Same 7 cases, same scripted model, one component removed at a time.

| configuration | unsafe approvals | recall (strict) | precision (strict) | severity agreement | verified plans | gaps cleared without sign-off |
|---|---|---|---|---|---|---|
| `full` | 0/7 | 1.0 | 1.0 | 1.0 | 7/7 | 0/3 |
| `no_replay` | 0/7 | 1.0 | 1.0 | 1.0 | 0/7 | 0/3 |
| `no_static` | 3/7 | 0.0 | 1.0 | 0.0 | 7/7 | 0/3 |
| `no_memory` | 0/7 | 1.0 | 1.0 | 1.0 | 7/7 | 0/3 |
| `no_verify` | 0/7 | 1.0 | 1.0 | 1.0 | 0/7 | 0/3 |
| `no_coverage` | 0/7 | 1.0 | 1.0 | 1.0 | 7/7 | 3/3 |
| `no_rule_coverage` | 3/7 | 0.0 | 1.0 | 0.0 | 7/7 | 3/3 |

Note: `no_replay` also disables plan verification, because the Verifier is the same replay tool pointed at the generated plan.
