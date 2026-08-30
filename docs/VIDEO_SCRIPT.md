# Solution video: shot list and script (target 4:40)

Record with `results/` and `trajectories/` already generated, terminal on the left, the review packet
on the right. Every number spoken is on screen.

## 0:00 - 0:35 | The problem, with a real PR

Show the two-statement migration from `case_01`.

> "A product engineer renames a column and updates the reporting view in the same migration. Two
> statements. It looks self-contained. To review it honestly I need to know which of the fourteen
> statements our services issue touch that column, whether anything reads `SELECT *` off that view,
> how big the table is, and who deploys the code that breaks. That is twenty to forty minutes. It
> gets five."

## 0:35 - 1:15 | The simple baseline

Run it live:

```bash
python baseline/baseline_review.py --case eval/cases/case_01_rename_with_compat_view.json \
    --variant prompt_with_schema --print-review
```

> "One prompt, the migration, the schema, the same hazard vocabulary. It catches the rename. It does
> not catch that the profile page and the signup insert both stop working, because it cannot look
> that up. And it has no evidence for anything it says."

Then run it on `case_11` and let it say `APPROVE` on a migration that drops a view a worker reads
every minute. That is the failure this project exists to remove.

## 1:15 - 2:45 | One realistic execution, start to finish

```bash
python -m sentinel review --case eval/cases/case_01_rename_with_compat_view.json --print-report
```

Walk the packet top to bottom:

* the `BLOCK` banner and the two reproduced failures, reading one engine error out loud
* the silent one: `q_bi_summary` still runs, column set changed, `INC-2025-02` cited from memory
* the phase 1 / phase 2 plan, the rollback, the code steps between phases
* the human gates and the "what this review did not check" section

Then open `trajectories/case_01_rename_with_compat_view.md` and scroll to the retry:

> "The Rollout Engineer's first plan swapped the view in phase one. The Verifier replayed it and
> handed back: `q_bi_summary, column set changed, removed full_name`. Its own plan had the same bug
> as the original migration. Policy tightened, regenerated, replayed, sixteen of sixteen passing."

Finish with the gate:

```bash
python -m sentinel execute --report results/case_01_rename_with_compat_view.json \
    --case eval/cases/case_01_rename_with_compat_view.json
# REFUSED
```

## 2:45 - 3:40 | The comparison

Run `python eval/run_eval.py --ablations` on camera. It finishes in under a second.

Show `results/comparison.md`: unsafe approvals 1/12 and 1/12 versus 0/12, recall 0.55 and 0.61 versus
0.94, evidence 0 of 19 findings versus 34 of 34, verified plans 0 versus 12, modelled reviewer minutes
30 versus 9.2.

> "Same twelve cases, same vocabulary, same scorer. Reviewer minutes are modelled from assumptions
> you can read and disagree with in `eval/scoring.py`. Everything else is measured."

## 3:40 - 4:25 | Changelog: what actually helped, and what I removed

Show the changelog table, then the ablation table.

> "The change that contributed most was pairing execution with static rules. Look at the replay-only
> row: two unsafe approvals, worse than rules alone, because a lock hazard fails nothing. Execution
> only reports what breaks, and the expensive hazards break nothing.
>
> The experiment I removed: my first drift check flagged any change to a `SELECT *` result set,
> additions included. It fired on every single `ADD COLUMN`. It taught me that a reviewer who gets a
> HIGH for every added column stops reading, and a tool nobody reads has a recall of zero. It is a
> note in the trajectory now, not a hazard.
>
> And the honest one: memory changed no verdicts. It moved severity agreement from 0.935 to 0.968. I
> nearly cut it, and kept it because severity is what decides whether a change waits for a
> maintenance window."

## 4:25 - 4:40 | Failure mode and close

> "The failure mode is that the corpus is the world. Case nine's real risk is a dbt model that is not
> in the corpus, and case twelve contains a `CLUSTER` statement my parser does not model. Both are
> missed on purpose, and both show up in the packet as unmodelled or unchecked, because a tool that
> quietly narrows its own scope launders a gap into a green check.
>
> Clone it, run `python eval/run_eval.py`. No key, no network, one second, same numbers."


---

## v2 addendum (30 seconds, drop in after the changelog beat)

> "One more row, and it is the only one that makes the tool look worse. Case 09 used to come back
> SHIP AS PLAN with a declared blind spot printed underneath it. Reviewers read badges, not
> appendices. So the coverage ledger now caps the verdict: NEEDS COVERAGE SIGNOFF, the object named,
> the gap marked irreversible, and the CLI refuses to run it. It moves no detection metric. It adds
> reviewer minutes. Under adversarial constants it reverses the sign of my best number, and that
> reversal is published in results/time_sensitivity.md rather than repriced away. A sensor that
> reports its own blind spot has not finished the job until the blind spot can change the answer."

Show on screen: `results/case_09_unbatched_backfill.md` (the coverage ledger table), then the
`no coverage gate` row of `results/components.md`.
