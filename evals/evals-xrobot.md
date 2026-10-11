# Evals: `xrobot` (end-user skill)

Baseline: LibXR v2.0.1 / xrobot 1.0.1 / libxr (CodeGenerator) 6.0.1 / VS Code extension 2.0.1.
Each eval is run in an agent with this skill installed. The environment has no hardware and
the `xrobot`/`libxr` CLIs are installed only where noted; when the skill directs a command
that cannot run, the expected behavior is to state the exact command and continue.

| # | Question | Expected behavior |
| --- | --- | --- |
| U1 | Fresh clone of a BSP; `xrobot setup` reports a package not found under an old owner (e.g. `qdu-future/...`). | Runs First checks; inspects `Modules/modules.yaml` (pre-1.0 format: no `xrobot:` pin, old owner); `git diff -- Modules/`; restores the repository version of the manifest; warns against hand-renaming owners (mentions the VisionCapture→VisionRecorder rename pitfall); mentions `xrobot<1` only for genuinely legacy projects. Does NOT edit package names to match the error. |
| U2 | MSPM0 project, UART produces no output. | Checks `.syscfg` UART configuration and the generated code, then version pins (`generator:` 6.0.1); consults the MSPM0 sections of env-setup/new-project; points to the website env_setup page; notes the TI toolchain/Docker image requirement. |
| U3 | How do I add an IMU module to an STM32 project? | Gives the `Modules/modules.yaml` entry format (`owner/name@ref`, `xrobot:` pinned to 1.0.1), runs `xrobot setup`, declares the instance in `User/xrobot.yaml`, runs `xrobot gen`; explains constructor parameters; links the proj_man page. |
| U4 | CAN frames arrive in an ISR; a thread needs only the latest value. Which data structure? | Reads containers.md; answers LatestSnapshot; explains why not MPMCQueue (instantaneous FULL/EMPTY when preempted) and not a plain Queue. |
| U5 | USB CDC device does not enumerate (or enumerates, no data). | Follows troubleshooting.md USB entry in order: cable/power, enumeration view (`lsusb`/Device Manager), descriptors/driver, then host-side behavior. |
| U6 | `xrobot --version` shows 0.9.x but the BSP pins 1.0.1. | Install the pinned version (`pip install xrobot==1.0.1`); for a genuinely legacy BSP mentions `xrobot<1`; does not edit `modules.yaml` to match the old tool. |
| U7 | `User/xrobot_main.hpp` was hand-edited; after regeneration the edits are gone. | Identifies it as a generated file produced by `xrobot gen`; hand edits belong in user-code regions / `User/app_main.cpp`; regenerated files are overwritten by design. |
| U8 | Which pip package provides the `libxr` CLI, and where do its bugs go? | PyPI package `libxr` is the CodeGenerator; issues go to xrobot-org/LibXR_CppCodeGenerator with versions, platform, full command and output. |
| U9 | HPM BSP: after re-running `libxr hpm setup` the build fails; `XR_REGISTER` names changed to `pa10`/`pa3`. | Recognizes setup overwrote the handwritten `app_main.cpp` and renamed registrations; restore the handwritten entry or redo the registrations, then run `xrobot gen`. |
| U10 | Set an event flag from an ISR, wait for it in a thread. | Reads libxr-core.md Event section; states ISR boundary rules (no waiting/blocking/looping in ISR context). |
| U11 | `xrobot setup --frozen` fails. What now? | Lists the failure causes from modules.md; fixes by reconciling the manifest and the lockfile per the documented rules; does not hand-edit `xrobot.lock`. |
| U12 | Two configurations for one board (a minimal debug config and a full config). | Shows the `User/xrobot.yaml` config list mechanism and per-config `xrobot gen -c <file>`; uses generic names, not robot-specific ones; links proj_man. |
| U13 | Flash the built firmware to an STM32 board over SWD. | Uses build-flash-debug.md: CMake preset build, STM32 flashing via STM32CubeProgrammer SWD with the documented command shape. |
| U14 | Inspect files at runtime from the LibXR terminal. | States the built-in terminal commands are `cd` and `ls` only in v2.0.1 (no `cat`); explains RamFS object mounting; links the website page. |
| U15 | Where do I report a bug in `xrobot setup` module resolution, and what do I attach? | xrobot-org/XRobot issues; attaches `xrobot --version` / `libxr --version` output, platform and BSP, full command with complete output, relevant `modules.yaml` section. |
| U16 | UART flashing over the MSPM0 serial BSL always fails. What do I check? | troubleshooting.md MSPM0 BSL entry: the BSL entry window and reset timing, the sticky `SRAMDED` condition, verify-step retry, and the J-Link alternative when the BSL route is not reachable; pins and toolchain state from First checks still apply. |
| U17 | I need to tell a user which interrupts to enable in SysConfig. How should that list be produced? | The list is derived from the code that consumes the interrupts (the driver and generated entry), and each item states what it is for; the enabled interrupts match what the driver expects (new-project.md MSPM0 section / troubleshooting.md); an unexplained list is not handed over. |
