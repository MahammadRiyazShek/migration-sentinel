# Judges start here

One page. Every rubric row, the file that answers it, and the command that proves it. Whole suite
runs in **under 10 seconds** for **$0.00**: standard library only, no `pip install`, no API key, no
network, synthetic data.

## Five commands, in order

```
git clone https://github.com/MahammadRiyazShek/migration-sentinel && cd migration-sentinel
python3 --version                                                       # 3.11+ (3.11 and 3.12 verified)
python3 -m sentinel review --case eval/cases/case_12_release_train.json  # one realistic execution
python3 eval/run_eval.py --ablations                                    # 9 arms x 12 cases = 108 reviews
python3 eval/model_invariance.py                                        # 180 reviews, 4 hostile models
python3 tools/check_results.py                                          # 27/27 claims re-asserted
```

Expected output, verified on a clean container (Python 3.12.13, no network):

| command | prints | wall clock |
|---|---|---|
| `sentinel review --case case_12` | `case_12_release_train: BLOCK (3 blocker / 5 high) -> results/case_12_release_train.md` | <0.1 s |
| `eval/run_eval.py --ablations` | baseline vs pipeline table, per-case detail, 9 ablation arms | 1.0 s |
| `eval/model_invariance.py` | 15 model/narrator arms, `surface_changed=0/12` on every one | ~4 s |
| `python3 -m unittest discover -s tests` | `Ran 33 tests ... OK` | 0.3 s |
| `tools/check_results.py` | `27/27 claims hold` | <1 s |

Nothing writes outside the repo. `sentinel review` never touches a database at all; `sentinel
execute` uses an in-memory SQLite sandbox and refuses to run without `--i-approve --reviewer "name"`.

## Rubric row to evidence

| row | weight | where it is answered | how to check it |
|---|---|---|---|
| Problem & user value | 15 | `README.md` -> "Who has this problem", "The bottleneck" | read; the user is the migration-review rota, the bottleneck is 20-40 min of evidence gathering per PR against 5 min of attention |
| Agent solution & engineering | 30 | `sentinel/orchestrator.py`, the five agent instructions in `sentinel/agents/prompts/`, `sentinel/coverage.py` (ledger), `sentinel/narrator.py` (the headline the model cannot write) | `sentinel review` on any case, then `results/ablation.md` for what each component is worth |
| End to end quality | 20 | `results/case_12_release_train.md` is the artifact a reviewer actually receives: verdict, hazards with machine evidence, expand/contract SQL, verification outcome, declared blind spots | open that file; then try `sentinel execute` without approval and watch it refuse |
| Measured improvement | 15 | `results/comparison.md`, `results/ablation.md`, `README.md` -> "Improvement Changelog" | `eval/run_eval.py --ablations` regenerates all of it |
| Reproducibility | 15 | `REPRODUCTION.md` (clean-environment walkthrough, versions, runtime, cost) | `tools/check_results.py` re-derives all 27 published claims from raw JSON |
| Hot take / insights | 5 | `README.md` -> "Hot take", `results/model_invariance.md` | `eval/model_invariance.py` |
| Deliverable 4: agent trajectories | - | `trajectories/*.jsonl` and `*.md` (per-case agent runs, tool calls, retries, human checkpoints), `docs/AGENT_TRAJECTORIES.md` (how to read them), `agent_traces/` (the human-plus-agent build sessions) | `docs/AGENT_TRAJECTORIES.md` first |

## If you only have five minutes

1. `results/comparison.md` - the fair-baseline table. Primary metric first: **0/12 unsafe approvals vs 1/12 for both baselines.**
2. `results/model_invariance.md` - four models built to sabotage the review; the decision surface moves in **0 of 168** completed reviews. Read the `hostile-fluent` / `pattern` row: a lie in ordinary professional English walked through v3's own blocklist onto 12 of 12 headlines while v3's metric for it read 0. v5's answer is provenance, not a longer blocklist: **0/48** misleading headlines reach the reviewer, and 0 of 60 headlines are model-written.
3. `docs/SUPERVISOR_LOG_V5.md` then `docs/SUPERVISOR_LOG_V4.md` - the things I still think are wrong with this, including the one that cannot be fixed without a second author.

## Honest scope, up front

Twelve cases, one schema, ground truth written by the author. Reviewer minutes are **modelled**, not
measured, and `eval/time_sensitivity.py` publishes the two constant sets that reverse the sign of that
one claim. Every other number in the submission is a count.
