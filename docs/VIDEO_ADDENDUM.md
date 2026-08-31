# Video addendum: what changed after the recording

The submitted video was recorded against v2. The repo is v3+. Nothing in the video is wrong about the
architecture or the baseline comparison; three on-screen numbers are stale, and one component did not
exist yet. When video and repo disagree, `results/comparison.md` and `results/model_invariance.md`
are authoritative.

## Corrections, exhaustive

| on screen (v2) | in the repo now (v3) | why it moved |
|---|---|---|
| ablation table with 8 arms | 9 arms, 108 reviews | the coverage gate became its own ablation arm |
| reviewer minutes/case **8.5** | **9.2** | the coverage gate turns every declared blind spot into a human gate, and that costs time. The number went up on purpose and is published as it fell out |
| "coverage-gap cases cleared without sign-off" absent | second primary metric, **0/2** | v2 could say "ship as plan" above its own declared blind spot without the scorer calling it an unsafe approval |
| no hostile-model section | `results/model_invariance.md`, 96 reviews, three hostile models | v2 argued invariance from the shape of the code; v3 measured it, found the decision surface unmoved (0/84) and the *prose* fully compromised (11/12 sycophantic headlines) |

Everything else in the video (problem, baseline A/B, one full execution, changelog narration) still
matches the repo.

## If you re-record: 75-second delta clip script

Total 75 s, screen recording, no editing needed. Append to the existing video or upload separately and
link both.

**0:00-0:12 - why there is an addendum.** "This clip covers three days of changes made after the main
video. Two new components and one number that got worse on purpose."

**0:12-0:32 - the coverage gate.** Show `results/case_12_release_train.md`, scroll to the coverage
ledger. "The review declares what it structurally could not observe: unmodelled statements, rows
rewritten in place, a value class the rollback cannot restore. Any open gap caps the verdict at
NEEDS_COVERAGE_SIGNOFF, which is not an approval and not executable. It invents no hazard, so
precision and recall do not move, and reviewer minutes go from 8.5 to 9.2. It is the only component
that makes this pipeline look worse on a published number."

**0:32-0:58 - the hostile models.** Run `python3 eval/model_invariance.py`. "Three models that are
not trying to help: a sycophant, an injected one, a dead endpoint. 96 reviews. The decision surface
changes in zero of 84 completed reviews. But with the guard off, the sycophant printed 'Approved, safe
to ship' under a badge reading BLOCK on 11 of 12 cases, and no metric I had could see it, because
every metric read the decision surface and the reviewer reads the sentence at the top. The dead
endpoint crashed 12 of 12 runs on a missing dict key."

**0:58-1:15 - the lesson and the proof.** Run `python3 tools/check_results.py`, hold on `23/23 claims
hold`. "A system can be invariant in every number it publishes and still lie to the person reading
it. Audit the output your user actually reads. And if removing components will not find that bug,
write a component that lies to you on purpose."

## If you do not re-record

The description already carries the disagreement notice, and this file is the exhaustive diff. That is
enough for the completeness gate: judges are told which artifact wins before they can be misled by
the other.
