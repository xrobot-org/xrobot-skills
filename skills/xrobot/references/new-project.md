When to read this: Creating a firmware or host project on STM32, MSPM0, HPM, CH32, ESP32 or Linux/Webots — from an existing BSP, from a vendor tool project, or from a template.

# Starting a new project

Every project pairs a board (or a host) with the LibXR git submodule and the XRobot module layer. Two CLIs do the generation: `libxr` turns a vendor tool project (CubeMX `.ioc`, TI SysConfig `.syscfg`, HPM Pinmux Tool `.hpmpc`) into C++ entry code, and `xrobot` resolves Modules and generates `User/xrobot_main.hpp`. Install the pinned CLI versions first (references/env-setup.md). Command outputs below are examples; the versions follow the baseline in references/env-setup.md, and `--help` reports the current form. While wiring pins, `libxr pins <model>` prints the package and pin layout of a chip model (STM32, MSPM0, HPM).

## STM32

### Start from a BSP

The flow below runs against https://github.com/xrobot-org/bsp_stm32f103.git (STM32F103RCTx, BluePill):

```
git clone --recursive https://github.com/xrobot-org/bsp_stm32f103.git
cd bsp_stm32f103
pip install xrobot==1.0.1 libxr==6.0.1
xrobot setup
cmake --preset debug
cmake --build --preset debug
```

Example output — setup and build tail:

```
$ xrobot setup
Resolved 1 Module commit
Checked 1 config; generated User/xrobot_main.hpp for User/xrobot.yaml
```

```
[102/103] Linking CXX executable BluePill.elf
Memory region         Used Size  Region Size  %age Used
             RAM:       14680 B        48 KB     29.87%
           FLASH:       89860 B       256 KB     34.28%
...
BluePill.elf built for product: xrobot
```

The `debug` preset uses ST `starm-clang` (STM32CubeCLT). With `arm-none-eabi-gcc` instead, switch before configuring:

```
$ libxr stm32 toolchain gcc
[INFO] Switched the default preset to cmake/gcc-arm-none-eabi.cmake
[INFO] Done.
```

The switch rewrites the `toolchainFile` of the default preset in `CMakePresets.json` and removes `build/` and `cmake-build*`. Multi-config BSPs (for example https://github.com/QDU-Robomaster/bsp-dev-c.git) select the product before building: `xrobot gen -c <config>`, where `<config>` is one of the YAML files under `User/RobotConfig/`; single-config BSPs ship with the selection in place.

### Start from a CubeMX project

Generate a project in STM32CubeMX with the Toolchain / IDE option set to CMake. The generator takes the system layer from the `.ioc`: a FreeRTOS section selects FreeRTOS, a ThreadX section selects ThreadX, and a project with neither is bare metal. One command then adds LibXR (submodule, `.gitignore`/`.gitattributes` entries, parse, generation, CMake integration):

```
libxr stm32 setup -d . --xrobot
```

In bsp_stm32f103, where the committed files match the 6.0.1 output, the same command reports them unchanged:

```
$ libxr stm32 setup -d . --xrobot
[INFO] Found .ioc file: ./STM32F103RC.ioc
...
[INFO] Configuration exported to: ./.config.yaml
[INFO] Generating C++ code...
[INFO] System: FreeRTOS
[INFO] Generated User: unchanged app_main.cpp, app_main.h, flash_map.hpp, libxr_config.yaml
[INFO] LibXR.CMake already included in CMakeLists.txt.
[INFO] [Pass] All tasks completed.
[INFO] Next: run `xrobot gen` to bring User/xrobot_main.hpp up to date; libxr setup does not update it
[INFO] Build: cmake --preset debug && cmake --build --preset debug
```

The two-step equivalent (parse alone also prints the configuration summary):

```
libxr parse -d .
libxr gen -i .config.yaml -d . -o User/app_main.cpp --xrobot
```

`libxr stm32 cmake -d .` performs the CMake integration that the one-step command includes. `-t usart1` (or `-t usb_fs_cdc`) stores `terminal_source` in `User/libxr_config.yaml`. `libxr stm32 cubemx-gen` re-runs STM32CubeMX in script mode from the CLI (`--firmware keep|migrate`, `--download`).

With `--xrobot`, the generated entry registers every hardware object with `XR_REGISTER(name, ...)` and ends in `XROBOT_MAIN()`.

### Add the XRobot layer to a fresh project

In a project without `Modules/modules.yaml`, the `libxr` setup output names the next commands (`xrobot init`, `xrobot module add`, `xrobot setup`, `xrobot instance add`); with `modules.yaml` present it reminds about `xrobot gen`. The full sequence:

```
xrobot init
xrobot module add xrobot-org/BlinkLED@same-or-dev
xrobot setup
xrobot instance add xrobot-org/BlinkLED --id blink_led
xrobot gen
```

`xrobot source search <text>` lists module ids (README example output: `xrobot-org/BMI088 [module] https://github.com/xrobot-org/BMI088.git`). `@same-or-dev` follows the BSP's own branch, falling back to `dev`. `xrobot instance add` creates the instance with default values; single values change with `xrobot instance set <id> <path> <value>`, for example `xrobot instance set blink_led args.blink_cycle 250` (path and quoting rules: https://xrobot.work/docs/proj_man/proj-man-config). Arguments that name hardware reference the `XR_REGISTER` names printed in `User/app_main.cpp`.

The BSP path skips init/module add/instance add: its `Modules/modules.yaml` and configs are committed, so `xrobot setup` alone resolves and generates.

Keep `xrobot gen` after every `libxr` regeneration: libxr leaves `User/xrobot_main.hpp` to xrobot, and both setup outputs end with that reminder. The build re-checks the header and stops with a stale-file message naming `xrobot gen -c User/xrobot.yaml` when a config changed without regeneration.

### Generated files

- `xrobot setup` / `xrobot gen` write `User/xrobot_main.hpp` (header: "Generated by `xrobot gen` from User/xrobot.yaml; do not edit by hand."), `Modules/CMakeLists.txt` and the `Modules/<owner>/<Repo>/` checkouts; `.gitignore` keeps all three out of the repository. `xrobot.lock` records the resolved module commits, is committed, and is maintained by `xrobot setup` (header: "Generated by `xrobot setup`; do not edit by hand.").
- `libxr` writes `.config.yaml` (parse output, gitignored, rewritten on every generation), `User/app_main.cpp`, `User/app_main.h`, `User/flash_map.hpp` and `cmake/LibXR.CMake`. Only the interior of the `/* User Code Begin N */ ... /* User Code End N */` markers in `User/app_main.cpp` is user-owned and survives regeneration; everything else in that file, and `User/app_main.h`, is generated, and a malformed or unpaired marker leaves the whole generation unwritten (concept: the User Code regions section of references/modules.md). Files whose generated content is unchanged keep their timestamp.
- Hand-editable places: the config YAMLs (`User/xrobot.yaml`, other configs under `User/`, `Modules/modules.yaml`), the parameters in `User/libxr_config.yaml` (its `generator:` pin and comments survive regeneration), and application code inside the User Code regions of `User/app_main.cpp`. CubeMX owns everything under `Core/` and `Drivers/`.

## MSPM0

Project shape: one `.syscfg` in the repository root; `User/main.c` calls `SYSCFG_DL_init()` and enters `app_main()`. The flow below runs against `https://github.com/xrobot-org/bsp-mspm0g3507-mini.git`:

```
git clone --recursive https://github.com/xrobot-org/bsp-mspm0g3507-mini.git
cd bsp-mspm0g3507-mini
pip install xrobot==1.0.1 libxr==6.0.1
xrobot setup
export MSPM0_SDK_INSTALL_DIR=<sdk directory>
export SYSCONFIG_TOOL=<sysconfig directory>/sysconfig_cli.sh
libxr mspm0 setup -d . --xrobot
xrobot gen
cmake --preset debug
cmake --build --preset debug
```

`xrobot setup` needs no TI tools. `libxr mspm0 setup -d . --xrobot` needs `SYSCONFIG_TOOL` and `MSPM0_SDK_INSTALL_DIR`, or a SysConfig output left by an earlier build; the failure without them is quoted in references/env-setup.md. Inside `ghcr.io/xrobot-org/docker-image-mspm0:main` the two exports are preset. Example output:

```
$ libxr mspm0 setup -d . --xrobot
[INFO] Processing mspm0g3507_minidb48.syscfg...
[INFO] Running SysConfig on mspm0g3507_minidb48.syscfg
[INFO] Configuration exported to: ./.config.yaml
[INFO] System: bare metal
[INFO] Generated User: unchanged app_main.cpp, app_main.h, libxr_config.yaml
[INFO] Next: run `xrobot gen` to bring User/xrobot_main.hpp up to date; libxr setup does not update it

===== [Configuration Summary] =====

MCU: MSPM0 MSPM0G3507

GPIO (4 pins):
  LED1: PB8, OUTPUT
...
```

Registration names follow the project: GPIO objects take the SysConfig pin labels (`LED1`, `KEY1`); peripheral objects take lowercase instance names (`uart0`). After `xrobot gen`, the CMake configure stage runs SysConfig through `cmake/MSPM0SysConfig.cmake` and fills `build/<preset>/syscfg/` with `ti_msp_dl_config.c/h`, `device_linker.lds` and companions; the build ends:

```
[57/57] Linking CXX executable mspm0_minidb48.elf
mspm0_minidb48.elf built for product: xrobot
```

Products: `build/<preset>/mspm0_minidb48.elf/.hex/.bin/.map`. After editing peripherals, pin names or DMA settings in the `.syscfg`, rerun `libxr mspm0 setup -d . --xrobot`, then `xrobot gen`. A fresh SysConfig project adds the XRobot layer with the init/module add/setup/instance add/gen sequence from the STM32 section.

### Interrupts enabled in SysConfig

A request to enable interrupts in SysConfig is answered with a list derived from the code that consumes them: the peripheral objects generated into `User/app_main.cpp` and their `XR_REGISTER` names, the LibXR drivers behind those objects, and the hand-written code inside the User Code regions — the place an interrupt setup for a key belongs (references/modules.md). Copying a list from an SDK empty example or opening every interrupt produces entries nothing reads.

One line per interrupt, each naming the setting in the `.syscfg`, the consumer, and what the interrupt delivers:

- UART RX: enable the receive interrupt of the UART instance the application reads. The generated object is the lowercase instance (`uart0`), and it fills the receive queue that `LibXR::UART::Read` on `uart0` drains — the terminal reaches it through `terminal_source: uart0` in `User/libxr_config.yaml`.
- Key edge: enable the GPIO port interrupt, and the press arrives as the configured edge on that port. The configuration summary prints the setting, as in `KEY1: PB24, INPUT, FALL interrupt`, and the consumer is the handler written in a User Code region.

The list then runs in both directions against the driver's expectation: every enabled interrupt has a consumer, and every consumer's interrupt appears in the list. A consumer whose interrupt stays off reads until the wait returns `ErrorCode::TIMEOUT`; an entry enabled with no consumer delivers to nothing. The MSPM0 drivers enable their own IRQ sources and set the NVIC priority at runtime, and SysConfig generates a priority only for the interrupts it enables itself — the `.syscfg` carries the enable, the driver carries the priority, and the list states both for each entry.

What to check before handing the list over: `libxr parse -d .` prints the configuration summary the `.syscfg` now yields, `build/<preset>/syscfg/ti_msp_dl_config.c/h` holds the generated enables, and the LibXR view of the VS Code extension shows each peripheral's `.syscfg` settings, interrupts included, beside its `libxr_config.yaml` values (references/vscode-extension.md). An edited `.syscfg` is followed by `libxr mspm0 setup -d . --xrobot` and `xrobot gen`.

### Generated files

- The xrobot-generated files match the STM32 list: `User/xrobot_main.hpp`, `Modules/CMakeLists.txt`, `Modules/<owner>/<Repo>/` (gitignored), `xrobot.lock` (committed, maintained by setup).
- `libxr` writes `.config.yaml`, `User/app_main.cpp` (hand edits go inside the User Code regions, references/modules.md), `User/app_main.h` and `User/libxr_config.yaml`; `flash_map.hpp` and the CMake integration file are STM32-only.
- `build/<preset>/syscfg/` is produced at CMake configure time and stays under `build/`.
- `User/main.c` is a hand-written file (SDK empty-example style) and survives regeneration.

## HPM

Project shape: an HPM SDK application — `app.yaml` in the root, one `.hpmpc` under `boards/<board>/`; the SDK lives outside the project and is reached through `HPM_SDK_BASE` (see references/env-setup.md, or use `ghcr.io/xrobot-org/docker-image-hpm:main` where the variables are preset). The flow below runs against `https://github.com/xrobot-org/bsp-hpm5301evklite.git`:

```
git clone --recursive https://github.com/xrobot-org/bsp-hpm5301evklite.git
cd bsp-hpm5301evklite
pip install xrobot==1.0.1 libxr==6.0.1
xrobot setup
cmake --preset debug-flash-xip
cmake --build --preset debug-flash-xip
```

Presets: `debug-flash-xip`, `debug-ram`, `release-flash-xip`; products `build/<preset>/output/demo.elf` and `demo.bin`. Example build tail:

```
[89/89] Linking CXX executable output/demo.elf
Memory region         Used Size  Region Size  %age Used
           FLASH:      103688 B         1 MB      9.89%
             ILM:        2576 B       128 KB      1.97%
             DLM:        38560 B     130304 B     29.59%
        AHB_SRAM:           0 B        32 KB      0.00%
```

### Regenerating the entry, and the hand-written-file trap

For a fresh Pinmux Tool project, `libxr hpm setup -d . --xrobot` parses the `.hpmpc`, generates `User/app_main.cpp` and `app_main.h`, and creates `User/libxr_config.yaml` with default settings when absent. Example output:

```
$ libxr hpm setup -d . --xrobot
[INFO] Configuration exported to: ./.config.yaml
[INFO] System: bare metal
[INFO] ./User/libxr_config.yaml does not exist; creating it with the default settings
[INFO] Generated User: wrote app_main.cpp, app_main.h, libxr_config.yaml
[INFO] Next: run `xrobot gen` to bring User/xrobot_main.hpp up to date; libxr setup does not update it
```

The trap on bsp-hpm5301evklite: its `User/app_main.cpp` is hand-written by the BSP author and registers `LED`/`KEY` built on the SDK `BOARD_*` macros. Running `libxr hpm setup` overwrites the file with generator output and renames the registrations to the raw `.hpmpc` pin names `pa10`/`pa3`, so the next `xrobot gen` fails:

```
$ xrobot gen
User/xrobot.yaml: blink_led.args.led: LED is neither an XR_REGISTER name nor an earlier instance id; candidates of type LibXR::GPIO&: pa10, pa3
```

The User Code regions survive; the generated object section changes. Recovery:

```
git checkout -- User/app_main.cpp User/app_main.h
xrobot gen
```

After this, `xrobot gen` reports `User/xrobot_main.hpp for User/xrobot.yaml is unchanged`.

Rule: for a project whose `User/app_main.cpp` is hand-maintained, restore the hand-written entry after any `libxr hpm setup` run (or reapply the hand-written registrations), or align the `args` in `User/xrobot.yaml` with the generated register names. For a fresh Pinmux Tool project the generated names are the intended ones: GPIO objects take `.hpmpc` pin names (`pa10`), peripherals take lowercase instance names (`i2c3`), GPTMR outputs become `pwm_gptmr0_ch1`; add the XRobot layer with the init/module add/setup/instance add/gen sequence from the STM32 section. Board files (`tool_config.hpmpc`, `pinmux.c/h`, `clock.c/h`) come from a HPM Pinmux Tool export; the tool validates them on import, so edits go through the tool.

### Generated files

- The xrobot-generated files match the STM32 list.
- `libxr hpm setup` writes `.config.yaml`, `User/app_main.cpp`, `User/app_main.h`, and creates `User/libxr_config.yaml` with defaults when absent. In bsp-hpm5301evklite the two app_main files are hand-maintained — see the trap above.
- The BSP carries no `User/libxr_config.yaml` in the repository; the first `libxr hpm setup` creates it (untracked).

## CH32

https://github.com/xrobot-org/CH32V307_LibXR_Template.git is a plain LibXR application template for CH32V307VC (FreeRTOS): the repository has no `Modules/`, no `User/xrobot.yaml`, and the `xrobot`/`libxr` CLIs have no role in its flow. Build with the template README's own command:

```
git clone --recursive https://github.com/xrobot-org/CH32V307_LibXR_Template.git
cd CH32V307_LibXR_Template
docker run --rm -v "$PWD:/work" -w /work ghcr.io/xrobot-org/docker-image-ch32-riscv:main \
  bash -c 'cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j"$(nproc)"'
```

Locally: WCH RISC-V GCC 15.2+ (`riscv32-wch-elf-` prefix; CMake stops on older versions; `-DCOMPILER_PREFIX=<prefix>` points CMake at a toolchain outside PATH). Products: `build/CH32V307VC.elf/.hex/.bin` (memory table: FLASH 28.66%, RAM 93.89% — the example application, dual USB CDC plus RamFS, sits near the 64 KB RAM limit). Flashing per the template README: WCH-LinkE with WCH's OpenOCD (`openocd -f wch-riscv.cfg`) or VS Code Cortex-Debug; flashing needs hardware.

### Generated files

The template ships hand-written sources only (`User/app_main.cpp` is example code without User Code markers); the LibXR submodule pin fixes the library version; the Python CLIs generate nothing in this flow.

## ESP32

ESP32 projects are ESP-IDF component projects: LibXR enters the build through `cmake/esp32.cmake` in the LibXR checkout, and the project carries hand-written sources because the `libxr` generator covers STM32, MSPM0 and HPM. Project setup, component requirements and build steps: https://xrobot.work/docs/env_setup/env-setup-esp32.

## Linux / Webots

https://github.com/QDU-Robomaster/bsp-linux-autoaim.git builds a host program:

```
git clone https://github.com/QDU-Robomaster/bsp-linux-autoaim.git
cd bsp-linux-autoaim
git submodule update --init --recursive
pip install xrobot==1.0.1
xrobot setup
xrobot gen -c User/xrobot.yaml
cmake --preset release
cmake --build --preset release --target rm_auto_aim
```

Example output:

```
$ xrobot setup
Resolved 15 Module commit
Checked 2 configs; generated User/xrobot_main.hpp for User/xrobot.yaml
```

```
[49/50] Linking CXX executable rm_auto_aim
rm_auto_aim built for product: xrobot
```

Host dependencies: C++20 compiler, CMake 3.21+, Ninja, OpenCV 4 (core/imgproc/dnn/calib3d), Eigen 3, pkg-config, and the libudev development files — configure fails without libudev, with the failure and the fix quoted in references/env-setup.md. Missing `wpa_client`/`libnm` produce warnings and stay non-fatal for this BSP. The detection backends (HailoRT, OpenVINO) and the model files follow the BSP README; the build configures and compiles with both backends absent, and CMake reports `ArmorDetector backends: HailoRT=0 OpenVINO=0`.

`xrobot gen -c <config>` selects the product; the repository carries `User/xrobot.yaml` (infantry/hero) and `User/RunConfig/sentry.yaml`. The binary runs as `build/release/rm_auto_aim`; deployment uses the repository's systemd service script (BSP README; running needs camera hardware and models, both covered there).

Webots: the Docker page lists the webots image (Webots R2025a) among the official images (https://xrobot.work/docs/env_setup/env-setup-docker), and LibXR's system and driver layers include a webots backend (https://xrobot.work/docs/basic_coding/basic-cmake).

### Generated files

- The xrobot-generated files match the STM32 list; the autoaim BSP resolves 15 module commits into `Modules/QDU-Robomaster/` and `Modules/xrobot-org/` checkouts.
- `User/main.cpp` is the hand-written entry (`PlatformInit()`, static objects, `XR_REGISTER` lines, `XROBOT_MAIN()`).
- `User/xrobot.yaml` and `User/RunConfig/*.yaml` are user-editable configs; the platform has no vendor-project generation step.
