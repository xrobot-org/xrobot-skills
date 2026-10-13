---
name: xrobot
version: 1.0.1
description: "Work on robot firmware with the XRobot/LibXR ecosystem: set up the environment, create or migrate projects, generate code with the libxr and xrobot CLIs, manage Modules and instances, build, flash, and debug, use the LibXR C++ framework and its data structures, and diagnose errors. Covers STM32 (CubeMX), TI MSPM0 (SysConfig), HPMicro HPM (Pinmux Tool), WCH CH32, ESP32 (ESP-IDF), and Linux host programs. Trigger phrases (Chinese): 搭环境 / 建工程 / 生成代码 / 模块 / 编译烧录 / 报错 / 选数据结构"
---

# Working with XRobot and LibXR

This skill serves robot developers working with XRobot and LibXR: it covers environment setup, project creation and migration, code generation, Module management, building and flashing firmware, LibXR usage, and runtime troubleshooting, across STM32 (STM32CubeMX), TI MSPM0 (SysConfig), HPMicro HPM (Pinmux Tool), WCH CH32, ESP32 (ESP-IDF), and Linux host programs.

## Version baseline

Baseline: LibXR v2.0.1 / xrobot 1.0.1 / libxr (CodeGenerator) 6.0.1 / VS Code extension 2.0.1.

Verify the user's actual versions before relying on version-specific details: `xrobot --version`, `libxr --version`, and `pip show xrobot` / `pip show libxr`. When an installed version differs from this baseline, the `--help` output of the installed tools takes precedence: run `xrobot --help`, `libxr --help`, and the `--help` of each subcommand before quoting flags or defaults.

## First checks

Run these steps at the start of a task that touches a project or the toolchain and keep the results at hand. A pure API or data-structure selection question skips steps 2-4 and is answered from references/libxr-core.md or references/containers.md.

1. Record the versions and pins:
   - `xrobot --version` and `libxr --version` print the installed tool versions.
   - The LibXR submodule commit: `git -C Middlewares/Third_Party/LibXR rev-parse HEAD` in CubeMX projects, `git -C libxr rev-parse HEAD` in other BSPs; `git submodule status` lists the path.
   - The `xrobot:` field of `Modules/modules.yaml` (quick check: `sed -n 's/^xrobot: *//p' Modules/modules.yaml`).
   - The `generator:` field of `User/libxr_config.yaml`; some BSPs carry no such file.
   - The installed tools match the pins; for a mismatch, see references/troubleshooting.md.
2. Record the project state. Run `git log -1`, `git status`, and `git diff -- Modules/ User/`. Uncommitted edits under `Modules/` or `User/` change what `xrobot setup` and code generation do; worked examples are in references/troubleshooting.md.
3. Identify the platform. The checks below run in this order and match the detection used by `libxr parse` and `libxr gen`:
   - a `.ioc` file in the project directory: an STM32CubeMX project;
   - `app.yaml` in the root with a `.hpmpc` under `boards/*/`: an HPM SDK project (this identification applies even when a `.syscfg` is also present);
   - a `.syscfg` file in the root: a TI SysConfig (MSPM0) project;
   - none of these, and the directory also holds no `Modules/modules.yaml`, `User/` directory, `CMakeLists.txt` or vendor project file: the directory is not a project root. Locate the project root first, because the remaining checks assume one, and request a directory listing when the contents are unknown;
   - none of these, with a project present: an ESP-IDF project or a Linux host program, both integrating LibXR directly through CMake.
4. Check the toolchain for the identified platform (compiler, CMake, Ninja, vendor SDK or vendor tool). Per-platform requirements: references/env-setup.md.

When a check cannot run in the current environment — a tool is not installed, or the project is not on this machine — record the command verbatim with its failure output, request a run where the project lives, and continue from the complete output that comes back. Record version, pin and file states only from that output.

## Concepts

LibXR is an embedded C++20 framework that presents peripherals (`LibXR::UART`, `LibXR::SPI`) over bare-metal, FreeRTOS, ThreadX, and Linux system layers, and ships middleware, containers, and robotics utilities. The CodeGenerator (PyPI package `libxr`, command `libxr`) reads vendor project files — STM32CubeMX `.ioc`, TI SysConfig `.syscfg`, HPM Pinmux Tool `.hpmpc` — and generates the peripheral objects plus the `app_main` entry for a board. XRobot (PyPI package `xrobot`, command `xrobot`) is the module manager: Modules are ordinary C++ classes published as Git repositories, `xrobot setup` checks them out at the commits locked in `xrobot.lock`, and the instances declared in `User/xrobot.yaml` are compiled into `User/xrobot_main.hpp`, which constructs each instance against the registered hardware and runs their `OnMonitor()` inside the generated `XRobotMain`. A BSP repository ties one board together: the vendor project, the generated `User/app_main.cpp`, hardware registrations (`XR_REGISTER(spi1, LibXR::SPI)`), tool pins, and module requests. Modules and BSPs are discovered through source indexes; the project-management pages describe how sources, setup, and locking work: https://xrobot.work/docs/proj_man. The concept walkthrough with a worked example: https://xrobot.work/docs/concept.

## Decision routing

| Task at hand | Read |
| --- | --- |
| Install the Python tools or a platform toolchain | references/env-setup.md |
| Which PyPI package provides a CLI, and which repository its bugs go to | Concepts and Help and feedback in this file |
| Create a project, import or migrate a BSP, or run code generation | references/new-project.md |
| Enable or change a peripheral, pin or interrupt in the vendor project (`.ioc`, `.syscfg`, `.hpmpc`) | references/new-project.md |
| Add Modules, edit `Modules/modules.yaml`, or manage instances | references/modules.md |
| Which file owns a generated path, and where a hand edit survives regeneration | references/modules.md |
| Work with the VS Code extension | references/vscode-extension.md |
| Build, flash, or debug | references/build-flash-debug.md |
| Flash a board whose chip or BSP is unknown (read IDCODE/UID through the probe, then match the table in Flash) | references/build-flash-debug.md |
| Use LibXR interfaces, threads, or the ISR/thread boundary | references/libxr-core.md |
| Race conditions, data shared between an interrupt and a thread, or unexpected `FULL`/`EMPTY` | references/libxr-core.md (Interrupt and thread boundaries), references/containers.md |
| Choose a data structure | references/containers.md |
| Diagnose an error or unexpected behavior | references/troubleshooting.md |

## References

| File | Purpose |
| --- | --- |
| env-setup.md | Python tools (`xrobot`, `libxr`) and the toolchains and SDKs for STM32, MSPM0, HPM, CH32, ESP32, and Linux. |
| new-project.md | Starting from a vendor project or an existing BSP: `libxr` code generation and the `xrobot init`/`setup` flow. |
| modules.md | Module requests and refs, instances, `User/xrobot.yaml`, and `xrobot.lock`. |
| vscode-extension.md | The XRobot and LibXR views, the pin layout, and the CLI commands behind each action. |
| build-flash-debug.md | CMake presets, flashing tools, and debug sessions per platform. |
| libxr-core.md | Core abstractions: peripherals, read/write ports, threads and callbacks, middleware, ISR/thread boundary. |
| containers.md | Choosing among the queues, pools, snapshots, and lists LibXR provides. |
| troubleshooting.md | Errors and unexpected behavior, with causes and fixes. |

## Help and feedback

File issues in the repository that owns the problem:

- The skill content itself — a wrong or outdated step, command shape, or troubleshooting entry: https://github.com/xrobot-org/xrobot-skills/issues
- Quick questions and community help: the page at https://xrobot.work/qq (issues remain the channel for software bugs)
- `xrobot` CLI, module resolution, or the generated `User/xrobot_main.hpp`: https://github.com/xrobot-org/XRobot/issues
- LibXR runtime library: https://github.com/xrobot-org/libxr/issues
- CodeGenerator (parsing `.ioc`/`.syscfg`/`.hpmpc`, generated `User/app_main.cpp`, `libxr pins`): https://github.com/xrobot-org/LibXR_CppCodeGenerator/issues
- VS Code extension: https://github.com/xrobot-org/xrobot-vscode-extension/issues

Attach the `xrobot --version` and `libxr --version` output, the platform and BSP, the full command with its complete output, and the relevant section of `Modules/modules.yaml` (plus `User/libxr_config.yaml` when generation is involved). The documentation site is https://xrobot.work/.
