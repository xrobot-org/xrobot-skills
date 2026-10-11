When to read this: Read this when writing or reviewing LibXR C++ code — error handling, ISR rules, concurrency containers, port semantics, drivers, formatting, comments, and docs.

# LibXR coding conventions

Reference material: [basic coding](https://xrobot.work/docs/basic_coding), [advanced coding](https://xrobot.work/docs/adv_coding), [contribution guides](https://xrobot.work/docs/con_guide). Repository: <https://github.com/xrobot-org/libxr>.

## Error codes and assertion strategy

`ErrorCode` (`src/core/libxr_def.hpp`) is an `int8_t`-backed enum class with `PENDING`, `OK`, `FAILED`, `INIT_ERR`, `ARG_ERR`, `STATE_ERR`, `SIZE_ERR`, `CHECK_ERR`, `NOT_SUPPORT`, `NOT_FOUND`, `NO_RESPONSE`, `NO_MEM`, `NO_BUFF`, `TIMEOUT`, `EMPTY`, `FULL`, `BUSY`, `PTR_NULL`, `OUT_OF_RANGE`. Return an error code when the caller can recover; keep normal error return paths recoverable.

Three assertion macros with different evaluation behavior:

| Macro | Purpose | Enabled by | When disabled |
| --- | --- | --- | --- |
| `ASSERT` / `ASSERT_FROM_CALLBACK` | caller parameters and fixed configuration | `LIBXR_DEBUG_BUILD` | expression still evaluated, result unchecked |
| `DEV_ASSERT` / `DEV_ASSERT_FROM_CALLBACK` | internal development checks on library-owned state | `LIBXR_DEV_ASSERT_BUILD` (CI turns it on) | expression removed entirely |
| `REQUIRE` / `REQUIRE_FROM_CALLBACK` | unrecoverable resource, initialization, and exit-path failures | always compiled in | — |

`LIBXR_DEBUG_BUILD` is a plain CMake variable recomputed at each configure from the build type (Debug=ON) unless set explicitly; `LIBXR_DEV_ASSERT_BUILD` is a CMake option, independent of it. The test suite covers the on/off combinations of both, so a checked expression must stay safe to evaluate under every configuration.

Decision rules:

- A condition that cannot trigger once code and configuration are correct goes to `ASSERT`. Otherwise it goes to `REQUIRE`, or to a returned error code when the caller can recover.
- HAL/SDK call results on library-owned state go to `DEV_ASSERT`.
- Pick one mechanism per condition: asserting and returning an error for the same condition duplicates the contract.
- Place the operation outside the check; a checked expression carries no required side effects, since `ASSERT` still evaluates it when disabled and `DEV_ASSERT` drops it.
- Unrecoverable failures go through `libxr_fatal_error(file, line, in_isr)`: it loops forever; in ISR context it writes a null pointer so the hardware fault stops the core; in thread context it prints through STDIO when available, runs the fatal callback registered via `LibXR::Assert::RegisterFatalErrorCallback`, and sleeps in a loop.
- Library code emits diagnostics through the `XR_LOG_*` macros (Logger). STDIO output happens only through user-driven paths (user code, a user-configured Logger) and through `libxr_fatal_error`.

## Interrupt and thread rules

Details: [ISR/thread boundary](https://xrobot.work/docs/adv_coding/core/adv-coding-core-isr-thread-boundary).

- No loop-retry inside an interrupt. In an ISR, drop, defer, or hand off on `FULL`/`EMPTY`: the observed state describes that instant.
- No callbacks inside a critical section. Keep FIFO/DMA transfers, queue work, `SerializedService` handlers, and user callbacks outside the locked region; protect only the minimal register or flag update.
- No waiting in the interrupt path. BLOCK operations are task-only; ISR calls pass `in_isr=true` and complete without blocking. Recovery flows that would block return `BUSY` from ISR context.
- Serialize multi-context progress through the primitives in the next section instead of ad-hoc disable/enable pairs.

## Concurrency structure contracts

All structures live in `src/structure/` (plus `src/utils/serialized_service.hpp`). Overview: [basic coding: structure](https://xrobot.work/docs/basic_coding/structure).

| Structure | Contract | Use when | Avoid when |
| --- | --- | --- | --- |
| `MPMCQueue<Payload>` | Bounded MPMC queue; fixed payload, trivially copyable and trivially destructible; byte-block moves, no internal `Payload*`. On a single core, a context preempted between claiming a cell and publishing it leaves transient (spurious) FULL/EMPTY for every other context, so callers must tolerate waiting or retrying later. `Size()` is an approximation under concurrency. | Task/thread producers and consumers that can wait or retry; large capacities; multi-core contention. | Loop-retries in an ISR; callers that treat enqueue success as given; interrupt read/write where a FULL can only drop data — use `SlotPool`; a high-priority RTOS task that spins on FULL/EMPTY — yield before retrying. |
| `SlotPool<T>` | Fixed-size slots, each with an atomic state machine (`SLOT_FREE`/`SLOT_WRITING`/`SLOT_READY`/`SLOT_READING`, all CAS). `Acquire` returns `FULL` when nothing is free; `Publish` stamps a global publish sequence; `Take` picks the smallest sequence, `EMPTY` when none; `Release` cannot fail. A preempted operation holds only its own slot. Ordering is per-producer; no cross-producer global FIFO. `Acquire`/`Take` are O(N) scans. `Put`/`Get` wrappers require trivially copyable `T`. | A few to a few dozen slots shared between tasks and ISRs; multi-producer multi-consumer with ISR put/get. | NMI context; large pools; strict global FIFO ordering. |
| `LatestSnapshot<T>` | Three-slot mailbox: one producer `Store`, one serial consumer `LoadLatest`; keeps the latest complete value. Consecutive stores overwrite an unread intermediate without touching the value being copied. `LoadLatest` returns whether a new value arrived. The handover relies on a lock-free `std::atomic<uint32_t>`; a second writer can tear values and corrupt slot ownership. | Freshness-wins consumers: sensor snapshots, setpoints, latest-state reads. | Queueing (older values are dropped by design); multiple producers or consumers; non-copyable `T`. |
| `ObjectPool<Data>` | Reference-counted fixed slots. `Acquire` returns a move-only writable `Handle`; conversion to copyable read-only `ConstHandle` shares read access; the last release returns the slot. One in-flight `Acquire` per pool (no overlap or reentry; checked in debug builds); final release may run concurrently in tasks or ISRs and requires 32-bit CAS; construction and destruction stay outside ISR. Slots stay constructed for the pool lifetime; release neither destructs nor clears. The reference count tracks lifetime, and data synchronization stays the caller's job. | One buffer handed to one writer and many readers, such as frame publishing with read-only views. | Concurrent `Acquire` from several contexts; relying on release to reset or destroy the payload. |
| `SPSCQueue<Data>` | Lock-free single-producer/single-consumer byte ring; internal capacity is `capacity + 1` (sentinel slot). Batch operations commit all-or-nothing (`FULL`/`EMPTY`). `ProduceWithWriter`/`ConsumeWithReader` advance only the FIFO prefix the callback wrote or read. `Reset` is a consumer-side discard and lets a concurrent producer continue. | One task/ISR producer facing one consumer, including ISR endpoints. | Multiple producers or consumers. |
| `SerializedService` | Single-consumer serialization of progress events. `Invoke(events, in_isr, handler)` publishes event bits and the caller that takes the execution bit runs the handler until the drain ends; concurrent triggers coalesce into the active drain. Event bits mean "state needs rechecking" and carry no occurrence count. `Publish` only records bits. The handler throws no exceptions and blocks on no progress guarded by the same service. | Driving ISR/task-shared driver state machines, such as serial RX/TX progress shared between interrupts and tasks. | Counting semantics (how many times an event fired). |

The plain `Queue` family (`basic_queue.hpp`) is a non-lock-free byte-ring FIFO; use it within a single execution context or behind an external lock.

## ReadPort / WritePort semantics

Full semantics: [RW semantics](https://xrobot.work/docs/adv_coding/core/adv-coding-core-rw-semantics). Headers: `src/core/rw/read_port.hpp`, `write_port.hpp`, `operation.hpp`.

API shape:

- `port(data, op, in_isr = false)` submits a request. `op` is a `ReadOperation`/`WriteOperation` built from a `Callback&` (CALLBACK), a `Semaphore&` plus timeout (BLOCK), a `std::atomic<OperationPollingStatus>&` (POLLING), or nothing (NONE).
- Non-BLOCK `OK` means admitted. The backend finishes each operation exactly once through its `Finish` path, possibly later; Pipe-mode writes complete at enqueue. BLOCK `OK` means completed; `TIMEOUT` means detached after the deadline, and a timed-out call returns only after progress stops touching the buffer, so it can exceed the requested timeout.
- `OperationPollingStatus` is `uint32_t`-backed; the completing side release-stores `DONE`/`ERROR`, and the caller acquire-loads it.

Return codes:

- `OK` admitted (non-BLOCK) or completed (BLOCK); `FULL` insufficient byte space or request slots, with no side effects on payload, metadata, or callbacks; `BUSY` the producer or request phase is occupied; `TIMEOUT` a timed-out BLOCK; `NOT_SUPPORT` an unbound or unsupported port; `SIZE_ERR` a positive request above queue capacity; `ARG_ERR` invalid arguments.
- Zero-length reads act as readiness probes and accept a null address; a supported port answers them with `OK`.
- Partial transfer: reads copy only when the full request is available; writes accept no partial request; Stream appends are all-or-nothing.

Buffer ownership and lifetime:

- WritePort copies payload into its internal ring at admission, so the source buffer is reusable as soon as the call returns. The callback, semaphore, or polling state must stay valid until the operation's completion boundary; a detached (timed-out) request no longer touches its semaphore.
- ReadPort keeps at most one unsatisfied request; the destination buffer stays valid until completion or cancellation, and through the return of a BLOCK call.
- Backend side: `GetReadQueue(in_isr)` / `GetWriteQueue(in_isr)` return scoped views. The read side uses `PushBatch`/`PushWithWriter` plus exactly one `Publish` per scope, including scopes with no data. The write side allows one `PopAll`/`PopWithWriter`/`FailFront` per front. `FailFront` covers a locally detected, unreplayable partial external transfer failure; capacity shortfalls and DMA start failures take the bounded-overload path instead.
- Backend housekeeping, flush, and interrupt-disarm paths stay out of the public producer admission phase: a write admits without `BUSY` whenever the queue has capacity, so an internal path that consumes the producer phase is a defect even when it completes.
- A UART with TX enabled is constructed with a positive `tx_queue_size`. Zero selects the Pipe completion-at-enqueue layout; on a normal UART it leaves the write callback bound while the backend is not ready.

## Drivers

- `driver/` is organized per platform: `st`, `ch`, `esp`, `hpm`, `mspm0`, `linux`, `webots`, `webasm`. The directory name is the `LIBXR_DRIVER` value; `LIBXR_SYSTEM` selects `system/<name>` the same way.
- `LIBXR_DRIVER` selects a whole platform directory at once: `cmake/config.cmake` normalizes the value (case-insensitive) and includes `driver/<dir>/CMakeLists.txt`, which globs every `.cpp`/`.c` in the directory into the `xr` target and exports the include path; per-peripheral toggles are outside the build model. Leaving `LIBXR_DRIVER` unset compiles the abstraction layer only, with a warning.
- USB device controller drivers live in the platform directory; the platform-independent XRUSB stack (descriptor core, endpoint core, device classes such as CDC-ACM, HID, UAC, GS USB, DAPLink, DFU) lives in `src/driver/usb/`.

Adapting a new platform:

1. Create `driver/<platform>/` with a `CMakeLists.txt` that globs sources into `xr` and exports the include directory, following an existing platform directory.
2. Start with `Timebase` (the millisecond tick underpins Timer, sleeps, and timeouts), then `GPIO` and `UART`. Record per-peripheral status in `doc/support.md` using its legend (supported / compile-only / in development / unsupported / hardware-unsupported), and mark which entries carry hardware evidence.
3. Derive drivers from the shared abstractions: a UART driver holds `ReadPort`/`WritePort` and forwards `Read`/`Write(data, op, in_isr)`; `SetConfig` receives the real call context (`in_isr`).
4. RX DMA ring/idle pattern: one ReadQueue scope per observed DMA position change — `PushBatch` with a linear segment or two wrap segments, exactly one `Publish`, and the cursor update before publish reentry. HT/TC/IDLE interrupts are progress hints. RX space shortage is a bounded overload: copy the prefix that fits and advance, with no replay, pause, or error states.
5. TX DMA pattern: one admitted request per DMA half-buffer; claim, fill, and settle once; the completion interrupt releases or refills the half and leaves already-settled requests untouched.
6. Keep the interrupt path non-blocking. Callers serialize `SetConfig`/`Read`/`Write`/`Mem*` on one synchronous-bus instance; the driver adds no multi-caller serialization.
7. UART TX completion means staged: data handed to the FIFO/DMA controller completes the request, and the wire state stays with the backend. Keep this separate from the borrowed-buffer rule for SPI/I2C, where a CPU copy completing does not count as physical transfer completion.

Peripheral contracts on new platform code:

- Derive a timer counter clock from the APB prescaler together with the `TIMPRE` bit, using the clock the HAL already resolved: the timer clock is PCLK scaled by the APB prescaler and `TIMPRE`. `driver/st/stm32_pwm.cpp` carries the forms, for example H7 as `min(HCLK, (TIMPRE ? 4 : 2) * PCLK)`.
- In a USB OTG device controller, size the RX FIFO before setting the TX0 base address and construct EP0 OUT before EP0 IN. `SetTxFiFo(0)` takes the current `GRXFSIZ`, so a TX0 base written first lands outside the FIFO RAM and EP0 control transfers misbehave.
- Decide per-part peripheral presence from the SoC header or the SVD instance set, not from whether a vendor common header declares the symbol: the CH32V30x common header defines `CAN2` on single-CAN packages, and `driver/ch/ch32_can_caps.hpp` keys CAN2 on the package-family macro instead.
- Budget CH32 FSDEV endpoint memory (PMA) against the peripherals that coexist with USB: 512 B with USB alone, 384 B once CAN1 is initialized, 256 B with CAN1 and CAN2 (`ch32_usbcan_shared.hpp`).
- The endpoint base contract fixes one CPU-writable buffer per endpoint at construction and starts transfers by length, which matches FIFO and PMA controllers. A descriptor-based controller (dQH/dTD) needs an endpoint layer of its own instead of a change to that contract.

Interrupt sources and priorities per platform:

- STM32: the CubeMX `.ioc` sets tick and peripheral NVIC priorities and is the single source of truth. Keep the 1 ms timebase interrupt at the top priority so peripheral ISRs cannot preempt timebase updates; measured reference configurations run the timebase IRQ at priority 0 with peripheral DMA IRQs below it.
- MSPM0: the driver enables its own IRQ sources and writes the NVIC priority at runtime — SysTick timebase 0, UART/SPI/INT_GROUP1 1 on a core with four priority levels. SysConfig generates priorities only for the interrupts SysConfig itself enables.
- CH32: PFIC priorities with HPE nesting; USB/CAN shared vectors install strong handlers through `ch32_usbcan_shared.cpp` so static-library linking pulls them in ahead of weak BSP handlers.
- HPM: PLIC priorities; platform IRQ wrappers dispatch to registered owners.
- ESP32: ESP-IDF interrupt allocation; one status snapshot per IRQ — mask-match the sources, snapshot the service, clear only those bits, re-read, and re-enable after processing the remainder.

Interrupt ownership changes (who claims a vector, who sets a priority) are public-contract changes and follow the public interface checklist.

DMA and cache:

- Drivers own cache maintenance on their DMA paths; STM32 keeps helpers in `stm32_dcache.hpp`. USB OTG DMA on STM32 invalidates `hpcd->Setup` in `HAL_PCD_SetupStageCallback`, so the USB path needs no extra PCD MPU or linker relocation.
- Keep DMA-capable storage aligned to the cache-line size with sizes in whole lines, so two buffers do not share a line. Alignment of generated DMA storage belongs to the generator layer; driver code adds its own maintenance around transfers.
- HPM drivers call SDK register- and driver-level APIs directly; SDK `board.c` helpers (console pin setup, board pin-init clock ordering) stay at the BSP integration layer. The `driver/hpm/` directory of LibXR v2.0.1 holds the dma, gpio, i2c, power, pwm and timebase drivers; UART, SPI and CAN have no LibXR HPM driver. The HPM errata and controller obligations (FGPIO E00037, MCAN bus-off recovery) are in the Platform contracts section of references/bsp-development.md.

## C++20 baseline

CMake sets `CMAKE_CXX_STANDARD 20` with `CMAKE_CXX_STANDARD_REQUIRED ON`; toolchains that bypass feature detection get explicit `-std=c++20`/`-std=gnu++20` or MSVC `/std:c++20`. New code compiles under this baseline on all supported systems (None, FreeRTOS, ThreadX, Linux, Webots, WebAssembly).

Compiler-portability surface: the compatibility macros in `src/core/libxr_def.hpp` (`LIBXR_PACKED*`, `LIBXR_NOINLINE`) cover GCC, Clang and MSVC and fall back to `#warning` plus an empty expansion on any other compiler, so a packed CAN frame or USB descriptor silently grows to its natural layout and the build stays green. Adding a toolchain means adding its branch; a line-protocol type keeps a compile-time assertion that distinguishes the packed layout from the padded one.

## Code style

- `PascalCase` for types, classes, structs, enum types, and member functions; `snake_case` for locals, parameters, and data members, with a trailing `_` on data members; uppercase for macros, error codes, log macros, and enum values.
- Allman braces, two-space indent, access specifiers at the left edge; keep the repository's existing `using`/`typedef` boundaries.
- `#pragma once`; a `.cpp` includes its matching header first; reorder includes only when the task or the formatter requires it.
- Source under `src/` follows the naming style; `driver/` and `system/` platform code is exempt (repository `AGENTS.md`).
- Many components allocate once at initialization and keep that memory for the process lifetime. Adding a release for symmetry alone is a defect; label a startup-time allocation as a leak only with ownership-stage evidence.
- Keep local pointer/reference spacing and existing low-level macros, conditional compilation, attributes, and `extern "C"` blocks unless the change alters their semantics.
- Keep functional changes free of unrelated whole-file reformatting.

Formatting checks, run from the repository root:

```sh
tools/format_cpp_files.sh --check
tools/format_cmake_files.sh --check
git diff --check
```

- `.clang-format` is Google-based with `BreakBeforeBraces: Allman`, `ColumnLimit: 90`, `IncludeBlocks: Regroup`; the check script pins clang-format 21.1.8, and CI installs `clang-format==21.1.8`.
- CMake formatting uses cmakelang 0.6.13 (`cmakelang[YAML]`).
- Format the touched files with the pinned versions; run repo-wide checks only for repo-level style or layout changes.
- The gate is per repository: the tools and versions above are LibXR's, and each other repository's CI names its own formatter and pinned version — read that repository's workflow files before running or claiming a format check there.

CI (`.github/workflows/check.yml`) gates each PR with: a build matrix (Debug-ON, Release-ON and Release-OFF with Unix Makefiles, plus Debug-ON with Ninja, where ON/OFF is `LIBXR_DEV_ASSERT_BUILD`; each with `LIBXR_TEST_BUILD=ON`, then `ctest`), the clang-format job, a doxygen-warnings job (Doxygen 1.12.0 running `tools/check_doxygen_warnings.sh` against `doc/doxygen_warning_baseline.txt` — lower the baseline when a change removes warnings), and the cmake-format job.

## Comments and Doxygen

- Public headers carry concise Doxygen. Public classes, enums, methods, parameters, return values, and fields follow the file's bilingual convention: one Chinese line, then its English counterpart, as in the `src/structure/` and `src/core/rw/` headers.
- Doxygen comments live in headers; definitions in `.cpp` files keep at most local `//` comments and do not restate header text.
- Record observable semantics and boundaries: preconditions, ownership, lifetime, execution context, reentry, completion, failure, platform limits.
- Local `//` comments cover non-obvious invariants, state transitions, memory-ordering reasoning, hardware timing constraints, and compatibility constraints. Skip syntax restatement, narration of obvious assignments, experiment history, and vague abstractions in place of behavior.
- Every `@param` names a parameter that exists in the declaration; unused named parameters carry `[[maybe_unused]]`.
- A virtual hook with a default implementation documents the caller contract: which return codes the caller handles and which it may ignore.
- Suppressions (`NOLINT`, `clang-format off/on`) go at the narrowest proven location, with an explanation when the constraint is not evident.

## Python code (XRobot tooling and CodeGenerator)

Style rules: [coding style (Python)](https://xrobot.work/docs/con_guide/con-guide-coding-style-python).

- ruff handles lint and format, with the version pinned in CI.
- Tests are `unittest` suites under `tests/` with shared fixtures and data directories; run the suite plus ruff before submitting.
- CI covers a Python 3.10–3.14 compatibility matrix on Linux and Windows and an import smoke test that exercises every top-level module after wheel installation.
- Generated output stays deterministic: independent of `PYTHONHASHSEED`, LF line endings, stable ordering, so generated files diff cleanly.

## Documentation

Style rules: [doc style](https://xrobot.work/docs/con_guide/con-guide-doc-style). The rules that matter most:

1. Classify each page first — tutorial, how-to, reference, or explanation — and keep it in its lane.
2. Keep neutral, third-person prose; use imperative form for commands, and avoid addressing the reader directly.
3. State what a thing is and does instead of framing it by negation.
4. Describe observed behavior rather than absolute guarantees ("`xrobot setup` stops and explains when a module has uncommitted changes").
5. Explain concepts through one concrete scenario plus a concept-to-scenario table; introduce each term where it is first needed.
6. Keep command sequences runnable in the written order, keep prose consistent with the shown code, and mark elisions as excerpts.
7. Hold terminology identical across source, comments, tests, and documentation.
8. Use generic scenarios for core-library examples, and keep verification history and review debates out of user-facing docs.
