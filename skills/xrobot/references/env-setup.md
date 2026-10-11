When to read this: Installing the host toolchain and the xrobot/libxr Python CLIs for one target platform, and checking the installation before running any project command.

# Environment setup

Version baseline: xrobot 1.0.1, libxr (CodeGenerator) 6.0.1, LibXR v2.0.1. LibXR is a C++20 library; both Python CLIs require Python 3.10 or newer. Command outputs below are examples and may differ by environment; `--help` reports the current form.

## Python CLIs (every platform)

Two command-line tools drive the Python side of every project:

- `xrobot` — module manager and main-function generator (PyPI package `xrobot`).
- `libxr` — the CodeGenerator for STM32, MSPM0 and HPM projects (PyPI package `libxr`, command `libxr`).

A project pins the versions it expects: the `xrobot:` line in `Modules/modules.yaml` pins XRobot, and the `generator:` line in `User/libxr_config.yaml` pins the CodeGenerator. Install exactly the pinned versions. Pick one install method per machine (pipx, pip, or a virtual environment) and stay with it.

pipx (recommended for system Pythons; see the env_setup overview for the three-way choice):

```
python -m pip install --user pipx
python -m pipx ensurepath
python -m pipx install xrobot==1.0.1
python -m pipx install libxr==6.0.1
```

`python -m pipx` works in the shell that ran `ensurepath`; open a fresh terminal so bare `xrobot` and `libxr` resolve from the updated PATH.

pip (example output, last line only; dependency entries differ per environment):

```
$ pip install xrobot==1.0.1 libxr==6.0.1
...
Successfully installed ... libxr-6.0.1 ... xrobot-1.0.1
```

On Debian/Ubuntu the system Python reports `externally-managed-environment` for plain pip installs; use pipx or a virtual environment there.

Check the installation:

```
$ xrobot --version
xrobot 1.0.1
$ libxr --version
libxr 6.0.1
```

The VS Code extension `XRobot.xrobot` drives both CLIs from the editor; the env_setup overview page lists it alongside the CLI installation: https://xrobot.work/docs/env_setup

## STM32

Install git, CMake and Ninja, STM32CubeMX (for `.ioc` projects), and one compiler: `arm-none-eabi-gcc` or ST `starm-clang` (provided by STM32CubeCLT or the VS Code STM32Cube extension). On Debian, the package set is:

```
apt-get update && apt-get install -y git cmake ninja-build make gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi build-essential
```

The Debian packages resolve to git 2.47.3, CMake 3.31.6, Ninja 1.12.1, and arm-none-eabi-gcc 14.2.1 (`15:14.2.rel1-1`).

BSP presets name the toolchain file: `cmake/starm-clang.cmake` by default, with `cmake/gcc-arm-none-eabi.cmake` as the GCC alternative. `libxr stm32 toolchain gcc|clang` switches the default preset (see references/new-project.md).

Platform page: https://xrobot.work/docs/env_setup/env-setup-stm32

## MSPM0

Install the TI MSPM0 SDK (tag `mspm0_sdk_2_11_00_07`) and TI SysConfig 1.28.1, plus arm-none-eabi-gcc, CMake and Ninja. The generator and the CMake build read two environment variables:

```
export MSPM0_SDK_INSTALL_DIR=<sdk directory>
export SYSCONFIG_TOOL=<sysconfig directory>/sysconfig_cli.sh
```

`sysconfig_cli.bat` replaces the script name on Windows; the SDK directory contains `.metadata/product.json`. The SDK lives on GitHub as tag `mspm0_sdk_2_11_00_07` of https://github.com/TexasInstruments/mspm0-sdk.git (about 2.3 GB; a read-only reference copy is enough):

```
git clone --depth 1 --branch mspm0_sdk_2_11_00_07 https://github.com/TexasInstruments/mspm0-sdk.git
```

The official image `ghcr.io/xrobot-org/docker-image-mspm0:main` ships the same SDK and SysConfig versions with both variables preset, and is the route the BSP README itself points to.

Check: with the variables unset and no earlier build output, generation stops and names both variables. Example output:

```
$ libxr mspm0 setup -d . --xrobot
[ERROR] .: no SysConfig output newer than mspm0g3507_minidb48.syscfg found under build*, cmake-build*, out, and SysConfig cannot run: SYSCONFIG_TOOL is not set; MSPM0_SDK_INSTALL_DIR is not set (the environment variables the CMake build uses). Build the project once, or set them and run `libxr parse` again.
```

Setting the two variables — or using the image — clears it. SysConfig output newer than the `.syscfg` under `build*`, `cmake-build*` or `out` is reused in place of a fresh SysConfig run.

Platform page: https://xrobot.work/docs/env_setup/env-setup-mspm0

## HPM

Install the HPM SDK v1.13.0 and the HPM RISC-V GCC toolchain, plus CMake 3.23+ and Ninja. Two environment variables point the build at them:

```
git clone --depth 1 --branch v1.13.0 https://github.com/hpmicro/hpm_sdk.git
export HPM_SDK_BASE="$PWD/hpm_sdk"
export GNURISCV_TOOLCHAIN_PATH=<toolchain directory>
```

(BSP README steps.) The official image `ghcr.io/xrobot-org/docker-image-hpm:main` ships HPM SDK v1.13.0 at `/opt/hpm_sdk/v1.13.0` and the toolchain at `/opt/hpm-riscv32-unknown-elf` (riscv32-unknown-elf-gcc 15.2.0) with both variables preset. The HPM Pinmux Tool — a web application or a VS Code extension — edits the `.hpmpc` project files.

Check: CMake configure prints the resolved SDK and toolchain. Example output:

```
-- Found toolchain: gnu (/opt/hpm-riscv32-unknown-elf)
-- hpm_sdk: 1.13.0 (/opt/hpm_sdk/v1.13.0)
```

Platform page: https://xrobot.work/docs/env_setup/env-setup-hpm

## CH32

Install the WCH RISC-V GCC 15.2+ toolchain with the `riscv32-wch-elf-` prefix, plus CMake and Ninja. CMake stops on older toolchain versions; `-DCOMPILER_PREFIX=<prefix>` selects a toolchain outside PATH. Flashing uses WCH-LinkE with WCH's OpenOCD build. The official image `ghcr.io/xrobot-org/docker-image-ch32-riscv:main` ships riscv32-wch-elf-gcc 15.2.0, CMake and WCH OpenOCD together.

`LIBXR_CH32_CONFIG_FILE` and the remaining platform specifics (WCH peripheral library quirks, SysTick and Flash notes) live on the platform page.

Platform page: https://xrobot.work/docs/env_setup/env-setup-ch32

## ESP32

ESP32 projects are ESP-IDF component projects; LibXR enters the build through `cmake/esp32.cmake` in the LibXR checkout. The ESP32 page of the documentation site covers the IDF version, component-project requirements, build and flash steps: https://xrobot.work/docs/env_setup/env-setup-esp32

## Linux

LibXR host programs need a C++20 compiler, CMake 3.21+, Ninja, pkg-config, OpenCV 4 (core/imgproc/dnn/calib3d), Eigen 3, and the libudev development files. On Debian these come from `libopencv-dev`, `libeigen3-dev`, `libudev-dev` and `pkg-config`.

`libudev` is required: CMake configure fails without it. Example output:

```
$ cmake --preset release
-- Checking for module 'libudev'
--   Package 'libudev', required by 'virtual:world', not found
CMake Error at /usr/share/cmake-3.31/Modules/FindPkgConfig.cmake:645 (message):
...
-- Configuring incomplete, errors occurred!
```

The remediation: `apt-get install libudev-dev`, then rerun configure. `libwpa-client-dev` (with `libnm-dev`) is optional; CMake warns when they are absent and the wifi client driver stays out of the build.

Platform page (Ubuntu 24.04 package list, Clang usage): https://xrobot.work/docs/env_setup/env-setup-linux

## Windows

The Python CLI installation is the same as on Linux: pipx works on Windows too, and after `python -m pipx ensurepath` a fresh terminal should resolve `xrobot` and `libxr` from the pipx bin directory on PATH.

The vendor toolchains install natively: STM32CubeCLT and STM32CubeMX, TI SysConfig, the HPM SDK with its RISC-V GCC, and the WCH toolchain all ship Windows builds. On Windows the SysConfig CLI script is `sysconfig_cli.bat` rather than `sysconfig_cli.sh`, and J-Link Commander is `JLink.exe` — beware of the identically named `jlink` tool a JDK may put on PATH (see the MSPM0 BSL entry in references/troubleshooting.md).

The command examples in this repository are POSIX shell. Run them as written in Git Bash or WSL, or translate them (`nproc` becomes `$env:NUMBER_OF_PROCESSORS` in PowerShell). The `sed -n 's/^xrobot: *//p'` quick check in the SKILL.md First checks section likewise needs a POSIX shell; under PowerShell, read the matching line of the file directly.

Where native vendor-toolchain installation is unwanted, the official Docker images (next section) plus Docker Desktop are the alternative route.

## Docker images

The official images live at `ghcr.io/xrobot-org/docker-image-<platform>:main` (Docker Hub `xrimage/*` mirrors them). The Docker page lists all seven — stm32, mspm0, ch32-riscv, hpm, esp32, linux, webots — with tool versions and the CI mapping of each image. The three below cover mspm0, hpm and ch32-riscv:

| Image | Contents |
| --- | --- |
| `docker-image-mspm0:main` | MSPM0 SDK (tag `mspm0_sdk_2_11_00_07`), SysConfig 1.28.1, arm-none-eabi-gcc 14.2.1, CMake, Ninja; `MSPM0_SDK_INSTALL_DIR` and `SYSCONFIG_TOOL` preset |
| `docker-image-hpm:main` | HPM SDK v1.13.0, HPM RISC-V GCC 15.2.0, CMake, Ninja; `HPM_SDK_BASE` and `GNURISCV_TOOLCHAIN_PATH` preset |
| `docker-image-ch32-riscv:main` | riscv32-wch-elf-gcc 15.2.0, CMake, WCH OpenOCD |

Typical use — mount the project and run the whole flow inside the image (one-liner from the HPM BSP README, with the version matching the `xrobot:` pin):

```
docker run --rm -v "$PWD:/src" -w /src ghcr.io/xrobot-org/docker-image-hpm:main \
  bash -c 'pip install xrobot==1.0.1 && xrobot setup && cmake --preset debug-flash-xip && cmake --build --preset debug-flash-xip'
```

The `xrobot`/`libxr` steps run in a plain Python container and the vendor-toolchain steps in the official image, both sharing one mounted project directory. Both arrangements work; the images remove the vendor-toolchain installation work.

Docker page: https://xrobot.work/docs/env_setup/env-setup-docker

## Version cross-check

Before the first project command, compare the installed tools with the pins of the project at hand:

- `xrobot --version` against the `xrobot:` line in `Modules/modules.yaml`
- `libxr --version` against the `generator:` line in `User/libxr_config.yaml`

Install the pinned versions when they differ, and hold the line in both directions: an older installed tool is replaced by the pinned release, and the `xrobot:` pin stays as the repository records it. A pre-1.0 project — no `xrobot:` field, legacy owner strings in its module list — keeps the old tool instead with `pip install 'xrobot<1'`; that branch is Fix 2 of the setup entry in references/troubleshooting.md. The First checks section of this skill lists the same two comparisons among its opening checks. Some BSP READMEs print `xrobot==1.0.0 libxr==6.0.0` in their install lines; the YAML pins are the authority.
