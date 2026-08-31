# Ablation: which component actually does the work

Same 6 cases, same scripted model, one component removed at a time.

| configuration | unsafe approvals | recall (strict) | precision (strict) | severity agreement | verified plans | gaps cleared without sign-off |
|---|---|---|---|---|---|---|
| `full` | 0/6 | 0.75 | 1.0 | 1.0 | 5/6 | 0/2 |
| `no_replay` | 0/6 | 0.5 | 1.0 | 1.0 | 0/6 | 0/2 |
| `no_static` | 0/6 | 0.125 | 0.5 | 1.0 | 5/6 | 0/2 |
| `no_memory` | 0/6 | 0.75 | 1.0 | 1.0 | 5/6 | 0/2 |
| `no_verify` | 0/6 | 0.75 | 1.0 | 1.0 | 0/6 | 0/2 |
| `no_coverage` | 0/6 | 0.75 | 1.0 | 1.0 | 5/6 | 0/2 |
| `no_rule_coverage` | 0/6 | 0.75 | 1.0 | 1.0 | 5/6 | 0/2 |

Note: `no_replay` also disables plan verification, because the Verifier is the same replay tool pointed at the generated plan.
