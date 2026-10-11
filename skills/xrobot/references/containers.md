When to read this: Use when selecting a LibXR data structure for moving data between tasks, threads, and interrupts, and when diagnosing unexpected FULL or EMPTY results.

# Data structure selection

The concurrency-oriented containers live in `src/structure/` and are aggregated by `libxr.hpp`; the queue family is also reachable through `queue/queue.hpp`. Every operation returns immediately with an `ErrorCode` (or a boolean), so producers and consumers decide per call whether to drop, retry later, or restructure — the containers themselves hold no waiting logic.

## Main table

| Structure | Use when | Look elsewhere when | Key contract | Header |
| --- | --- | --- | --- | --- |
| `LatestSnapshot` | one producer publishes state, one consumer polls for the newest value (sensor to control loop) | every message must be consumed; more than one producer or consumer | `Store()` publishes, `LoadLatest(out)` reports whether a new value arrived; intermediate values are skipped; the value being copied stays intact | `src/structure/latest_snapshot.hpp` |
| `SPSCQueue` | FIFO between exactly one producer and one consumer (ISR to task streams) | several producers or consumers; payload alignment above `std::max_align_t` or non-trivially copyable payloads | lock-free; fixed-size trivially copyable payloads; batch submits are all-or-nothing | `src/structure/queue/spsc_queue.hpp` |
| `SlotPool` | a small pool of message slots shared by tasks and interrupts, with per-message drop or retry decisions | large pools (`Acquire`/`Take` scan the pool); NMI context | per-slot state machine `SLOT_FREE`, `SLOT_WRITING`, `SLOT_READY`, `SLOT_READING` driven by CAS; take order follows publish sequence; `Release` has no failure return | `src/structure/slot_pool.hpp` |
| `MPMCQueue` | bounded multi-producer multi-consumer FIFO whose callers tolerate and retry `FULL`/`EMPTY` | an interrupt must act on `FULL` immediately (transient false `FULL`/`EMPTY` mid-handover) | fixed trivially copyable and trivially destructible payloads; `Size()` is an approximation under concurrency | `src/structure/queue/mpmc_queue.hpp` |
| `ObjectPool` | one writer produces a large object that several readers consume at their own pace (camera frames, large packets) | overlapping `Acquire` calls on the same pool; construction or destruction inside an ISR | reference-counted slots; `Handle` is move-only writable, `ConstHandle` copyable read-only; the last release returns the slot | `src/structure/object_pool.hpp` |
| `Queue` | a plain FIFO touched by one context at a time, or guarded by external mutual exclusion | concurrent producers or consumers without external locking | byte ring with a fixed element size; `Push` on a full ring returns `FULL`, `Pop` on an empty one returns `EMPTY`; `Overwrite` replaces the content | `src/structure/queue/basic_queue.hpp` |

Other containers in `src/structure/`: `DoubleBuffer` (active and standby buffers for DMA or USB streaming), `List` and `LockFreeList` (linked lists), `RBTree` (ordered key lookup), and `Stack` (array-based, mutex-protected). `latest_snapshot.hpp` and `slot_pool.hpp` exist from LibXR v2.0.1; when a header is missing, compare the LibXR commit recorded in the First checks of SKILL.md with the v2.0.1 tag.

## LatestSnapshot

Capacity semantics: three slots of `T`, all seeded by the constructor `LatestSnapshot(const T& initial)`. The producer owns the back slot, the consumer the front slot, and one atomic handover moves the middle slot between them.

Context requirements: exactly one producer calls `Store(const T&)` and exactly one serialized consumer calls `LoadLatest(T& out)`; the calls may overlap across cores, threads, or interrupts. `T` must be copy constructible and copy assignable. The handover relies on a lock-free `std::atomic<uint32_t>`.

Behavior under preemption: consecutive `Store()` calls may overwrite the middle value the consumer has yet to take, while the slot being copied stays reserved — a load observes one complete value. `LoadLatest` returns true when a value arrived since the previous load; otherwise it returns false and `out` receives the previous value.

Typical misuse: two producers (for example two ISRs) calling `Store` — the three-slot handover assumes a single writer, and concurrent writers can tear a value and corrupt slot ownership; relying on every message arriving — skipping is the feature.

Reference: [LatestSnapshot](https://xrobot.work/docs/basic_coding/structure/latest_snapshot).

## SPSCQueue

Capacity semantics: constructed with a capacity `N`, the internal ring actually provides `N + 1` slots — one sentinel slot distinguishes full from empty.

Payloads and API: fixed size, trivially copyable, with `alignof(Data) <= alignof(std::max_align_t)` enforced by `static_assert`. `Push`/`Pop`/`Peek` move single elements; the batch variants report `FULL` or `EMPTY` and submit nothing on a shortfall; `PushWithWriter`/`PopWithWriter` fill or drain through callbacks and commit only the confirmed prefix; `ProduceWithWriter`/`ConsumeWithReader` expose up to two FIFO segments covering a ring wrap; `Reset` (consumer side) discards the queued payloads.

Context requirements: one producer and one consumer, in any contexts including interrupts; the lock-free handover makes progress under preemption.

Typical misuse: a second producer or consumer racing on the ring indexes; expecting the queue to manage payload lifetimes — it moves bytes into a fixed ring.

Reference: [SPSCQueue](https://xrobot.work/docs/basic_coding/structure/spsc_queue).

## SlotPool

Capacity semantics: a fixed number of preallocated slots; `Acquire` and `Take` scan the pool, so the structure targets a few to a few dozen slots.

API flow: `Acquire(index)` claims a free slot (`SLOT_FREE` to `SLOT_WRITING`, `ErrorCode::FULL` when the pool has none), the writer fills `At(index)` and calls `Publish(index)` (`SLOT_WRITING` to `SLOT_READY`, assigning a global publish sequence), `Take(index)` claims the `SLOT_READY` slot with the smallest sequence (`SLOT_READY` to `SLOT_READING`, `ErrorCode::EMPTY` when none is ready), and the reader calls `Release(index)` after reading. Releasing a slot claimed by `Acquire` and abandoned before `Publish` is a legal allocator pattern. `Put(value)` and `Get(out)` compress the flow into one call each for trivially copyable `T`.

Context requirements: producers and consumers in tasks and interrupts. A preempted operation holds only its own slot: other contexts keep claiming the remaining free slots, and a returned `FULL`/`EMPTY` reflects the pool state at that moment. The pool stays out of NMI context.

Ordering: per-publisher FIFO by publish sequence; a global FIFO across publishers is outside the contract.

Typical misuse: large pools (the scan dominates); treating take order as arrival order when several ISRs publish.

Reference: [SlotPool](https://xrobot.work/docs/basic_coding/structure/slot_pool).

## MPMCQueue

Capacity semantics: bounded, with a fixed payload type required to be trivially copyable and trivially destructible; elements move as byte blocks and the queue holds no interior pointers to payloads.

Context requirements: multiple producers and consumers in tasks and interrupts. `Size()` is an estimate while operations are in flight.

Behavior under preemption: on a single core, an operation preempted between claiming a slot and publishing it leaves other contexts observing a transient `FULL` or `EMPTY` — a queue with free space reports `FULL`, a queue with pending items reports `EMPTY`. Callers wait or retry afterwards; a high-priority task that receives `FULL`/`EMPTY` yields the CPU and retries instead of spinning; an interrupt skips loop retries and skips asserting that the enqueue succeeded. Where an interrupt reads or writes and must decide on `FULL` immediately, `SlotPool` matches better.

Typical misuse: dropping frames on a transient `FULL` — capacity exists while the preempted operation finishes; spinning on `FULL`/`EMPTY` from an interrupt.

Reference: [MPMCQueue](https://xrobot.work/docs/basic_coding/structure/mpmc_queue).

## ObjectPool

Capacity semantics: a fixed number of slots holding fully constructed `T` objects for the pool's lifetime; storage is internal or caller-provided, and no allocation happens at runtime. The per-slot reference count is bounded by `UINT32_MAX`.

API flow: `Acquire()` returns a move-only `Handle` with exclusive write access; moving it into a copyable, read-only `ConstHandle` publishes the object to readers. The last released reference returns the slot to the free stack (LIFO reuse). Release leaves the object contents in place — the next acquirer writes them.

Context requirements: one acquirer at a time per pool — overlapping or reentrant `Acquire` calls violate the contract (checked by `ASSERT` under `LIBXR_DEBUG_BUILD`). Final releases run concurrently from any thread or ISR and have no failure return; pool construction and destruction run outside interrupt context; ISR use assumes a 32-bit CAS platform.

Typical misuse: two threads calling `Acquire` concurrently — both can end up owning the same slot (ABA double ownership); holding a `ConstHandle` after its slot was fully released and handed to the next acquirer.

Reference: [ObjectPool](https://xrobot.work/docs/basic_coding/structure/object_pool).

## Queue

Capacity semantics: a byte ring with a fixed element size, using internal storage or a caller-provided buffer.

API: `Push`/`Pop`/`Peek` for single elements; batch variants report `FULL` (space shortfall) or `EMPTY` (data shortfall) and submit nothing partially; `Overwrite` clears the ring and writes one element; `operator[](int32_t)` indexes from the head with positive values and from the tail with negative ones.

Context requirements: one context at a time, or external mutual exclusion around every call — the ring moves bytes with plain reads and writes and leaves synchronization to the caller.

Typical misuse: an ISR and a task sharing a `Queue` without locking — the head and tail updates race and entries interleave.

Reference: [Queue](https://xrobot.work/docs/basic_coding/structure/queue).

## Scenario quick reference

- "A CAN RX interrupt receives frames; the control thread only needs the newest frame." — `LatestSnapshot`: the ISR calls `Store`, the control thread calls `LoadLatest`. When every frame must be processed, the ISR becomes the single producer of an `SPSCQueue`.
- "High-frequency ISR `Put`/`Get` with a larger slot count." — evaluate `SlotPool`: it serves interrupts directly, while `MPMCQueue` reports transient `FULL`/`EMPTY` when preempted on a single core; keep the pool small because `Acquire`/`Take` scan it.
- "Several tasks hand commands to one worker thread." — `MPMCQueue` when tasks retry on `FULL`; `SlotPool` when the sender needs an immediate, non-transient answer.
- "One task produces large frames that several tasks read independently." — `ObjectPool` to share one buffer behind reference-counted handles.
- "A history of readings consumed by a single logger task." — `SPSCQueue` for lock-free streaming; `Queue` when the logger is the only context touching the queue.

## What a wrong choice costs

- `MPMCQueue` plus an ISR that drops on `FULL`: frames disappear while free slots exist — the `FULL` was the transient state of a preempted operation, not real congestion.
- A plain `Queue` shared between an ISR and a task without locking: head and tail updates race, and entries interleave or vanish from the ring.
- `LatestSnapshot` with two producers: `Store` calls race on the three-slot handover: a value can tear and slot ownership can be corrupted, beyond a lost update, because the structure assumes a single writer.
- `SPSCQueue` with a second consumer: two consumers race on the head index, and frames are read twice or skipped.
- `ObjectPool` with overlapping `Acquire`: two owners claim one slot; `LIBXR_DEBUG_BUILD` flags it through `ASSERT`, release builds hand out double ownership.
- Asserting enqueue success on `MPMCQueue` inside an interrupt: the assertion fires on a transient `FULL` even though capacity exists.

Reference: [Data structures](https://xrobot.work/docs/basic_coding/structure) — index with selection notes for every structure; [ISR, callback, and thread boundaries](https://xrobot.work/docs/adv_coding/core/adv-coding-core-isr-thread-boundary) for the context rules behind the table.
