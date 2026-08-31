# Video addendum: what changed after the recording

The submitted video was recorded against v2. The repo is v10. Nothing in the video is wrong about the
problem, the architecture, the baseline comparison or the walkthrough; some on-screen numbers are stale
and three components did not exist yet: the coverage gate, the structural narrator and the held-out
world on the second schema. **When video and repo disagree, `results/comparison.md` and
`results/model_invariance.md` are authoritative.**

## Corrections, exhaustive

| on screen (v2) | in the repo now (v10) | why it moved |
|---|---|---|
| ablation table with 8 arms | 9 arms, 108 reviews | the coverage gate became its own ablation arm |
| reviewer minutes/case **8.5** | **9.2** | the coverage gate turns every declared blind spot into a human gate, and that costs time. The number went up on purpose and is published as it fell out |
| "coverage-gap cases cleared without sign-off" absent | second primary metric, **0/2** | v2 could say "ship as plan" above its own declared blind spot without the scorer calling it an unsafe approval |
| no hostile-model section | `results/model_invariance.md`: **180 reviews**, 4 hostile models, 3 narrator modes | v2 argued invariance from the shape of the code. v3 measured it, found the decision surface unmoved and the *prose* fully compromised. v5 attacked v3's own guard and broke it |
| the headline is written by the model | the headline is a pure function of tool output | a model that lies in words v3's blocklist never learned printed above a `BLOCK` badge on 12/12 cases while v3's metric for it read 0. Model prose is now demoted below the evidence and labelled |
| 22 tests, 18 claims | **52 tests, 44 claims** | two hostile-model iterations, a held-out schema and a submission-text audit, each pinned by tests and by `tools/check_results.py` |
| no held-out evaluation | `results/holdout/`: **9 cases on a second schema**, rules hashed before the labels existed | in-sample numbers on rules and labels written by the same person are worth what the freeze is worth |

Everything else in the video (problem, baseline A/B, one full execution, changelog narration) still
matches the repo.

## If you re-record: 90-second delta clip script

Screen recording, no editing needed. Append to the existing video or upload separately and link both.

**0:00-0:10 - why there is an addendum.** "This clip covers what changed after the main video: two new
components, one number that got worse on purpose, and a bug I found inside my own fix."

**0:10-0:28 - the coverage gate.** Show `results/case_12_release_train.md`, scroll to the coverage
ledger. "The review declares what it structurally could not observe: unmodelled statements, rows
rewritten in place, a value class the rollback cannot restore. Any open gap caps the verdict at
NEEDS_COVERAGE_SIGNOFF, which is not an approval and not executable. It invents no hazard, so precision
and recall do not move, and reviewer minutes go from 8.5 to 9.2. It is the only component that makes
this pipeline look worse on a published number."

**0:28-0:55 - the hostile models, and the one that beat me.** Run `python3 eval/model_invariance.py`.
"Five models, three narrator modes, 180 reviews. The decision surface changes in zero of 168 completed
reviews. But look at hostile-fluent under the v3 guard: it writes ordinary professional English with no
banned phrase in it, and the guard printed 'this can ride the normal release train' above a BLOCK badge
on 12 of 12 cases - while the column that was supposed to catch that read zero, because the audit used
the same regexes as the guard."

**0:55-1:20 - the fix.** Run `python3 -m sentinel review --case
eval/cases/case_02_drop_column_still_read.json --provider hostile-fluent --print-report`. "Same hostile
model, shipped build. The headline is now rendered from the tool output, so no model writes it: zero of
sixty model-written headlines. Its paragraph is still in the packet, at the bottom, under 'Model
commentary, unverified prose, not evidence', after the reader has met the hazards it is inviting them
to ignore."

**1:20-1:30 - the lesson and the proof.** Run `python3 tools/check_results.py`, hold on
`27/27 claims hold`. "A defence audited in its own vocabulary reports on the attacker's imagination,
not on itself. Prefer a property you can check over a pattern you have to keep up to date - and if
removing components will not find that bug, write a component that lies to you on purpose."

## If you do not re-record

The description carries the disagreement notice and this file is the exhaustive diff, which is what the
completeness gate needs: judges are told which artifact wins before either can mislead them.
