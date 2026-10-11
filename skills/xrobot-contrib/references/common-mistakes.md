When to read this: An execution went off the rails — task drift, wrong branch or effective parameters, failed controls, stale GitHub state, an at-risk working tree, an out-of-scope discovery, an overturned conclusion, or a register, build, or tool claim that does not hold up.

Each entry pairs a symptom with the recovery. The shared pattern: stop, refresh the live baseline (branch, state, parameters, original request), then regenerate the work on the correct plane; do not extend or defend artifacts produced under the wrong conditions.

## Task drift

Symptom: the work in progress answers something other than the original request — a different goal, branch, data source, artifact, or topic than the task defines, with effort still flowing into artifacts produced on the wrong plane.

Handling: stop the current run. Refresh the task baseline: repository and branch, current goal, scenario or data source, expected evidence, and acceptance criteria; re-read the original request and the live `git status --short --branch`. Regenerate the artifacts on the correct plane rather than arguing for or building on the ones from the wrong one.

## Wrong branch or effective parameters

Symptom: results come from a different branch, commit, dirty state, or parameters than assumed; requested values and tool or runtime outputs disagree.

Handling: before branch-sensitive work, check the live state — `git status --short --branch`, HEAD, and the parameters actually in effect. On discovery of a mismatch, stop interpreting the results. Record the repository root, branch, HEAD, dirty state, artifact hashes, requested parameters, and effective parameters. Treat that run as invalid until the configuration is corrected, rerun on the corrected plane, and report the invalid run alongside the valid one.

## Failed control or contaminated experiment tree

Symptom: the known-good control fails in the current environment, or one tree accumulates several candidate changes, probes, and fixes so that no single variable explains a result.

Handling: a failing control stops the comparison. Restore the last known-good harness and preconditions, and prove the control passes again before changing one variable at a time. A contaminated tree: stop patching, save the current diff as an artifact, rebuild a clean baseline, re-apply only the single change for the current hypothesis, and record the patch and its hash. Conclusions drawn against an invalid baseline are void; re-establish them from a new controlled run instead of reinterpreting the old numbers.

## An overturned conclusion or premise

Symptom: a review conclusion, evidence from current production users, or a maintainer correction changes the owner, the public interface, buffer ownership or lifetime, completion or error semantics, or a hardware premise — work in progress rests on a statement that no longer holds.

Handling: the reset itself is `references/workflow.md`, Reset rules — what is invalidated, what stops being patched, and which record carries the restated contract. Refresh the premise, then continue from the reset step rather than from the point the old conclusion reached.

## GitHub state has changed

Symptom: the tracked state is stale — a PR was merged or closed, a branch was deleted, checks or reviews are outdated — and the next action is planned from the old record.

Handling: refresh the live state before acting: base and head refs with SHAs, PR status (open, draft, mergeable), checks, reviews, and branch existence. Stale records — old review comments, old screenshots — do not constitute evidence of the current state. Treat each GitHub action as a separate change: editing a PR description is a different action from merging, merging is a different action from releasing, and deleting one branch authorizes nothing about other refs. After a change, re-read the remote object and verify the SHA, the status, and the side effects, such as issue auto-close or source-branch deletion.

## Clearing other people's changes

Symptom: the working tree contains uncommitted changes from someone else or from a parallel session, and a reset, clean, or stash would remove them; modifications appear in the tree that the current task did not make.

Handling: run no `git reset --hard`, `git clean`, or `git stash` over uncommitted changes that the task did not create. Treat unknown changes as a question, not an obstacle to remove: stop and ask before touching them. Cleanup stays limited to the files, processes, and state that the current task produced, and unrelated dirty state stays intact.

## Out-of-scope findings

Symptom: while working inside the authorized scope, a defect or problem appears outside it — another module, another platform, a tool or CI issue.

Handling: report it as a finding with location, reproduction, and evidence, and leave the fix to its owner. Do not fold unrelated fixes into the current change, and do not widen the diff. Reusable follow-up suggestions belong in the report, not in the branch.

## Code and build claims

The task-level disciplines — baseline hygiene, verification budget, retry conditions, the ablation pass — are in `references/workflow.md`. The entries below cover claims made about code and builds, where the evidence behind a statement does not carry it.

### Register-model claims

Symptom: a driver or a document takes register behavior from an SVD entry — a field assumed read-clear, a reset value used as the model, an SDK line quoted without its SoC directory — and the hardware disagrees with the build.

Handling: the SVD enumerates peripherals, registers and addresses. Read-clear, write-1-to-clear and other side-effect semantics come from the reference manual, the errata, and the SDK implementation; an SVD reset value carries no modeling weight. Order of authority for register semantics: errata, then the SDK HAL implementation, then official examples, then the documented cross-part differences. An SDK citation gives the full path inside the SoC's directory tree, because same-named files differ in line numbers across SoCs and a manual section quoted across dies is a mis-citation. A tally of unresolved points counts independent sources, and the same document read twice counts once.

### Read-once status fields

Symptom: recovery logic reads a bus-error code, or two contexts poll the same status field, and every read after the first reports NoChange — the value each reader needed is already consumed.

Handling: check the field's access type before designing recovery. HPM MCAN `PSR.LEC` and `DLEC` are read-set: each CPU read returns the code and resets the field, and the hardware clears the error state after an error-free frame, so no clear API is missing. Read once per event, act on that read, and keep no cached copy re-polled from another context.

### A bound that is never read

Symptom: a timeout or spin budget sits in the code and limits nothing — the counter decrements while no branch tests it, or a wait loop never compares against a deadline — so a stalled peripheral leaves the caller inside the loop.

Handling: a bound exists where the loop reads it. A polling path tests the bound each iteration and returns an error code when it expires; an interrupt path bounds the wait by time or by a conservative iteration count, with one policy across similar paths in the same driver. A wait that does not return inside an ISR stops the subsystem that owns the interrupt.

### A source file CI never compiled

Symptom: a file added under a globbed directory stays out of the target in an existing build directory; a reference to it fails at link time and the error names the caller. A deleted file leaves a stale path behind. CI passes because every run configures from scratch.

Handling: a directory that downstream work adds or removes files in uses `file(GLOB ... CONFIGURE_DEPENDS)` or lists its sources explicitly; several platform `CMakeLists.txt` files in [xrobot-org/libxr](https://github.com/xrobot-org/libxr) glob without it. A green CI run says nothing about an existing build directory.

### A freshness check red on one host

Symptom: a check comparing generated files against a stored hash or expectation fails on Windows and passes on Linux CI for identical content.

Handling: a fixture hashed from raw bytes must not inherit the writing tool's line-ending conversion — CMake's `file(WRITE)` emits CRLF on Windows where the stored expectation was computed with LF. Write the bytes deterministically or normalize line endings before hashing. Recomputing the constant on the failing host moves the failure to the other platform.

### Filtered tool output

Symptom: a build, flash, or test transcript looks clean while the failure that explains the result was removed by the command's own filtering.

Handling: diagnose from unfiltered output. Lines dropped by `grep`, a pipeline, or a tail limit leave no evidence, and a filtered summary cannot support a claim of absence. Keep the full output in the run artifact and summarize from it.

## When to escalate to maintainers

- A public-behavior difference has no accepted decision behind it — a new error code, a new blocking condition, or a changed completion, callback, ownership, or call-context semantic. Propose it explicitly in the PR and reach agreement before relying on it.
- A control or baseline cannot be brought to a passing state after environment fixes, so no A/B conclusion is possible from the current harness.
- A fix requires touching shared CI workflows, release tooling, or the release-line and lock semantics (`xrobot.lock`, `--release-ref`, the shared workflow tags).
- Ownership of an unknown change is unclear, or a destructive recovery (reset, clean, force push) looks necessary to proceed.
- Evidence conflicts with the documented or accepted behavior of the library. Report the divergence with the first divergence point and its artifacts rather than patching around it.
