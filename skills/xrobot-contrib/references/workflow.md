When to read this: Planning or carrying out any change; the tiers below scale the record to the size of the change.

# Engineering workflow

The workflow runs work through five stages, scales the record to the size of the change, and attaches every conclusion to evidence through named gates. The stage-specific checklists live in the other reference files; this file holds the rules that span them.

## Stages

Work runs through five stages: design discussion, implementation, verification, review, and delivery. Each stage performs only its own work:

- A review request produces findings only.
- An implementation request ends at the local change. Pushing, opening a pull request, and merging happen only when the person making the request explicitly asks for them.
- Each stage needs its own approval: an approved design still goes through verification, and a change that passed verification still goes through review.

When the environment lacks a tool or a permission a stage needs, name the exact action that fills the gap — the command to run or the permission to request — and stop there.

## Work tiers

Scale the process and the record to the change:

- Direct answer or narrow review: answer from the references; read repository state only when the question needs it.
- Single-point change: verify the current state, make the minimal change, run one directly related check.
- Multi-file change or public-contract change: a task contract plus a before/after behavior comparison.
- Cross-repository work, on-board work, long-running work, or work likely to change hands: a task contract plus an itemized checklist. Create a run directory only when durable evidence with a named consumer is being produced.

## Task contract

Multi-file work and above maintain a short contract with these fields:

- the goal, the scope allowlist, and the non-goals;
- the allowed changes;
- the public behavior contract;
- the verification budget and the stop conditions;
- the decision ledger — accepted, rejected, and pending;
- the execution plane and the next action.

A blank or stale contract field is a hard stop: fill or refresh the field before continuing. After an interruption or a handoff, rebuild the current state from the contract before resuming.

## Design discussion

Before code moves, derive the plan from the explicit goal, the actual current behavior, and the real production users; choose implementation details only after that. Keep two records and update both after every discussion round:

- The discussion ledger, append-only and chronological: each correction, each rejected assumption, each open item.
- The current plan, holding only the conclusions in force: the interface and its return semantics, the owner and its context, status, competing scenarios, a user-compatibility table, accepted and pending decisions, verification requirements, and the implementation scope.

Implementation starts once the plan has maintainer agreement in the issue or pull-request discussion and no pending items remain.

## Ablation checks

Run an ablation pass at three points: when the plan is complete, when the implementation is complete, and before requesting review. Remove each abstraction, component, state, indirection, and side effect one at a time, and for each one name the concrete requirement, production user, or established fact that breaks without it.

- Nothing breaks: delete the part.
- The part exists only to compensate for another part's behavior: trace that root cause, write it down, and remove the compensation.
- The part bundles concerns that fail independently: split them.

Ablate the proposed fix as well: a root-cause fix keeps every real requirement satisfied without compensating parts. The report-done pass ablates everything the change added — each new file, fallback, branch, upstream or remote change — and names the consumer that breaks without it. Record the results in the discussion ledger.

## Public-interface gate

A change that existing callers can observe passes the public-interface checklist before implementation: enumerate production users, compare baseline and proposed behavior across the ten dimensions, and obtain explicit agreement for every difference no decision explains. The procedure is references/public-interface-checklist.md.

## Reset rules

A review conclusion, new evidence from production users, or a maintainer correction that changes the owner, the public interface, buffer ownership or lifetime, completion or error semantics, or a hardware premise invalidates the affected candidate and every piece of evidence that depends on it. Return to the design discussion and update the records there. Discard the old implementation regardless of its completeness, CI status, or time spent.

## Verification budget

Run the smallest check that can refute the current claim first. The full test matrix waits until the semantic gate passes: a public-behavior difference without an accepted decision produces matrix numbers with no decision attached. Do not repeat an accepted run whose sources, environment, and acceptance criteria are unchanged. Stop when the declared stop condition is reached. Retry a failure only after changing a material condition — the execution environment, the timeout or staging method, a disk or dependency precondition, the command, or the patch context. Do not count an identical retry as progress.

A check that goes green because a shared layer was bent to admit it did not pass. When a consumer does not fit the design, change or migrate that consumer, or stop and report; do not add a fallback or compatibility path, a loosened check, a moved version pin, or a glue file to LibXR, XRobot, the CodeGenerator or a BSP in order to make a build or a verification pass. Where such a bypass genuinely cannot be avoided, tell the maintainer before committing and state the consumer it serves and the condition for removing it.

## Testing and acceptance

Verification follows references/testing-and-acceptance.md: the eight-level evidence ladder, formal verification, host tests, CI, on-board acceptance, and experiment reporting. These rules govern every claim:

- Accept only evidence from the required path: on-board acceptance from an on-board run, backend proof from the backend, evidence built from the current code.
- Verify scenarios separately. Preview, recording, replay, rendering, and on-board runs are each their own scenario; a pass in one is evidence for that one, unless the person making the request explicitly links the scenarios.
- Before asking anyone for another physical action — a button press, a rewire, a power cycle — first obtain a way to observe the result (attaching a debugger without reset, reading registers, NMI or fault frames, capturing a log) and use it. Observation precedes repetition.

## Debug workflow

1. Reproduce the failure on the actual product path.
2. Capture the first divergent status, byte, register, frame, state transition, or log line.
3. State one falsifiable hypothesis and the smallest test that can reject it.
4. Run a same-input A/B comparison with one material variable changed.
5. Edit only after the divergence is localized.
6. Re-run the product acceptance path: a probe or a synthetic harness serves the diagnosis and never becomes the final proof.

Retries follow the verification budget: each one changes a material condition or brings new evidence.

## Tools and scripts

- Reuse repository-owned entry points before creating new tooling. Stable project-specific tools live in the repository's established `tools/` or `scripts/` directory.
- One-off probes and staged commands live in the task's run directory when one exists, otherwise in an OS temporary directory. Source trees and user startup locations stay free of them.
- A reusable script replaces a long inline shell chain when the logic may recur, changes system state, or needs checking.
- A reusable script opens with a header: purpose, usage, inputs, outputs and artifacts, prerequisites, side effects, idempotency, and examples.
- A script that deletes or overwrites defaults to a dry run and applies changes only on an explicit flag such as `--apply` or `--delete`.
- Long runs use strict error handling, explicit exit codes, bounded retries, and a machine-readable summary.
- Credentials, tokens, Wi-Fi material, private keys, and other secrets stay out of scripts, logs, manifests, and records.

## Environment cleanup

- Resolve every recursive move or delete target and confirm it sits inside the intended run, build, or workspace root before cleaning.
- Remove only task-owned temporary files, processes, ports, mounts, scheduled jobs, and devices; other people's changes and unrelated dirty worktrees stay intact.
- Stop the helpers the task started and confirm their processes and listeners are gone.
- Restore modified runtime configuration, device state, environment variables, and temporary routing, unless the retained state is an explicit deliverable.
- Keep rollback material until the new path passes acceptance; the last known-good artifact stays.
- End with `git status --short --branch`, the relevant process and port checks, and a list of the artifacts kept on purpose.

## Reusable material

- Promote repeated command logic into a repository-owned tool when the task's scope allowlist includes it; otherwise report it as a follow-up.
- Stable project rules enter repository documentation when the task's scope covers that change.
- Retain fixtures, reproducers, inputs, outputs, and environment metadata for a named future consumer only. Each retained run carries a concise human-readable summary and, when useful, a machine-readable manifest: artifact path, hash, baseline, scenario, result.
- Deduplicate before promoting: one maintained source replaces copied variants. Record the failure boundaries and the untested surfaces.

## Closing a task

- The acceptance path passed on the intended execution plane, and the checks the declared verification budget requires are recorded; a full build, a format run, a regression suite, and a hardware matrix are included when the budget names them.
- Task-owned background state and temporary files are cleaned or kept on purpose, and out-of-scope candidates are reported without being fixed.
- The delivery report states each delivery state separately (references/branches-and-releases.md, section "Delivery states").

## Review

Review is done by someone other than the implementer and the test-oracle author; its conclusions derive from before/after behavior, production users, and accepted decisions.

## Handoff and recovery

A long-running task, an interrupted task, or a task changing hands resumes from the task contract. Refresh the branch, the commits, the uncommitted changes, the current stage, the next action, and the open blockers before work continues.

## Baseline and contamination

Start work from a clean, isolated baseline. A shared dirty tree serves as read-only context unless the request explicitly targets that tree's files. Before touching state that version control does not track — device configuration, generated artifacts, firmware — make a dated backup copy. When out-of-scope changes turn up in the tree, stop and restart from a clean baseline instead of stacking work on top of them. The same rule handles a contaminated experiment tree that has accumulated several candidates, probes, and fixes: save the current diff as an artifact, rebuild the clean baseline, and re-apply only the single change the current hypothesis needs.

Repository cleanliness is part of the baseline: test data, copied project or board files, and new test infrastructure do not enter a product repository without the maintainer's approval — tests that run against real vendor projects belong to the repository designated for them and to the CI channel that already executes them.

## Branch hygiene

Keep the number of branches low: one active working branch at a time alongside `dev` and `master`. Delete a branch once its changes have merged, and do not recreate the old name of a branch that was renamed or moved — reference it by its new name. Repository-transfer and rename specifics, and the check for inbound links before deleting a branch, are in references/branches-and-releases.md.
