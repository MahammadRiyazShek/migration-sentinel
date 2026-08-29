# Agent trajectories

Every `review` run writes two files per case:

* `trajectories/<case>.md` - readable trajectory: each agent's goal and instructions, every tool call
  with its arguments and response, every model call with its cost, the feedback that changed the next
  step, retries, and the human checkpoints
* `trajectories/<case>.jsonl` - the same events as structured records, one per line

Agent instructions live in [`sentinel/agents/prompts/`](../sentinel/agents/prompts/). Each trajectory
names the agent whose instruction file drove it, so you can read the instruction and the behaviour
side by side.

## The five agents and what to look for

| agent | instructions | what it does | tools it calls |
|---|---|---|---|
| Cartographer | `prompts/cartographer.md` | parses DDL + migration into an exact change set; unparsed statements become explicit unknowns | `schema.parse`, `migration.parse`, `schema.apply_ops` |
| Blast Radius | `prompts/blast_radius.md` | static dependents, then shadow replay; only replay may create a blocker | `corpus.dependents`, `corpus.blast_score`, `shadow.replay` |
| Risk Officer | `prompts/risk_officer.md` | lock/volume/intent rules, memory escalation, merge, verdict | `memory.escalation` |
| Rollout Engineer | `prompts/rollout_engineer.md` | writes the expand/contract plan as SQL, lists human gates | (model for reviewer questions) |
| Verifier | `prompts/verifier.md` | re-parses and replays the generated plan; feeds failures back | `migration.parse`, `schema.apply_ops`, `shadow.replay` |

## Recommended reading order

1. **[`case_01_rename_with_compat_view.md`](../trajectories/case_01_rename_with_compat_view.md)** -
   the full loop including a retry. Start here.
2. **[`case_12_release_train.md`](../trajectories/case_12_release_train.md)** - the hard case: six
   changes, four blockers, and a statement the parser cannot model surfacing as a coverage gap
   instead of a silent pass.
3. **[`case_06_safe_unique_index.md`](../trajectories/case_06_safe_unique_index.md)** - the clean
   case. Worth reading to confirm the pipeline can say "nothing here" in 20 events.

## Walkthrough: case_01, including the retry

The interesting sequence, quoted from the trajectory:

**1. Cartographer** parses two statements into `rename_column(customers.full_name -> name)` and
`create_view(customer_billing_summary)`. No opinions, just structure.

**2. Blast Radius** calls `corpus.dependents` (6 candidate statements, weighted score 17) and then
`shadow.replay`. The tool responds with reproduced failures:

```
q_web_profile   OperationalError: no such column: full_name
q_web_signup    OperationalError: table customers has no column named full_name
q_bi_summary    column set changed: removed ['full_name'], added ['name']
```

Note what happened here: the compatibility view in the migration did not save the application. The
agent did not deduce that, it observed it.

**3. Risk Officer** adds what replay cannot see (single-step rename, missing rollback, cross-service
impact) and calls `memory.escalation`, which returns `INC-2023-09` for a rename on a table this team
has been burned on before, and `INC-2025-02` for BI column drift. Verdict: `BLOCK`.

**4. Rollout Engineer**, attempt 1, produces a phase 1 of: add `name`, batched backfill, and (because
the migration contained it) the replacement view definition.

**5. Verifier** replays that plan and hands back:

```
phase 1 is not safe yet: q_bi_summary (bi): column set changed, removed ['full_name']
```

This is a genuine regression in the generated plan, caught by the same tool that found the original
problem. The orchestrator logs the feedback, tightens the policy
(`include_view_changes = False`) and retries.

**6. Rollout Engineer**, attempt 2, moves the view redefinition to phase 2 and adds the code step
"point readers at the new definition before phase 2 replaces it".

**7. Verifier** replays again: all 16 statements pass. Phase 1 is verified.

**8. Human checkpoint** is recorded, not requested-and-assumed:

```
### Human checkpoint - pre-execution approval: REQUIRED
Nothing has been executed against any real database. `sentinel execute` runs phase 1 against a
local sandbox copy only, and refuses to run without --i-approve plus the reviewer's name.
```

## Where the human is in the loop

Three distinct checkpoints, all visible in the trajectories:

1. **Escalation** (`human_checkpoint: plan verification / ESCALATED`) when the retry budget runs out.
   Reproduce it with `max_attempts=1` on case_01; there is a test for it.
2. **Human gates** inside the plan: dedupe rules, truncation rules, observation windows, cutover
   timing. The pipeline names them and refuses to decide them.
3. **Pre-execution approval**, enforced in code. `sentinel execute` exits 2 without
   `--i-approve --reviewer "name"`, and exits 3 on a `BLOCK` verdict unless a named reviewer
   overrides it on the record.
