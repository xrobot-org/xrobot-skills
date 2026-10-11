When to read this: Read this checklist before changing any LibXR public surface — API, owner, state machine, backend, lifecycle — or any change that existing callers can observe.

# Public interface change checklist

The same LibXR headers serve bare-metal loops, RTOS tasks, interrupt handlers, and host processes. A change that looks local — one new return code, one extra retry, one reordered callback — becomes a contract change for every caller on every context. The steps below turn that comparison into a fixed procedure so observable differences surface before the code lands.

Reference material: [advanced coding: core](https://xrobot.work/docs/adv_coding/core), [RW semantics](https://xrobot.work/docs/adv_coding/core/adv-coding-core-rw-semantics), [ISR/thread boundary](https://xrobot.work/docs/adv_coding/core/adv-coding-core-isr-thread-boundary).

## Before touching code

For a public-contract change, write down three things first, then start the code:

1. **Current behavior.** The return codes, blocking and completion semantics, ownership, and call contexts the contract has today. Source this from the current code and real production callers, not from candidate tests or memory.
2. **Production users.** Every real caller and backend that depends on the behavior surface, listed one by one. List tests separately: tests document usage and expectations, and they do not count as users.
3. **Proposed behavior.** The delta, item by item. Each new return code, new blocking condition, completion meaning change, callback count/order/reentry change, and ownership or lifetime change gets its own line with a reason.

Scale the record to the change: a narrow change may need a short snapshot; public API, concurrency, lifecycle, backend, or cross-module changes need full coverage of the three items. Any baseline-versus-proposal difference without explicit authorization is a stop.

## The ten dimensions

Compare the baseline behavior, the proposed behavior, and the authorized behavior across all ten dimensions for every changed public surface. A difference that no authorization explains blocks the change.

1. **Return codes and capacity.** Enumerate the return-code set and the capacity limits before and after. Flag every new `BUSY`, `FULL`, `TIMEOUT`, or `FAILED`-class code, and every change to capacity queries such as `ReadPort::Capacity()` returning 0 while unbound.
2. **Payload visibility and ordering.** What data becomes visible to the other side, in what order, with which possibilities for loss, duplication, or replay. WritePort copies payload into its ring at admission, so the moment bytes become visible to the backend is part of the contract.
3. **Partial acceptance and consumption.** Request boundaries: WritePort `FULL` accepts nothing, Stream appends are all-or-nothing, a ReadQueue `PushBatch` writes the whole batch or returns `FULL`. A switch to prefix acceptance is a semantic change even when the happy path looks identical.
4. **Blocking, timeout, wakeup, and progress.** New blocking conditions, timeout detach behavior, wakeup mechanisms, and forward-progress guarantees. A timed-out BLOCK call returns after progress stops touching the buffer, which can exceed the requested timeout — preserve that class of property when touching the path.
5. **Completion meaning and callbacks.** What "complete" means (UART TX completion means the data is staged into the controller, with the wire state left to the backend), plus callback count, order, reentry results, and the context a callback runs in.
6. **Buffer ownership and lifetime.** Who owns each buffer at each point, when it becomes invalid, who releases it. WritePort releases the source buffer at admission; a ReadPort destination stays valid until completion or cancellation.
7. **Cancellation, teardown, recovery, and disabled state.** Behavior of `ClearQueuedData`, `FailFront`, pause/resume, and suspended backends; a configured-but-suspended backend still admits capacity-legal writes and delays completion, and the checklist applies to that state too.
8. **Task, callback, ISR, and core context.** The `in_isr` parameter surface, task-only BLOCK operations, and per-structure ISR limits (see the concurrency contracts in `coding-conventions.md`).
9. **Source compatibility, ABI, and layout.** Header-visible types, enum values, and struct layout. `OperationPollingStatus` is backed by `uint32_t` on purpose; changing an underlying width changes the ABI.
10. **Hardware side effects and Flash/RAM cost.** Peripheral state left behind, DMA and cache effects, and the code and data size delta.

## Authorization

Each of the following requires maintainer agreement in the issue or pull-request discussion before implementation starts — the plan carries agreement and no pending items, the same gate as the design stage in `references/workflow.md` — and an explicit statement of the difference in the pull request before merge:

- a new `BUSY` / `FULL` / `TIMEOUT` / `FAILED`-class return code on an existing path;
- a new blocking condition, or a change to timeout detach semantics;
- a change to what completion means, or to callback count, order, or reentry results;
- a change to ownership, lifetime, or call-context constraints.

A change to what an existing interface means adds its own requirement: the old usage must stop compiling or fail loudly at generation or configure time — a `static_assert`, a deleted overload, an explicit error — and every known user migrates in the same change set. Users that cannot migrate are listed for the maintainer before merge. An old form that keeps compiling with a new meaning — a callback parameter narrowed from a payload view to a concrete payload type, for example — compiles its way into a debug assert, or into undefined behavior in a release build.

State in the PR which of the ten dimensions change, the evidence for the baseline, and the production users affected. A green build or a mergeable state does not settle semantics; the recorded authorization does.

## Where the baseline comes from

Behavior baselines come from, in descending order of authority:

1. explicit maintainer decisions and accepted public contracts;
2. accepted baseline behavior in merged code, plus the public documentation;
3. platform and hardware evidence from measurements on the target;
4. current production usage.

Candidate tests cannot create requirements. A test expectation (oracle) must come from an authorized baseline, public documentation, hardware evidence, or an explicit maintainer decision. A test whose oracle is sourced from the diff under review proves internal consistency, and it proves nothing about contract correctness.

## Worked example

A proposal changes WritePort from returning `FULL` when the queue is full to dropping the oldest queued request instead:

- Dimension 1: `FULL` disappears from the return set on that path.
- Dimension 2: previously queued bytes vanish — a loss the old contract excluded.
- Dimension 5: dropped requests need a completion story (no notification, an error, or a cancellation), and each option is a callback-semantics decision.
- Dimension 6: dropped payload buffers change lifetime expectations for callers that reuse a buffer once its request completes.

Four dimensions move, so the change needs explicit maintainer sign-off and a production-user enumeration before implementation — even though the diff itself may be a few lines.

## Reset when premises change

A reset is due when an authoritative semantic discovery, evidence from current production users, or a maintainer correction changes any of: the owner, the public API, buffer ownership or lifetime, completion semantics, error behavior, resource origin, or hardware assumptions. Then:

1. Invalidate the affected conclusions and every piece of evidence that depends on them.
2. Stop patching the old candidate; keep it only as a counterexample.
3. Restate the contract from the correction and return to the design step before writing code.

Discard the old candidate regardless of its completeness, CI status, or time spent.
