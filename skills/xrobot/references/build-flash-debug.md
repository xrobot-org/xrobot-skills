When to read this: Configuring and building an XRobot BSP or LibXR template project, flashing a target, or starting a debug session.

# Build, flash and debug

CMake presets are the build entry of every BSP: `cmake --preset <name>` configures into `build/<name>`, and `cmake --build --preset <name>` builds. The standard sequence, with [bsp_stm32f103](https://github.com/xrobot-org/bsp_stm32f103) as the example:

```bash
git clone --recursive https://github.com/xrobot-org/bsp_stm32f103.git
cd bsp_stm32f103
pip install xrobot==1.0.1     # the version of the xrobot: pin in Modules/modules.yaml
xrobot setup
cmake --preset debug
cmake --build --preset debug
```

- Install the tool versions the repository pins: `xrobot:` from `Modules/modules.yaml`, and `generator:` from `User/libxr_config.yaml` where present. Quick-start blocks in BSP READMEs can lag behind the pins recorded in the files.
- BSPs that carry several product configurations build one at a time: run `xrobot gen -c <config>` first, with `<config>` pointing at one of the BSP's config files — for example a minimal debug configuration or the full-featured one ([bsp-dev-c](https://github.com/QDU-Robomaster/bsp-dev-c) keeps several under `User/RobotConfig/`; [bsp-linux-autoaim](https://github.com/QDU-Robomaster/bsp-linux-autoaim) generates from `User/xrobot.yaml`). Single-config BSPs skip this step — `xrobot setup` already generated for `User/xrobot.yaml`.
- The build stops when `User/xrobot_main.hpp` is stale relative to its inputs; run `xrobot gen` to refresh it.

## Presets and artifacts

| Repository (platform) | Presets | Configure + build | Artifact |
| --- | --- | --- | --- |
| bsp_stm32f103, bsp-dev-c (STM32) | debug, relWithDebInfo, release, minSizeRel | `cmake --preset debug` then `cmake --build --preset debug` | `build/debug/BluePill.elf` / `build/debug/DevC.elf` |
| bsp-mspm0g3507-mini (MSPM0) | debug, release | `cmake --preset debug` then `cmake --build --preset debug` | `build/debug/mspm0_minidb48.elf` plus `.hex`/`.bin`/`.map` |
| bsp-hpm5301evklite (HPM) | debug-flash-xip, debug-ram, release-flash-xip | `cmake --preset debug-flash-xip` then `cmake --build --preset debug-flash-xip` | `build/debug-flash-xip/output/demo.elf` plus `.bin` |
| CH32V307_LibXR_Template (CH32) | no presets | `cmake -B build -DCMAKE_BUILD_TYPE=Release` then `cmake --build build -j"$(nproc)"` | `build/CH32V307VC.elf` plus `.hex`/`.bin` |
| bsp-linux-autoaim (Linux host) | debug, relWithDebInfo, release | `cmake --preset release` then `cmake --build --preset release --target rm_auto_aim` | `build/release/rm_auto_aim` (host executable) |

Platform toolchain notes:

- STM32: the presets use the ST `starm-clang` toolchain (`cmake/starm-clang.cmake`, provided by STM32CubeCLT or the VS Code STM32Cube extension, on `PATH`). `libxr stm32 toolchain gcc` switches the default preset to `cmake/gcc-arm-none-eabi.cmake` and removes existing build directories.
- MSPM0: set `MSPM0_SDK_INSTALL_DIR` and `SYSCONFIG_TOOL` before configuring; CMake runs SysConfig at configure time and writes the results to `build/<preset>/syscfg/` (generated, not committed).
- HPM: set `HPM_SDK_BASE` (HPM SDK v1.13.0) and `GNURISCV_TOOLCHAIN_PATH`. The preset name selects `HPM_BUILD_TYPE`: `flash_xip` runs from the on-board QSPI flash, `ram` runs entirely from the 128 KiB ILM.
- CH32: requires the WCH RISC-V GCC 15.2+ toolchain (`riscv32-wch-elf-`); configure fails on older toolchains. Pass `-DCOMPILER_PREFIX=<prefix>` when the compiler is off `PATH`.
- Linux: a host build needing a C++20 compiler, CMake, Ninja, OpenCV 4, Eigen 3 and `libudev` (Debian package `libudev-dev`). The HailoRT (infantry/hero configs) and OpenVINO (sentry config) detection backends are optional at build time — with neither installed, the project configures and compiles with detection disabled. Missing `wpa_client`/`libnm` produce warnings only.

## Building in Docker

The CI images are public on GHCR and carry the vendor toolchains:

- `ghcr.io/xrobot-org/docker-image-mspm0:main` — the MSPM0 SDK and SysConfig 1.28.1 that the BSP's build requires, plus arm-none-eabi-gcc, with `MSPM0_SDK_INSTALL_DIR` and `SYSCONFIG_TOOL` preset.
- `ghcr.io/xrobot-org/docker-image-hpm:main` — HPM SDK v1.13.0 and the HPM RISC-V GCC toolchain. One-shot build of bsp-hpm5301evklite:

```bash
docker run --rm -v "$PWD:/src" -w /src ghcr.io/xrobot-org/docker-image-hpm:main \
  bash -c 'pip install xrobot==1.0.1 && xrobot setup && cmake --preset debug-flash-xip && cmake --build --preset debug-flash-xip'
```

- `ghcr.io/xrobot-org/docker-image-ch32-riscv:main` — the WCH RISC-V GCC toolchain, CMake and WCH's OpenOCD. One-shot build of the CH32 template:

```bash
docker run --rm -v "$PWD:/work" -w /work ghcr.io/xrobot-org/docker-image-ch32-riscv:main \
  bash -c 'cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j"$(nproc)"'
```

- `ghcr.io/xrobot-org/docker-image-stm32:main` — the image the shared STM32 BSP CI builds in.

Inside a container, install the `xrobot` release matching the version pinned by the project (`xrobot:` in `Modules/modules.yaml`), as shown in the HPM command.

## Flash

When the board's BSP is unknown, identify the chip first: read the IDCODE or unique ID through the debug probe and match it to a row below. Before scripting a flash, read the vendor's own user guide and official example for the exact boot and download flow of the chip at hand — bootloader entry, ISP, DFU, option bytes, reset levels — and carry the published errata workarounds into the procedure.

| Platform | Debug interface | Flashing |
| --- | --- | --- |
| STM32 (bsp_stm32f103, bsp-dev-c) | SWD | STM32CubeProgrammer CLI: `STM32_Programmer_CLI --connect port=swd --download build/debug/BluePill.elf -hardRst -rst --start` — the VS Code task "CubeProg: Flash project (SWD)" wraps it. Release `.hex`/`.bin` files flash with any SWD tool. OpenOCD alternative for the STM32F103: `openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "program build/debug/BluePill.elf verify reset exit"`. |
| MSPM0G3507 (bsp-mspm0g3507-mini) | SWD | J-Link: `JLinkExe -Device MSPM0G3507 -If SWD -Speed 4000 -AutoConnect 1`, then `loadfile build/debug/mspm0_minidb48.elf`, `r`, `g`. XDS110 works as well. For UART flashing, the terminal command `power bootloader` resets into the ROM bootloader over the on-board CH340N serial link. |
| HPM5301 (bsp-hpm5301evklite) | JTAG | J-Link: `JLinkExe -Device HPM5301xEGx -If JTAG -JTAGConf -1,-1 -Speed 4000 -AutoConnect 1`, then `loadfile build/debug-flash-xip/output/demo.elf`, `r`, `g`. OpenOCD runs with the SDK configurations plus the board's `hpm5301evklite.cfg`. Hold KEY&BOOT through reset for the ISP boot mode; the ROM ISP on this part polls UART only (references/troubleshooting.md). |
| CH32V307 (CH32V307_LibXR_Template) | WCH-LinkE (SDI) | WCH's OpenOCD build: `openocd -f wch-riscv.cfg`. The template's VS Code configurations ("Launch CH32V307" / "Attach CH32V307", Cortex-Debug) download and debug `build/CH32V307VC.elf`. |
| Linux (bsp-linux-autoaim) | — | No flashing: the product is a host executable (below). |

Interface summary: STM32 and MSPM0 debug over SWD, HPM5301 exposes JTAG, and CH32 uses WCH's SDI transport through WCH-LinkE, which needs WCH's OpenOCD build rather than mainline OpenOCD. The [debug documentation](https://xrobot.work/docs/debug) is the reference for the SWD (https://xrobot.work/docs/debug/swd) and JTAG (https://xrobot.work/docs/debug/jtag) setups.

## Debug

- The STM32 BSPs ship VS Code launch configurations for the ST-Link and J-Link GDB servers (STM32Cube extension); bsp-dev-c additionally carries a SEGGER Ozone project (`DevC.jdebug`) and an OpenOCD launcher for CMSIS-DAP probes.
- CH32V307_LibXR_Template debugs through Cortex-Debug with `gdbPath: riscv32-wch-elf-gdb` and `wch-riscv.cfg`, with FreeRTOS awareness.
- After a reset, the firmware terminal comes up on the BSP's configured terminal source (USB CDC on bsp_stm32f103, the CH340N serial link at 115200 on the MSPM0 board) and provides the LibXR shell.
- bsp-linux-autoaim has GDB debug configurations and Remote-SSH tasks under `.vscode/`.

## Run on Linux

bsp-linux-autoaim produces `rm_auto_aim`, a host executable — run it directly from the repository root:

```bash
./build/release/rm_auto_aim
```

For unattended operation, `sudo deploy/install-service.sh` installs a systemd service that restarts the program on exit (`journalctl -u rm-auto-aim -f` follows the logs; `--remove` uninstalls). The detection backend (HailoRT or OpenVINO) and the vision models belong to the runtime environment; the binary runs with detection disabled when both are absent.
