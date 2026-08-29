# Ablation: which component actually does the work

Same 12 cases, same scripted model, one component removed at a time.

| configuration | unsafe approvals | recall (strict) | precision (strict) | severity agreement | verified plans |
|---|---|---|---|---|---|
| `full` | 0/12 | 0.939 | 0.969 | 0.968 | 12/12 |
| `no_replay` | 1/12 | 0.545 | 1.0 | 0.944 | 0/12 |
| `no_static` | 2/12 | 0.333 | 1.0 | 1.0 | 12/12 |
| `no_memory` | 0/12 | 0.939 | 0.969 | 0.935 | 12/12 |
| `no_verify` | 0/12 | 0.939 | 0.969 | 0.968 | 0/12 |

Note: `no_replay` also disables plan verification, because the Verifier is the same replay tool pointed at the generated plan.
