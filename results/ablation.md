# Ablation: which component actually does the work

Same 12 cases, same scripted model, one component removed at a time.

| configuration | unsafe approvals | recall (strict) | precision (strict) | severity agreement | verified plans | gaps cleared without sign-off |
|---|---|---|---|---|---|---|
| `full` | 0/12 | 0.97 | 0.97 | 0.969 | 12/12 | 0/2 |
| `no_replay` | 1/12 | 0.576 | 1.0 | 0.947 | 0/12 | 0/2 |
| `no_static` | 2/12 | 0.333 | 1.0 | 1.0 | 12/12 | 0/2 |
| `no_memory` | 0/12 | 0.97 | 0.97 | 0.938 | 12/12 | 0/2 |
| `no_verify` | 0/12 | 0.97 | 0.97 | 0.969 | 0/12 | 0/2 |
| `no_coverage` | 0/12 | 0.97 | 0.97 | 0.969 | 12/12 | 1/2 |
| `no_rule_coverage` | 0/12 | 0.97 | 0.97 | 0.969 | 12/12 | 0/2 |

Note: `no_replay` also disables plan verification, because the Verifier is the same replay tool pointed at the generated plan.
