When to read this: Plan and execute verification for a LibXR, XRobot, module or BSP change — the evidence ladder, formal verification, host tests, CI, on-board acceptance, USB/CAN debugging, and experiment reporting.

## Verification budget

Start verification from the smallest check that can refute the current claim, and expand the scope only as the actual risk grows. For a change that touches public behavior — return codes and capacities, data visibility and ordering, partial acceptance, blocking and timeouts, completion and callback semantics, ownership and lifetime, cancellation, call contexts, ABI or layout, hardware side effects, Flash/RAM — review the semantic difference first, and run the full test matrix after that gate: an unreviewed matrix run produces numbers with no decision attached. Compiling proves that the toolchain accepts the change into the build for that backend and option set; runtime, semantic, and hardware claims need their own levels of evidence (see the evidence ladder below). Do not repeat an accepted run whose sources, harness, environment, and acceptance criteria are unchanged. Stop at the declared budget; produce extra hashes, archives, inventories, or absence checks only for a concrete consumer.

## Evidence levels

| Level | Evidence | What it proves | What it leaves open |
| --- | --- | --- | --- |
| 1 | Static inspection or compile pass | The code reads consistently against the contract, and the toolchain accepts the change into the build for that backend and option set. | Runtime behavior of any kind: requirements, public semantics, MMIO and DMA behavior, timing, hardware. |
| 2 | Deterministic regression of known examples (host tests, `test/automatic`) | Deterministic core semantics on Linux: containers and queues, read/write ports, middleware, utilities, and the assertion-mode matrix. | Real cross-toolchain builds, USB enumeration and traffic, DMA/cache timing, IRQ and RTOS interleaving on the target, physical line behavior. |
| 3 | Sanitizer, stress, or repeated dynamic execution on the host | Memory errors, data races, undefined behavior, and low-probability interleavings on the paths the run exercises. | Interleavings the host scheduler does not produce, target timing, paths the run does not reach. |
| 4 | Independent abstract model checking with negative controls | Safety and liveness of the abstract protocol under the stated assumptions; the broken configurations produce their expected counterexamples. | Whether the code implements the model; everything the model excludes (see "Formal verification and model checking"). |
| 5 | Implementation-level memory-model or bounded verification | The concrete code's ordering and bounded-state behavior under the checker's memory model and bounds. | Behavior past the bounds, backend code outside the checked source, hardware. |
| 6 | Real backend or toolchain build with the touched path included | The target's SDK and toolchain compile and link the touched path. | Runtime behavior on the target. |
| 7 | Hardware acceptance on the product path | On-board functional test: the real build runs on target hardware, and the touched peripheral paths work there (UART, SPI, I2C, CAN, USB). Long-run stress rounds add repeatability under sustained load: counters and error statistics surface low-probability interleavings and slow drift. | Statistical timing claims and stability margins beyond the recorded rounds; generalization beyond the recorded board, wiring, host, and build identity. |
| 8 | Release or deployment acceptance in the intended environment | The published artifact (package, image, firmware release, deployed site) works where its users run it. | Other environments and configurations. |

Keep a conclusion within the strongest completed level and cite that level; a statement at one level is no proof at a higher one. A build pass is not hardware validation, and a model check is not proof of backend MMIO or DMA behavior. Software and build gates cover their own layer, while DMA/cache coherency, IRQ timing, USB enumeration, and RTOS interleaving on the target are hardware-level claims backed by level 7 evidence.

## Test coverage

- Cover normal behavior plus the timeout, partial-completion, reentry, teardown, wraparound, and error paths that apply to the change.
- Treat driver, DMA, ISR, concurrency, ABI and layout, persistence, and performance changes as high-risk surfaces; each carries explicit evidence at the level its claim needs.
- Report what the tests leave untested.

## Formal verification and model checking

Levels 4 and 5 follow these rules:

- Write the specification independently from the implementation's guards.
- Map each action and linearization point of the model back to concrete code.
- Include intentionally broken configurations and require their expected counterexamples; a model that cannot fail proves nothing.
- Separate safety, liveness, fairness assumptions, platform contracts, and implementation correspondence, and state each at its own level.
- Turn every confirmed counterexample into a deterministic implementation test (level 2).
- State what the model excludes, especially MMIO, DMA, interrupt masking, cache, backend scheduling, and user callbacks.

## Host tests

LibXR keeps two test categories under `test/` in [xrobot-org/libxr](https://github.com/xrobot-org/libxr): `test/automatic` runs on Linux in CI, and `test/manual/{system,driver}` targets specific hardware. Automatic tests are organized as one directory per tested interface, mirroring the source layout — `src/core/rw/read_port.*` maps to `test/automatic/core/rw/read_port/`. Driver and system tests follow the common abstractions (`uart.hpp`, `Thread`) rather than platform implementation files; Linux serves as the harness environment. The test program has a single explicit `main.cpp`, and the run sources are listed explicitly. See [test/README.md](https://github.com/xrobot-org/libxr/blob/master/test/README.md).

Run the suite from the repository root:

```sh
cmake -S . -B build -DLIBXR_TEST_BUILD=ON -DLIBXR_DEV_ASSERT_BUILD=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel 8
ctest --test-dir build --output-on-failure --no-tests=error
```

Terminal tests need the pseudo-terminal helper `script` from util-linux; CTest wraps them, and the full program has a 300-second timeout. Run one group with `--case` (case names are listed in `test/automatic/main.cpp`):

```sh
script -q -e -c './build/test/libxr_test --case lockfree_list' /dev/null
```

The executable is `build/test/libxr_test` (CMake target `libxr_test`). For full output of the registered suite:

```sh
ctest --test-dir build -V -R '^libxr_automatic$' --no-tests=error
```

The automatic build pins `LIBXR_SYSTEM=linux` and fails the configure otherwise; some core semantic tests are written to stay runnable without an OS layer (`LIBXR_SYSTEM=none`, for example `test_async_cooperative`) — keep tests in that group runnable the same way. Assertion behavior carries its own matrix: the four `test_assert_{debug}_{dev}` combinations and the `test_assert_disabled` probe. `LIBXR_TEST_BUILD=OFF` builds the product library without tests.

v2.0.1 contains no sanitizer build entry: the CMake options, CI workflows, and test documentation define no ASan/UBSan/TSan or valgrind configuration. Running sanitizers means adding the compiler flags in a separate build configuration outside the checked-in options.

## LIBXR_DEBUG_BUILD

`LIBXR_DEBUG_BUILD` turns on LibXR's `ASSERT` checking: when active, a failed `ASSERT` calls `libxr_fatal_error(file, line, in_isr)`; when inactive, the `ASSERT` expression is still evaluated and the check is skipped. `DEV_ASSERT` is a separate development-time check enabled only by `LIBXR_DEV_ASSERT_BUILD` and left unevaluated otherwise. `REQUIRE` stays active in every configuration and reports unrecoverable runtime failures; recoverable errors are returned as error codes.

The variable defaults from the build type. Unset, it is recomputed on every configure (Debug turns it ON, other build types turn it OFF) as a normal CMake variable, so switching the build type in an existing build directory takes effect immediately. Set explicitly with `-DLIBXR_DEBUG_BUILD=ON` or `-DLIBXR_DEBUG_BUILD=OFF`, it enters the cache and keeps that value on later reconfigures. It is independent of `LIBXR_DEV_ASSERT_BUILD`. In module CI, the default `RelWithDebInfo` build type is configured with `-O2 -g` plus `-DLIBXR_DEBUG_BUILD=ON`, so `assert()` and `eigen_assert` stay active despite `-DNDEBUG`.

## Module CI: module-ci.yml@v1

Module repositories adopt the shared workflow from [xrobot-org/XRobot](https://github.com/xrobot-org/XRobot) in `.github/workflows/build.yml` (this is the file the existing module repositories carry):

```yaml
name: Module CI
on:
  push:
  pull_request:
  workflow_dispatch:
jobs:
  build:
    uses: xrobot-org/XRobot/.github/workflows/module-ci.yml@v1
    with:
      template-args: '[]'
```

One job on `ubuntu-latest` (container image `ghcr.io/xrobot-org/docker-image-linux:main`) checks out the module, resolves the context refs, generates a constructor probe with `xrobot check-module` — a compile-only `XRobotCompileCheck()` translation unit whose dependency arguments are void placeholders — and builds it together with LibXR's Linux backend as a C++20 CMake project. When `ctest-regex` is set, the module's own tests are built and the matching CTest tests run, with a per-test timeout of 15 seconds by default.

The matrix is the ref combination, decided by the event: a pull request builds against its target branch, a tag push against `master`, every other event against the current branch. XRobot, LibXR, and dependency requests resolve to that context branch and fall back to `dev` when the repository has no branch of that name (same-or-dev). The `xrobot-ref`, `libxr-ref`, and `dependency-ref` inputs default to empty and follow that rule; setting one pins its context. Other inputs: `build-type` (default `RelWithDebInfo`), `template-args` (JSON list for the probe's template arguments), `sources` (extra module index URLs), `apt-packages`, `cmake-options`, `ctest-regex`, `ctest-timeout`.

One job builds one Linux-backend probe per run; multi-platform compile coverage comes from the backend build matrices and BSP CI.

## BSP CI: bsp-stm32-ci.yml@v1

STM32 BSPs call the shared workflow; the caller job needs `contents: write` because the release job attaches firmware to releases (this is `xrobot_stm32.yml` of `bsp_stm32f103`):

```yaml
name: build

on:
  push:
    branches: [main, master, dev]
    tags: ['v*']
  pull_request:
    branches: [main, master, dev]
  workflow_dispatch:

jobs:
  build:
    permissions:
      contents: write
    uses: xrobot-org/XRobot/.github/workflows/bsp-stm32-ci.yml@v1
    with:
      project: BluePill
      build-type: Debug
```

Inputs: `project` (CMake project name, the base name of the firmware ELF, required), `configs` (one per line; `default` builds `User/xrobot.yaml`, any other name builds `<config-dir>/<name>.yaml`), `config-dir` (default `User/RobotConfig`), `toolchain`, `build-type` (default `Release`), `presets`, `release-configs`, `image`.

The `check` job installs the pinned tools — the `xrobot:` field from `Modules/modules.yaml` and the `generator:` field from `User/libxr_config.yaml` — regenerates `User/app_main.cpp`, `app_main.h`, `flash_map.hpp`, and `libxr_config.yaml` with `libxr parse`/`libxr gen` and fails on any difference from the committed files, rejects CRLF text files, runs `xrobot format --check`, and runs `xrobot setup --frozen` with context and release refs, so locked modules sit on the target release line.

The `build` job runs the configs x presets matrix; non-default configurations run `xrobot gen -c <config-dir>/<config>.yaml` first. Release-marked builds package `build/<project>.elf/.hex/.bin` with the configuration YAML and a `build-info.json` that records the commit, tool versions and pins, LibXR submodule commit, module commits, and section sizes.

The `release` job publishes firmware on a published Release, a `v*` tag push, or a push to `master`/`main`. A master push whose commit has no `v` tag receives the next patch tag automatically — the highest `vX.Y.Z` plus one, `v1.0.0` first — and publishes `<project>-<config>[-<preset>]-<tag>.{elf,hex,bin}`, the configuration YAML, a reproducible `tar.gz`, `SHA256SUMS`, and `firmware-manifest.json`. See the [project CI documentation](https://xrobot.work/docs/proj_man/proj-man-ci).

Build-only platforms: the MSPM0, HPM, CH32, and Linux BSPs run their own build-only workflows (a `build.yml` per repository, `build-test.yml` for Linux across x86 and arm64) with a firmware-release job only in the STM32 path. MSPM0, HPM, and CH32 add a daily `libxr-master` canary that checks out LibXR `master` and builds; a canary failure does not fail the workflow. For these platforms the CI evidence is the build itself, and firmware comes from a local build.

## On-board acceptance

Before flashing, back up the whole flash and record the backup's SHA256. After the tests, write the backup back and read it back to confirm byte-identical content. Track which board each backup came from (chip UID) so a backup is restored to the board it came from, and record the final state in the report: which firmware runs on the board, and where the backup lives. Run Debug and Release builds. Support timing-related conclusions with bounded stress rounds, for example a fixed list of configuration switches with counted outcomes per round; hardware timing and error-path tests are level 7 evidence, so add them when the claim concerns those areas.

For a board whose BSP is unknown, the first step is to read the IDCODE and the unique ID through the debug probe and to match the chip to a BSP; flashing starts after that match.

Flash by platform. Before a vendor procedure runs, check the chip's datasheet and published errata for its boot and download flow — bootloader entry, ISP, option bytes, reset levels — and carry the errata workarounds into the sequence; the commands below come from the BSP READMEs and start the check rather than end it:

- STM32 (`bsp_stm32f103`, `bsp-dev-c`): STM32CubeProgrammer CLI over SWD, as in the BSP's `.vscode/tasks.json` task `CubeProg: Flash project (SWD)`:

  ```sh
  STM32_Programmer_CLI --connect port=swd --download <current CMake launch target> -hardRst -rst --start
  ```

  Release `.hex`/`.bin` images also flash with any SWD tool.
- MSPM0G3507 (`bsp-mspm0g3507-mini`): J-Link over SWD (an XDS110 works as well):

  ```sh
  JLinkExe -Device MSPM0G3507 -If SWD -Speed 4000 -AutoConnect 1
  ```

  then in J-Link Commander: `loadfile build/debug/mspm0_minidb48.elf`, `r`, `g`. The terminal command `power bootloader` resets into the ROM BSL for serial flashing.
- HPM5301 (`bsp-hpm5301evklite`): J-Link over JTAG:

  ```sh
  JLinkExe -Device HPM5301xEGx -If JTAG -JTAGConf -1,-1 -Speed 4000 -AutoConnect 1
  ```

  then `loadfile build/release-flash-xip/output/demo.elf`, `r`, `g`. OpenOCD uses the SDK's `boards/openocd/` configurations plus the board's `hpm5301evklite.cfg`.
- CH32V307 (`CH32V307_LibXR_Template`): WCH-LinkE with the WCH build of OpenOCD. `openocd -f wch-riscv.cfg` starts the debug server; download and debug `build/CH32V307VC.elf` through the VS Code Cortex-Debug launch configuration.
- Linux (`bsp-linux-autoaim`): the product is a host program, so acceptance runs the built binary directly; deployment installs a systemd service with `sudo deploy/install-service.sh`.

## A/B comparison on hardware

Build two firmware images that differ only in the change under test — same toolchain, same build type, same configuration — and run the baseline as well. Swap one variable at a time (host, port, cable or adapter, firmware build) and record counts per run. Prefer a same-input base/target comparison over parameter sweeps. State in the conclusion which numbers distinguish the before/after builds; when the runs cannot be distinguished, record that the change showed no effect at this level.

Run the baseline in the same session on the same hardware as the candidate; a number quoted from an earlier run is a reference, not a control. When the baseline does not fail where a failure was expected — or when both builds pass — record that outcome as measured, and do not reshape the code under test to manufacture a baseline failure. When the candidate fails, stop and preserve the scene: the inputs, the logs, the counters, the board state, and the exact image that failed get diagnosed from the preserved state rather than flashed over.

An overload test is the generic shape of a separating test. Drive the input past the processing capacity — queue writes arriving faster than the consumer drains them, for example — and record progress per build: the baseline stalls and stops making progress while the changed build keeps running with bounded latency, and the conclusion names the overload run as the measurement that distinguishes the before and after builds. When both builds stall, or both keep running, the test does not separate them and needs a different observable.

When both builds fail, prove the control on the current harness first, then trace the shared failure to a cause — the inputs, the environment, the harness, or both images — before the group is reclassified or rerun.

## Ablation experiment design

An ablation compares a candidate against a control with one variable changed. Design the comparison in four parts before running it.

Freeze every variable but one:

- Declare each comparison as an explicit triple — fixed conditions, the single changed variable, the observed quantities.
- Split a multi-dimensional change into a sequence of single-variable experiments; the winning configuration freezes into the next experiment's baseline, and variables that shift everything downstream (input size, preprocessing) go last in the sequence.
- Run all groups on the same input frames, replay sequences, and calibration data, with the same set sizes.
- Pin the artifact under test with a fingerprint — provenance, commit, export time, calibration-set identity, shape, dtype, layout, quantization parameters, output hashes — and after any configuration change regenerate the derived artifacts and print the loaded artifact's identity (path and hash) in the run log, so the run proves it tested the intended build.

Make the comparison fair:

- Compare like with like: inference-only against inference-only, end-to-end against end-to-end. Mixed figures do not compare, and neither compares against theoretical peak numbers.
- Keep a complete unmodified control in every ablation; an optimization without a control does not stand.
- Align everything except the tested variable: toolchain and compiler versions, build options (candidates may build independently but with identical options), run conditions such as clock and scheduling policy, and downstream and post-processing versions.
- Record coverage next to speed: output counts, class and attribute agreement, geometric error, missed frames. A deleted branch or a swapped model carries coverage metrics so the faster incomplete variant does not win on speed alone.

Evaluate in layers:

- Run each candidate up a ladder — single-frame white-box, fixed-size replay, extended full replay, real sensor on an empty scene, real sensor on the target scene — passing one layer before the next.
- Each layer answers one question — the white-box layer the numerical contract, replay the model behavior, full replay the queues and downstream, the real sensor the capture chain, the target scene the task semantics — and its conclusions stay on that layer; report passed and untested items side by side and keep an open-boundary list of what remains unmeasured.
- Set a correctness group and a performance group at each layer; a candidate enters the pool only when both pass.

State conclusions as numbers:

- Phrase a conclusion as metric name, statistic (mean, p95, max), and measurement conditions.
- Walk one probe frame through the data flow — raw model, split components, compiled artifact, final decode — saving shape, dtype, layout, and output hash per stage; localize a divergence by substituting stages in data-flow order.
- Fix acceptance thresholds before the experiment; a candidate passes when semantic error sits inside the pre-declared threshold and the performance gain repeats across runs.
- Keep the baseline metrics that passed acceptance as a long-term contract and report later comparisons as deltas against those same numbers; define throughput (frames produced downstream) and latency (same-frame timestamp to result timestamp) separately and report them separately — a pipeline overlap gain in throughput is a throughput result, not a latency result.
- Failed rounds enter the matrix with their error type and triggering parameters, so a long search does not pay for the same failure twice.

## USB debugging

Split the path into segments — application write, class-driver queue, endpoint/FIFO, bus, host controller, host driver, application read — and collect independent evidence per segment instead of inferring across segments.

Device-side counters: add SWD-readable global counters (IRQ count, reset/setup/data-in callbacks, transfer start/finish) to a diagnostic build. Read a baseline after attach, run the failure window, read again; the difference is the event count within the window. Keep diagnostic patches in the working tree, out of the commit.

Host-side reading: `dmesg` error codes classify the failure — `-110` is a timeout (the request produced no completion event), `-71` is EPROTO (CRC or bit errors, a signal problem), `-62` means the device stopped answering, which commonly happens when the target sits halted after `reset halt`. For finer detail, use xhci tracepoints (the `urb_enqueue` to `urb_giveback` interval) or usbmon.

Inference rule: an ACK from the host hardware for IN data means the packet reached the host with a correct CRC. Device sent everything, host hardware ACKed, and the driver reported no completion event — the defect sits in the host driver path.

Stuck endpoint (STM32 OTG): halt the core and read `DIEPCTLn` (EPENA), `DIEPTSIZn` (remaining PKTCNT), and `DTXFSTSn` (FIFO free words). EPENA=1 with PKTCNT=1 and an empty FIFO means the packet was cleared and the transfer stalls at that state. Compare the HAL sequence against the reference-manual disable sequence for IN endpoints (SNAK, wait INEPNE, EPDIS, wait EPDISD, flush FIFO). A control transfer that misbehaves from the first enumeration points at FIFO setup rather than at the endpoint state: read `DIEPTXF0` against `GRXFSIZ`, and a TX0 start address above the controller's total FIFO word count means the TX0 base was written before the RX FIFO size.

SWD discipline: run `reset run` before detaching. A target left halted stops answering EP0 and the host keeps reporting `-62`. During USB activity, SWD access to OTG registers can wedge the CPU inside the IRQ handler; when live sampling is needed, sample DWT_PCSR or SRAM instead.

Concurrency defects: reproduce on the host first, with deterministic injected timings — completion-callback re-entry, double buffering, write from callback, unbind/rebind, coalesced wakeups. The fix fails in an existing test before the fix and passes after it; keep test and fix in separate commits. Reuse LibXR primitives where they fit (for example `SerializedService` single-consumer serialization); interrupt paths wait for nothing, and disabling interrupts is a workaround rather than a fix.

Throughput and integrity criteria: fix the machine configuration and duration per round, and compare round-to-round numbers. A frame-format stream checker reports per-topic frame counts and rates plus `skipped_bytes`/`bad_header`/`bad_payload`/`ts_backwards`; a terminal round-trip check uses fixed bytes. Trust only counters decoded from raw RAM or log data; the decoding script reads the data instead of embedding expected values.

A/B exclusion: change one variable per run — host, port, cable, firmware build — with counts per run, and record the excluded items (power supply, kernel version, firmware differences) so the ground is not re-covered. A powered device in the USB path (extension cable, switch chip) is tested by bypassing it and connecting directly. See the [debug pages](https://xrobot.work/docs/debug) for tool-level material.

## CAN testing

Check termination resistors, bit rate, and the automatic-retransmission configuration first when CAN transceivers misbehave. With two boards transmitting simultaneously and automatic retransmission disabled, a frame that loses arbitration gets cancelled — count "cancelled" as an expected outcome in test scripts rather than a failure.

## Experiments and reports

Identify every experiment before running it: repository root, branch, commit, dirty state, tool versions, firmware/binary hashes and hardware identity, scenario and inputs, reset/preconditions, requested versus effective parameters, the known-good control, the single changed variable, acceptance criteria, and the rollback point. A hypothesis that needs source changes goes into a clean, isolated worktree; unrelated probes and fixes stay out of the same experiment. Declare what the experiment can refute before running it — experiments and candidate tests do not create product requirements.

Control validity: run the known-good control on the same harness first. A failing control stops the comparison until the environment or harness passes it again. A mismatch between requested and effective parameters voids the comparison. Reuse the previously accepted harness instead of a rewritten approximation.

Performance measurement: define the measured path, clock, toolchain, and build options, input sizes, sample count, warmup, and statistics. Separate fixed per-operation cost from context-dependent handler, copy, callback, cache-line, and interrupt cost. Compare only between identical binary shapes and hardware preconditions, and report the latency, memory, Flash/RAM, and stability trade-off together.

Report: experiment identity, control result, candidate result, the first divergence point, evidence level, untested areas, and the rollback path. State untested areas explicitly. Stop at the declared verification budget; without a concrete open claim, avoid re-running the same matrix or appending hashes, archives, inventories, or absence checks.

## Audits and review conclusions

A review or defect sweep keeps an itemized list of the ground it covered, with each item in one state: `unseen`, `checked-no-change`, `finding`, `blocked`, `excluded`. The sweep ends with no unexplained `unseen` item, and each `excluded` item traces to the decision that excluded it.

A proposed correction is reviewed as an object of the same standing as the finding it answers: reachability, implementability, and the regression it could introduce. A conclusion that rests on no independent source can carry a fix of negative value.
