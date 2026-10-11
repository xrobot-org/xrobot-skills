When to read this: A concrete XRobot or LibXR failure surfaced — setup, lock, generation, format, submodule, USB CDC, CAN, I2C, an analog or timer output, a watchdog reset, a bootloader session, or a platform build — and the next step is a symptom-to-check-to-fix path.

Entries are ordered roughly by how often each failure surfaces. Commands run in a shell inside the BSP repository; the `xrobot` CLI operates on the nearest ancestor directory that contains `Modules/modules.yaml`, and `-C DIR` starts the search elsewhere. Quoted messages are example tool output; `<placeholder>` stands for a machine-specific path or name.

## Symptom index

Look up the failure in this table first; each entry it points to is a Check → Fix → Links path.

| Symptom | Entry |
| --- | --- |
| **Module resolution and lock** | |
| setup reports a missing package or a rewritten owner | Setup on a freshly cloned BSP reports a missing package or a mismatched owner |
| a requested package is not found, or the name is ambiguous | A package is not found, or the name is ambiguous |
| the lock and the module list disagree, or `setup --frozen` fails | xrobot.lock disagrees with Modules/modules.yaml, or `setup --frozen` fails |
| installed tool versions do not match the BSP pins | The installed generator does not match the BSP pin |
| format or CRLF check fails in CI | The format check or the line-ending check fails |
| submodule directories are empty after clone | Submodules are not initialized |
| **Generation and build** | |
| HPM regeneration breaks the build or the config check | Regenerating an HPM project breaks the build or the config check |
| `User/xrobot_main.hpp` not updated after a `libxr ... setup` run | The module main function is not updated after `libxr ... setup` |
| the Linux configure step fails on missing libudev | The Linux build fails on missing libudev |
| `libxr mspm0 setup` cannot run SysConfig | `libxr mspm0 setup` reports that SysConfig cannot run |
| the build stops: `User/xrobot_main.hpp` is stale | The build stops: User/xrobot_main.hpp is stale |
| pip install fails with externally-managed-environment | pip install fails with externally-managed-environment on Debian/Ubuntu |
| the generator reports `XR_REGISTER` errors | Generation reports errors around XR_REGISTER |
| **Peripherals and runtime** | |
| USB CDC does not enumerate, or the port is silent | USB CDC does not enumerate, or the port carries no data |
| CAN frames are lost, cancelled, or never arrive | CAN transmission or reception misbehaves |
| no output on the serial console | The serial console produces no output |
| the I2C bus answers nothing | I2C shows no waveform and no acknowledge |
| wrong PWM frequency | A PWM output measures a different frequency than configured |
| the DAC pin never leaves its initial voltage | A DAC output stays at the initial voltage |
| watchdog resets under load | The independent watchdog resets the board while the firmware is busy |
| waits misbehave after long uptime or a huge timeout | Waiting misbehaves after long uptime or with a very large timeout |
| a depth-one queue asserts at startup or drops the newest message | A one-slot MPMCQueue asserts at startup or loses the newest message |
| CRC results go wrong once several threads run | CRC results turn wrong in a multithreaded program |
| **Flashing and boot** | |
| HPM ROM ISP download does not work | Downloading through an HPM ROM ISP does not work |
| UART bootloader (BSL) flashing never connects | Flashing an MSPM0 over the UART bootloader never connects |

## Setup on a freshly cloned BSP reports a missing package or a mismatched owner

A fresh clone resolves without edits. When `xrobot setup` cannot find a package, or the error proposes replacing owner or module names line by line, the module list is out of step with the repository state — a pre-1.0 module list, or local rewrites under `Modules/`.

Check:

1. Run `git diff -- Modules/` and `git status --short`. Modifications under `Modules/` on a machine that only cloned the repository indicate local rewrites, not repository content.
2. Read the first lines of `Modules/modules.yaml`. A current list starts with an `xrobot:` pin (for example `xrobot: 1.0.1`) and requests modules as `owner/Repo@ref`. A pre-1.0 list carries no `xrobot:` field and uses legacy owner strings such as `qdu-future/CameraBase`.
3. Check whether the requested module still exists under that name. Repository history contains renames: the `bsp-linux-autoaim` module list once requested `QDU-Robomaster/VisionCapture`, later replaced by `QDU-Robomaster/VisionPreview` and `QDU-Robomaster/VisionRecorder`.

Fix:

1. Restore the repository version of the module list and re-resolve:

   ```bash
   git diff -- Modules/        # confirm the divergence first
   git checkout -- Modules/
   xrobot setup
   ```

2. A pre-1.0 project that must stay on the old toolchain installs an old XRobot instead of rewriting the list:

   ```bash
   pip install 'xrobot<1'
   ```

3. Restore the repository version of the list as a whole. Rewriting package names one error at a time turns one stale list into a second, invented one: for example, the owner from the error message gets substituted, the next module turns out to have been renamed (`VisionCapture` → `VisionRecorder`), and only the repository version resolves the setup.

Links: https://xrobot.work/docs/proj_man/proj-man-setup, https://xrobot.work/docs/proj_man/proj-man-source-man

## A package is not found, or the name is ambiguous

Check:

1. Write the request in canonical `owner/Repo@ref` form (for example `xrobot-org/BlinkLED@same-or-dev`). A bare `Repo` resolves only when exactly one candidate exists across the active sources; several candidates produce an ambiguity error that lists them.
2. Search the active sources for the package and list every source that provides it:

   ```bash
   xrobot source search <text>
   xrobot source find <id>
   ```

   `xrobot source search BMI` prints `xrobot-org/BMI088 [module] https://github.com/xrobot-org/BMI088.git` (output as shown in the XRobot README).
3. Compare the owner string against the index in use. Legacy owner strings such as `qdu-future` still appear in old lists and indexes and may point at repositories under `QDU-Robomaster`; the active index decides what resolves.
4. Read `Modules/sources.yaml` or run `xrobot source list` to see which indexes are consulted. A module published on a second index — the QDU index at `https://qdu-robomaster.github.io/qdu-future-modules/index.yaml`, for example — resolves only when that index is listed.

Fix:

- Correct the request in `Modules/modules.yaml`, or add it with `xrobot module add owner/Repo[@ref]`; add a missing index with `xrobot source add-source <url> [--priority N]`; then run `xrobot setup`.
- When the module was renamed, request the new name.

Links: https://xrobot.work/docs/proj_man/proj-man-source-man, https://xrobot.work/docs/proj_man/proj-man-setup

## xrobot.lock disagrees with Modules/modules.yaml, or `setup --frozen` fails

`setup --frozen` checks out exactly the commits recorded in `xrobot.lock`. The request set, the `xrobot:` pin, and the lock format must all agree.

Check:

1. Compare the requests in `Modules/modules.yaml` with the `requests:` section of `xrobot.lock`; order and case do not matter. The error lists the differences (added, removed, or modified requests) and names each request as `owner/name@ref`, as in `Modules/modules.yaml requests team/A@missing: ...`.
2. Confirm `xrobot.lock` exists. Without a lock, run `xrobot setup` once without `--frozen` to create it.
3. Compare the installed tool with the pin: `xrobot --version` against the `xrobot:` field of `Modules/modules.yaml`. Under `--frozen` a mismatch, or a missing pin, is an error; a plain `xrobot setup` warns instead, and `xrobot describe` reports pin diagnostics.
4. Inspect the lock format. A lock whose version differs from 1, that contains `directory` entries, or whose commits are not 40-character hex strings is stale and needs regeneration.
5. Confirm `--frozen` is not combined with `--update` or `--offline`; the options are mutually exclusive.
6. Read the lock header: `# Generated by `xrobot setup`; do not edit by hand.` Hand-edited locks cause most disagreements.

Fix:

- Refresh the lock after intentional changes to `Modules/modules.yaml`:

  ```bash
  xrobot setup
  ```

  or re-resolve only named modules with `xrobot setup --update <module> ...`. `--frozen` reports an error reading `internal: --frozen would change xrobot.lock` when the checked state would rewrite the lock; re-resolve without `--frozen` first.
- Regenerate a stale-format lock with `xrobot setup --update`.
- A release-gate failure (`xrobot setup --frozen --release-ref <ref>`) prints the fixing command, in the form `xrobot setup --update --context-ref refs/heads/dev [<module> ...]`.

Links: https://xrobot.work/docs/proj_man/proj-man-setup

## The installed generator does not match the BSP pin

STM32 and MSPM0 BSPs record the CodeGenerator version as `generator:` in `User/libxr_config.yaml`; the XRobot tool version is pinned as `xrobot:` in `Modules/modules.yaml`.

Check:

1. Read both pins: `generator:` in `User/libxr_config.yaml` and `xrobot:` in `Modules/modules.yaml`.
2. Compare with the installed tools:

   ```bash
   libxr --version
   xrobot --version
   ```

3. When the versions differ, a plain `xrobot setup` warns and `xrobot describe` reports the pin state; `setup --frozen` fails until the installed XRobot matches the `xrobot:` pin. CI reports a missing pin with `Pin xrobot in Modules/modules.yaml and generator in User/libxr_config.yaml`.

Fix:

- Install the versions recorded by the pins of the repository being built, for example:

  ```bash
  pip install xrobot==1.0.1 libxr==6.0.1
  ```

  The pin is the authority: install the pinned version rather than lowering the `xrobot:` pin to match an older installed tool.
- A project whose list carries no `xrobot:` pin and whose requests use pre-1.0 owner strings stays on the old tool instead: `pip install 'xrobot<1'`, as in Fix 2 of the first entry of this file.
- The `generator:` pin applies to the STM32 and MSPM0 BSPs; `bsp-hpm5301evklite` ships no `User/libxr_config.yaml`.

Links: https://xrobot.work/docs/proj_man/proj-man-setup, https://xrobot.work/docs/code_gen/stm32

## The format check or the line-ending check fails

CI runs `xrobot format --check` plus a check that tracked text files contain no CRLF line endings.

Check:

1. Run `xrobot format --check` locally. Files it names need the canonical layout.
2. Inspect line endings: `git config core.autocrlf` and the repository `.gitattributes`. A BSP initializes `.gitattributes` with `* text=auto`, `*.sh text eol=lf`, and `*.bat text eol=crlf`; module checkouts are cloned with `-c core.autocrlf=false` so the generated header digest stays identical across platforms.
3. Look for edited files whose working-tree copy carries CRLF while the repository expects LF.

Fix:

- Rewrite the configs into the canonical layout:

  ```bash
  xrobot format
  ```

- Normalize line endings through git instead of an editor:

  ```bash
  git add --renormalize .
  ```

- Keep `core.autocrlf` consistent with the repository settings; the CI check expects `* text=auto` in `.gitattributes`.

Links: https://xrobot.work/docs/proj_man/proj-man-config

## Submodules are not initialized

Check:

1. Run `git submodule status`. An uninitialized submodule is listed with a leading `-`, for example `-5161373dbe6d9d9fb1904d90e0ebd4344a44047a libxr`, and its directory is empty.
2. A clone without `--recursive` registers submodules without initializing them; the BSP READMEs clone with `git clone --recursive`.

Fix:

```bash
git submodule update --init --recursive
```

Then rerun the flow from the start (`xrobot setup`, then CMake). The LibXR submodule sits at `Middlewares/Third_Party/LibXR` in the STM32 BSPs and at `libxr/` in the others.

Links: https://xrobot.work/docs/quick_start

## USB CDC does not enumerate, or the port carries no data

Check:

1. Confirm enumeration on the host first: Windows Device Manager, or `lsusb` and `dmesg` on Linux. A device that never appears is an enumeration problem; a device that appears but delivers no data is a data-path problem.
2. For enumeration failures, work outward from the board: cable and power first (a charge-only cable or an insufficient supply fails here), then descriptors and drivers on the host. On Linux, `dmesg` error codes classify the failure: `-110` marks a timed-out request, `-71` (EPROTO) marks CRC or signaling errors, and `-62` marks a device that stops answering — which also happens while the target is halted under a debugger.
3. For missing data, confirm the firmware writes to the CDC port that the host opened, and that `terminal_source` in `User/libxr_config.yaml` names that port — bsp_stm32f103 ships `terminal_source: usb_fs_cdc`, and a console bound to another object leaves the CDC link silent while enumeration succeeds.
4. After `terminal_source` or the CDC registration changed, rebuild and reflash; the running firmware still carries the old binding until then.
5. `CDCToUart` forwards the host's line-coding changes (baud rate, parity, stop bits) to the bridged UART through `SetConfig` and discards its return code, so a configuration the UART refuses stays invisible to the host.

Fix:

- Replace the cable or port, power the board from a source that sustains enumeration, and select the correct host driver.
- Point `terminal_source` at the CDC registration, or write to the CDC object from the application, then regenerate the entry with the platform setup command (`libxr stm32 setup -d . --xrobot`).

Links: https://xrobot.work/docs/basic_coding/driver/usb

## CAN transmission or reception misbehaves

Check:

1. Termination: the bus carries a 120 ohm terminator at each end. A missing or doubled terminator produces intermittent errors before total failure.
2. Bit rate: both nodes configure the same bit rate, including the timing settings that come from the configuration tool (CubeMX `.ioc`, SysConfig `.syscfg`, Pinmux Tool `.hpmpc`).
3. Automatic retransmission: when it is disabled, a frame that loses arbitration while another node transmits is cancelled. The cancelled frame is the expected behavior of that configuration.
4. Counters: read TX/RX and error counters on both nodes to separate frames that were never sent from frames that were sent and lost on the wire. `CAN::GetErrorState(state)` returns TEC, REC and the bus-off, error-passive and error-warning flags, and reports `ErrorCode::NOT_SUPPORT` on a driver that does not implement it.
5. Receive side: `CAN::Register(cb, type, mode, start_id_mask, end_id_mask)` subscribes to frames by type and by an `ID_MASK` or `ID_RANGE` filter; a callback runs in the driver's receive context, interrupt context included, so a handler hands the frame off instead of doing long work (references/libxr-core.md). `AddMessage(pack)` returns an `ErrorCode` for every transmit request.

Fix:

- Terminate the bus and match bit rates before changing software.
- With automatic retransmission disabled, cancelled frames are expected and the application resends when needed; enable retransmission when every frame must arrive.

Links: https://xrobot.work/docs/basic_coding/driver/can, https://xrobot.work/docs/perf/perf-can

## The serial console produces no output

A silent port sits somewhere on a five-step path: the vendor project, the pin multiplexing, the generated code, the clock and framing, the host program.

Check:

1. Vendor project: the USART/UART/LPUART instance is enabled and its mode includes the transmitter. LibXR binds the transmit path only for a handle whose mode carries `UART_MODE_TX`, so a receive-only configuration leaves writes unclaimed.
2. Pin multiplexing: the transmit and receive pins take the peripheral function in the vendor tool — the `.ioc` label on STM32, the pin mux in the `.syscfg` on MSPM0, the assignment in the `.hpmpc` on HPM — and the transmit pin is not left in another function.
3. Generated code: `User/app_main.cpp` declares the object and registers it (`static STM32UART usart1(&huart1, usart1_rx_buf, usart1_tx_buf, 5);` with `XR_REGISTER(usart1, LibXR::UART)`); the object name is the lowercase instance on both platforms (`usart1`, `uart0`). `User/libxr_config.yaml` names the console in `terminal_source`; `-t usart1` writes it. An edited vendor project with a stale object set needs `libxr stm32 setup -d . --xrobot` (or `libxr mspm0 setup -d . --xrobot`) and then `xrobot gen`.
4. Transmit DMA: the STM32 constructor asserts when the mode includes the transmitter and the HAL handle has no `hdmatx`. MSPM0 generation stops earlier with `uart0: no DMA TX channel in the SysConfig project ... the MSPM0 UART driver constructs only with DMA TX`. Enable DMA TX with its trigger, or drop the port. HPM differs again: the generator creates no UART objects, and a configured source warns `terminal_source '<name>' has no effect: the HPM generator creates no UART, so the terminal is not initialized`.
5. Clock, rate and framing: the peripheral clock runs, and the configured baud rate is non-zero — `SetConfig` reports `ARG_ERR` for 0. The hardware word follows the data-bit and parity mapping: 8 data bits without parity is an 8-bit word, 7 with parity is 8, 8 with parity is 9, and stop bits take 1 or 2; other combinations are refused before the configuration is applied. In 7-bit mode the received byte is defined in its low seven bits only, and masking belongs to the application.
6. Host program: it opens the port the board actually presents — a CDC port, or the bridge-chip serial link (115200 on the MSPM0 board's CH340N) — at the configured rate and framing. A garbled stream points here; a completely silent one points back at steps 1 to 4.

Fix:

- Work the steps in order and stop at the first mismatch; a change in the vendor project or in `User/libxr_config.yaml` is followed by the regeneration pair `libxr stm32 setup -d . --xrobot` and `xrobot gen`.
- Keep `terminal_source` on a UART object that exists in the generated code.

Links: https://xrobot.work/docs/basic_coding/driver/uart, https://xrobot.work/docs/code_gen/stm32/stm32-code-gen-uart, https://xrobot.work/docs/perf/perf-uart

## I2C shows no waveform and no acknowledge

A bus where nothing answers is electrical before it is software.

Check:

1. The pins run in open-drain mode and SCL and SDA carry pull-up resistors. A push-pull pin configuration or a missing pull-up keeps the line from ever falling and rising; the driver leaves the electrical behavior to the hardware, so a bus that answers nothing starts here.
2. Both SCL and SDA are assigned in the vendor project. On HPM, an I2C instance missing one of the two generates no object and appears under `Other` in the parse summary instead.
3. The clock speed is non-zero — `SetConfig` reports `ARG_ERR` for a speed of 0 — and the address matches the device's own strapping.

Fix:

- Correct the pin mode, the pull-ups, or the missing line in the hardware or the vendor project, then regenerate and retest before changing any application code.

Links: https://xrobot.work/docs/basic_coding/driver/i2c, https://xrobot.work/docs/code_gen/stm32/stm32-code-gen-i2c

## A PWM output measures a different frequency than configured

The return code of the PWM interface describes the call, not the pin: read the waveform with a scope or a frequency counter before changing the application.

Check:

1. A measured frequency exactly twice the requested one on an STM32F4 part that carries the `TIMPRE` bit (F410, F412, F413, F423, F427, F429, F437, F439, F446, F469, F479 — the common F407 has none) with the APB prescaler at 4, 8 or 16: `TIMPRE` set makes the timer clock four times the APB clock while the driver derives two. Keep the APB prescaler at 1 or 2, or request half the intended frequency. H5 and H7 derive the multiplier from `TIMPRE`.
2. Full scale on a 16-bit timer: the compare value comes from the period scaled by the duty, so a duty of 1.0 on an advanced-control timer (TIM1, TIM8) whose period register reached its 16-bit maximum wraps to 0 and the output stays inactive for the whole period; 32-bit timers (TIM2, TIM5) are unaffected. Request a duty slightly under full scale, or lower the frequency so the period stays below the register maximum.
3. A requested period of one count leaves the counter frozen and the output at a constant level for every duty below full scale, while the calls still report OK. Check the frequency and prescaler pair the driver computed.
4. Channels sharing one timer stop together: stopping one channel clears the timer-level enable along with the channel. A break input active on an advanced-control timer clears the main output asynchronously, so a successful enable call can still leave the pin dead.
5. On an HPM part with a dedicated PWM peripheral, a GPTMR instance generates no PWM object — the generator lists it under `Other`; the GPTMR path produces PWM only on a part without a PWM peripheral. Attach duty-cycle loads to the dedicated PWM instance.

Fix:

- Match the APB prescaler and the `TIMPRE` expectation, keep the duty below full scale on 16-bit timers, keep one channel's stop semantics in mind when channels share a timer, and treat a scope reading as the acceptance criterion for a PWM change.

Links: https://xrobot.work/docs/basic_coding/driver/pwm, https://xrobot.work/docs/code_gen/stm32/stm32-code-gen-pwm, https://xrobot.work/docs/code_gen/hpm

## A DAC output stays at the initial voltage

Every `Write` reports OK while the pin holds the voltage the object was constructed with.

Check:

1. The trigger setting of the DAC channel in the vendor project. The driver's constructor starts the channel once and `Write` only loads the data register, so a channel armed with a software or external trigger transfers nothing after that start; a channel with the trigger disabled updates as soon as the register is written.
2. The reference voltage passed to the constructor: written values are clamped to it, so a reference read from the wrong pin scales the whole output range.
3. The return code, which tracks the register write and not the analog output — measure the pin.

Fix:

- Leave the DAC trigger disabled in the vendor project and regenerate, or drive the trigger from the application for each update; verify the pin with a meter instead of with the call result.

Links: https://xrobot.work/docs/basic_coding/driver/dac, https://xrobot.work/docs/code_gen/stm32/stm32-code-gen-dac

## The independent watchdog resets the board while the firmware is busy

Resets that line up with a flash write or with a CPU-bound loop point at the feeding task rather than at the watchdog.

Check:

1. The flash structure: on a single-bank part (STM32G4 class) an erase or program operation stalls the core for its whole duration, so ticks lag and nothing runs — including the feed — while a write is in flight.
2. Task priorities: a CPU-bound loop running above the LibXR timer task starves the feed, and the reset follows at the timeout. Bound the loop or lower its priority.
3. The window configuration: keep the `MX_IWDG_Init()` call generated by CubeMX. On IWDG families that have the window feature, LibXR sets `IWDG_WINDOW_DISABLE` on the handle it configures, so a window left open by hand-edited initialization code is a source of frequent resets.
4. The timeout against the longest blocking operation, measured rather than estimated.

Fix:

- Feed from a context that outranks the busy work, and size the feed interval to cover the erase and program time of a single-bank flash, or move long flash writes to a moment where the margin covers them.

Links: https://xrobot.work/docs/basic_coding/driver/watchdog, https://xrobot.work/docs/basic_coding/driver/flash

## Waiting misbehaves after long uptime or with a very large timeout

Durations in the LibXR interfaces count milliseconds in 32-bit quantities, so the count wraps after 2^32 ms — a little under 50 days.

Check:

1. A host (Linux) program kept running for weeks: a relative wait rebuilt into an absolute deadline reads as the past once the count wraps, the sleep returns immediately, and the timer thread runs at full CPU. Days-long service reaches the boundary although CI never does, so long-running hosts get a check near 2^32 ms of uptime.
2. A wait asked for as `UINT32_MAX` in place of "forever": backends split on the reading — some block indefinitely, some treat it as a real 2^32 ms ceiling and return `TIMEOUT` when it expires. Code that assumes one meaning on all platforms changes behavior with the target.
3. Elapsed-time arithmetic written as plain unsigned subtraction, which loses the wrap handling the time helpers provide; a timeout computed that way can expire immediately around the boundary.

Fix:

- Keep single waits well below 2^32 ms and re-arm them, compute elapsed time through the time helpers rather than raw subtraction, and treat `TIMEOUT` from a maximal wait as a retry point instead of a fatal error.

Links: https://xrobot.work/docs/basic_coding/core/core-time, https://xrobot.work/docs/basic_coding/system/timer, https://xrobot.work/docs/basic_coding/system/thread

## A one-slot MPMCQueue asserts at startup or loses the newest message

The multi-producer multi-consumer queue requires a capacity above one.

Check:

1. The declared capacity: `MPMCQueueBase` asserts `capacity_ > 1` when the queue is constructed, so a build with `LIBXR_DEBUG_BUILD` defined stops at startup on a one-slot queue. Without that flag the expression is evaluated and its result discarded: the next push overwrites an element nobody popped, and a consumer then waits on a slot that has already moved on.
2. The intent behind a depth of one: latest-value handoff — one producer publishing, one consumer polling the newest value — belongs to `LatestSnapshot`, which skips intermediate values by design; slots shared with interrupts belong to `SlotPool`.
3. Ported code: a queue type replaced in place keeps the old single-slot capacity and inherits the violation.

Fix:

- Give the queue a real capacity of at least two, or move the latest-value pattern onto `LatestSnapshot` and the interrupt-shared pattern onto `SlotPool` (selection table: references/containers.md).

Links: https://xrobot.work/docs/basic_coding/structure/mpmc_queue, https://xrobot.work/docs/basic_coding/structure/latest_snapshot, https://xrobot.work/docs/basic_coding/structure/slot_pool

## CRC results turn wrong in a multithreaded program

At the baseline version, the CRC lookup tables are built lazily on first use and the build is not synchronized.

Check:

1. Whether two threads can reach CRC8, CRC16, CRC32 or CRC64 for the first time at the same moment. The build fills the table in place and sets the initialized flag last, so a racing first call leaves a corrupted table that the process keeps for its whole life — every later result of that CRC is wrong, including for the thread that won the race.
2. Who calls first: logging, packet encoding, and flash-image validation all touch the tables, so the corruption can appear long after startup and far from its cause.

Fix:

- Compute one CRC value from a single thread before the threads that use the utility start; the damage is per process, so one warm-up call covers every later user of that CRC.

Links: https://xrobot.work/docs/basic_coding/utils/crc

## Regenerating an HPM project breaks the build or the config check

In `bsp-hpm5301evklite`, `User/app_main.cpp` is maintained by hand. Running `libxr hpm setup` on it overwrites the file and changes the registered names from the BSP's `LED` and `KEY` to the raw pin names of the Pinmux Tool project (`pa10`, `pa3`), after which `xrobot gen` fails:

```
User/xrobot.yaml: blink_led.args.led: LED is neither an XR_REGISTER name nor an earlier instance id; candidates of type LibXR::GPIO&: pa10, pa3
```

Check:

1. Read the header comment of `User/app_main.cpp`. Hand-maintained files carry a descriptive comment; generated files start with `// Generated by `libxr gen`; do not edit by hand.`
2. Run `git diff -- User/` to see whether regeneration replaced the hand-written entry.
3. Compare the `XR_REGISTER` names in the current file with the names used by the config (`args:` such as `led: LED`).

Fix:

- Restore the hand-written entry when the BSP ships one:

  ```bash
  git checkout -- User/app_main.cpp User/app_main.h
  xrobot gen
  ```

- When regeneration is intended — a new project, or a deliberate rework — redo the registrations with the generated names and update the config arguments to match (`LED` → `pa10`, `KEY` → `pa3` in this example). `libxr hpm setup` also creates a default `User/libxr_config.yaml` when the BSP carries none.

Links: https://xrobot.work/docs/code_gen/hpm

## Downloading through an HPM ROM ISP does not work

The ISP loop in the HPM5301-class ROM polls UART only, and a debugger attached to the session ends it.

Check:

1. Entry: hold KEY&BOOT while RESET is pulsed, and where the same button doubles as a user key, release it before the final reset so the boot condition is not re-asserted.
2. Transport: the ROM ISP on this part runs over UART0, and the ISP loop polls that interface only.
3. Debugger: attaching J-Link to a running ISP session raises the debug interrupts (DEBUG0/1) and stops the ISP loop, so state read from the debugger during that session is not the ISP's. JTAG download of an application image is a separate path and stays available (references/build-flash-debug.md).
4. Board-level causes when the UART path also fails: the pin multiplexing and PHY configuration of the ISP pins, and the crystal frequency, against the datasheet of the exact model; the SDK's USB example running on the same board separates a board fault from a download-flow fault.
5. A board that shipped with a bootloader: a `flash_xip` image is linked over the region holding it, and a whole-chip erase removes the bootloader with nothing to restore it from. Back up the full flash first. When a running application re-purposes the debug pins, asserting the BOOT pin during reset reaches the ROM ISP, which re-enables the debug interface.

Fix:

- Download over the UART ISP or over JTAG with J-Link or OpenOCD on HPM5301-class boards; enter the ISP with no probe attached and connect the host to UART0.

Links: https://xrobot.work/docs/env_setup/env-setup-hpm, https://xrobot.work/docs/debug/jtag, https://github.com/hpmicro/hpm_sdk

## The module main function is not updated after `libxr ... setup`

`libxr stm32 setup`, `libxr mspm0 setup`, and `libxr hpm setup` regenerate the BSP entry files and print:

```
[INFO] Next: run `xrobot gen` to bring User/xrobot_main.hpp up to date; libxr setup does not update it
```

Check:

1. After any `libxr ... setup`, look for the `Next:` line in the output.
2. When a stale main function is suspected, rerun `xrobot gen`; an unchanged header reports `User/xrobot_main.hpp for <config> is unchanged`.

Fix:

```bash
xrobot gen
```

`User/xrobot_main.hpp` belongs to the `xrobot` tool; the `libxr` setup commands leave it untouched.

Links: https://xrobot.work/docs/proj_man/proj-man-gen-main

## The Linux build fails on missing libudev

The Linux driver layer of LibXR requires libudev. On a minimal system, `cmake --preset ...` fails with:

```
-- Checking for module 'libudev'
--   Package 'libudev', required by 'virtual:world', not found
CMake Error at <cmake>/Modules/FindPkgConfig.cmake:645 (message):
  The following required packages were not found:

   - libudev
```

with the call stack pointing at `libxr/driver/linux/CMakeLists.txt`.

Check:

1. Confirm `libudev` appears under `The following required packages were not found`.
2. Read the other messages in the same configure run: a missing `wpa_client` prints a warning with its own install command (`sudo apt install libwpa-client-dev libnm-dev`) and only disables the Wi-Fi driver.

Fix:

```bash
sudo apt install libudev-dev
```

Rerun the CMake configure afterwards. Detection backends such as HailoRT or OpenVINO are optional at configure time: the project configures with `ArmorDetector backends: HailoRT=0 OpenVINO=0` and builds without them.

Links: https://xrobot.work/docs/env_setup/env-setup-linux

## `libxr mspm0 setup` reports that SysConfig cannot run

The MSPM0 generation step needs the TI tools. Without them the command fails with:

```
[ERROR] .: no SysConfig output newer than <board>.syscfg found under build*, cmake-build*, out, and SysConfig cannot run: SYSCONFIG_TOOL is not set; MSPM0_SDK_INSTALL_DIR is not set (the environment variables the CMake build uses). Build the project once, or set them and run `libxr parse` again.
```

Check:

1. Confirm both variables are exported: `MSPM0_SDK_INSTALL_DIR` (the MSPM0 SDK directory) and `SYSCONFIG_TOOL` (the SysConfig CLI: `sysconfig_cli.sh` on Linux and macOS, `sysconfig_cli.bat` on Windows).
2. The official build image `ghcr.io/xrobot-org/docker-image-mspm0:main` ships the SDK, SysConfig, and both variables.

Fix:

- Set both variables and rerun, or build the project once — the CMake build runs SysConfig and leaves output under `build/<preset>/syscfg/` — and rerun `libxr mspm0 setup -d .`.

Links: https://xrobot.work/docs/env_setup/env-setup-mspm0, https://xrobot.work/docs/code_gen/mspm0

## Flashing an MSPM0 over the UART bootloader never connects

The ROM bootloader opens a fixed window measured from the moment it is invoked, and manual entry usually starts that window before the host is ready.

Check:

1. The window: after invocation the BSL polls the interface for a connection packet for 10 s, then falls into STANDBY, which only a power-on reset leaves; inside the command phase, 10 s of idle re-locks the bootloader and later commands go unanswered. The host has to already be streaming connection packets at an interval of 0.5 s or less when BSL and RESET are pressed — entering BSL first and connecting afterwards fails every time. TI's MSPM0 bootloader application note (SLAU887A) describes the flow; the link runs at 9600 8N1 while the same physical port serves the terminal at 115200.
2. The reset sequence: hold the BSL entry condition while RESET is pulsed, then release it.
3. The aftermath of a cut-short session: a failed BSL session can leave the sticky NMI state `SRAMDED`, and every later reset then lands in `Default_Handler`. Clear it through `NMIICLR` before reading the board as dead.
4. The J-Link alternative: a device-specific connection resets the target on connect, so attach as `Cortex-M0+` to inspect without a reset. On MSPM0G3507 the first standalone verify after programming can report a wrong CRC and match on a retry — verify in 1 KB blocks with one retry.
5. Windows hosts: `JLink.exe` on `PATH` can resolve to the JDK's `jlink`, a Java tool of the same name whose usage text has nothing in common with SEGGER's commander. Print the banner with `JLink.exe -?` first, or script the full path of the J-Link installation.
6. Software entry on MSPM0G351x: reading the FACTORY region after the clock initialization HardFaults — errata FLASH_ERR_01 (SLAZ758E) covers the flash wait state that MCLK above 32 MHz requires, and the SDK example that sizes SRAM for the bootloader-entry path reads that region. Keep that read out of a bootloader-entry path.

Fix:

- Start the host script streaming connection packets, then enter BSL; or skip the manual window entirely with the terminal command `power bootloader`, which resets the firmware into the ROM bootloader while the host already holds the port (references/build-flash-debug.md, references/libxr-core.md).
- Move the flash to SWD with J-Link or XDS110 when the timing window is inconvenient.

Links: https://xrobot.work/docs/env_setup/env-setup-mspm0, https://xrobot.work/docs/debug/swd, https://github.com/TexasInstruments/mspm0-sdk

## The build stops: User/xrobot_main.hpp is stale

The build runs a `Checking that the generated XRobot entry is up to date` step that compares `User/xrobot_main.hpp` against every input the header records — the config, the entry source, and each parsed module header. When any input is newer, the build stops with:

```
User/xrobot_main.hpp is stale: <reason> Run `xrobot gen -c User/xrobot.yaml` in <BSP> before building.
```

Check:

1. Identify what changed since the last generation: configs under `User/`, module sources under `Modules/`, or the lock.
2. Confirm which config should be built. Multiple configs live beside `User/xrobot.yaml` (for example `User/RobotConfig/*.yaml`); `-c` selects one.

Fix:

```bash
xrobot gen -c User/xrobot.yaml
```

Regeneration rewrites the header for the selected config and records a fresh digest; the build then proceeds. After a `libxr ... setup`, run `xrobot gen` to keep both generation layers current (see the entry above).

Links: https://xrobot.work/docs/proj_man/proj-man-gen-main, https://xrobot.work/docs/proj_man/proj-man-config

## pip install fails with externally-managed-environment on Debian/Ubuntu

Debian and Ubuntu system Python rejects a plain `pip install xrobot` with `externally-managed-environment`.

Check:

1. Look for `externally-managed-environment` in the pip output.
2. Check whether pipx is available: `pipx --version`.

Fix:

- Install through pipx:

  ```bash
  pipx install xrobot
  ```

  For a pinned BSP, `pipx install xrobot==1.0.1`.
- Windows installs and virtual environments use plain `pip install xrobot`.

Links: https://xrobot.work/docs/quick_start

## Generation reports errors around XR_REGISTER

The generator collects registrations from source syntax before preprocessing, so `#if` guards have no effect on it.

Check:

1. One registration carries one type, as in `XR_REGISTER(spi1, LibXR::SPI)`. Registering several types from one name is an error that suggests referencing the object and registering each reference separately.
2. Registrations sit outside `#if`, `#ifdef`, `#ifndef`, and `#define`. A conditionally compiled registration desynchronizes the generated bindings from the code that actually compiles. Move the condition to the object instead: a peripheral that is absent produces no object, and the registration line stays unconditional.
3. Each registered name maps to one parameter of `XRobotMain`. On STM32 the generator emits, for each FDCAN, an additional `LibXR::CAN& canX = fdcanX;` with its own registration; a name collision between coexisting CAN and FDCAN objects on the same chip reports an error.

Fix:

- Keep every `XR_REGISTER` line at file scope without preprocessor guards and give it exactly one type; resolve a name collision by renaming the registered object rather than guarding the line.

Links: https://xrobot.work/docs/proj_man/proj-man-gen-main

## Still unresolved

Before repeating a physical step — pressing a button, rewiring, power-cycling — set up a way to observe what the board reports instead: attach a debugger without resetting it, read the fault frame or the relevant registers, or capture the serial log. Evidence from one observation settles what several repetitions cannot.

File the issue in the repository that owns the failing layer, and attach the versions and outputs listed below.

- `xrobot` tool behavior — setup, lock, config checks, generation of `User/xrobot_main.hpp`: https://github.com/xrobot-org/XRobot/issues
- LibXR library and driver behavior: https://github.com/xrobot-org/libxr/issues
- Code generation output — `libxr parse` / `libxr gen` and the platform setup commands: https://github.com/xrobot-org/LibXR_CppCodeGenerator/issues
- Guidance in this skill that is wrong or outdated: https://github.com/xrobot-org/xrobot-skills/issues

Attach: `xrobot --version` and `libxr --version`; the pins (`xrobot:` in `Modules/modules.yaml`, `generator:` in `User/libxr_config.yaml`); the BSP and LibXR submodule commits (`git log -1`, `git submodule status`); the full command output; and the steps that reproduce the failure. SKILL.md ends with the same routing.
