When to read this: Installing or driving the XRobot VS Code extension — the two views, its commands, the pin layout, or its CLI requirements and troubleshooting.

# VS Code extension

The extension (marketplace id `XRobot.xrobot`, source repository https://github.com/xrobot-org/xrobot-vscode-extension) adds an XRobot activity-bar container with two views:

- XRobot view — the modules, configurations and instances of an XRobot BSP (a folder containing `Modules/modules.yaml`). Its content is the JSON of `xrobot describe` plus `Modules/modules.yaml` and `Modules/sources.yaml`; every edit runs an `xrobot` command.
- LibXR view — STM32CubeMX (`.ioc` at the root), MSPM0 (`.syscfg` at the root) and HPM (`app.yaml` plus `boards/*/*.hpmpc`) projects: the platform, the settings of `User/libxr_config.yaml`, the STM32 internal flash layout from `User/flash_map.hpp`, and the pin layout. It runs `libxr` commands.

Both views refresh on changes to `*.ioc`, `*.syscfg`, `app.yaml`, `boards/*/*.hpmpc`, `main.c`, `Modules/*.yaml`, `xrobot.lock` and `User/**`.

## Installation and requirements

Install "XRobot" from the VS Code Marketplace (https://marketplace.visualstudio.com/items?itemName=XRobot.xrobot), or download the `.vsix` from the repository's GitHub Releases and use "Install from VSIX".

- XRobot view: the `xrobot` CLI (1.0 line; the baseline is 1.0.1, and the project's `xrobot:` pin names the version to install) and `git`.
- LibXR view: the `libxr` CLI (6.0 line; baseline 6.0.1). The pin layout depends entirely on `libxr pins -d . -f json`, so install a libxr release that carries that subcommand — the release pinned by the project (`generator:` in `User/libxr_config.yaml`), e.g. `pipx install libxr==6.0.1`.
- Both CLIs are looked up on `PATH`, in pip's per-user script directories, and in the `xrobot.cli.extraPath` setting. When a console script is absent, the extension falls back to running the Python module with the interpreter from `xrobot.cli.pythonPath`.
- The extension declares `extensionKind: workspace`: under Remote-SSH or in a Dev Container it installs into the workspace and the CLIs run in the remote environment.

## Commands

Command ids and palette titles from `package.json` (extension 2.0.1). The five marked hidden are excluded from the Command Palette and back the views' own buttons and context menus:

| Command id | Palette title | Notes |
| --- | --- | --- |
| `xrobot.helloWorld` | XRobot: Hello World | |
| `xrobot.refreshAll` | XRobot: Refresh All | |
| `xrobot.collapseAllViews` | XRobot: Collapse All Views | |
| `xrobot.showPinLayout` | XRobot: Show Pin Layout | LibXR view title-bar button |
| `xrobot.generateLibxrCode` | XRobot: Generate LibXR Code | play button |
| `xrobot.selectProduct` | XRobot: Select Product (xrobot gen -c) | |
| `xrobot.createModuleWizard` | XRobot: Create Module (xrobot new-module) | |
| `xrobot.addModuleInstance` | XRobot: Add Module Instance | |
| `xrobot.editModuleInstance` | XRobot: Edit Module Instance | |
| `xrobot.deleteModuleInstance` | XRobot: Delete Module Instance | |
| `xrobot.addRepo` | XRobot: Add Module Request | |
| `xrobot.editRepoVersion` | XRobot: Change Module Request Ref | |
| `xrobot.deleteRepo` | XRobot: Remove Module Request | |
| `xrobot.addSource` | XRobot: Add Source | |
| `xrobot.editSourceUrl` | XRobot: Edit Source URL | |
| `xrobot.editSourcePriority` | XRobot: Edit Source Priority | |
| `xrobot.deleteSource` | XRobot: Delete Source | |
| `xrobot.pickLibxrConfigPath` | XRobot: Pick LibXR Config Path | inline edit button |
| `xrobot.pickLibxrAppMainPath` | XRobot: Pick LibXR App Main Path | inline edit button |
| `xrobot.runCli` | XRobot: Run CLI | hidden; generic executor behind tree actions |
| `xrobot.openFile` | XRobot: Open File | hidden |
| `xrobot.openUrl` | XRobot: Open URL | hidden |
| `xrobot.editYamlScalar` | XRobot: Edit YAML Scalar | hidden |
| `xrobot.openVendorTool` | XRobot: Open in Vendor Tool | hidden |

### Commands and the CLIs behind them

| Extension action | CLI work performed |
| --- | --- |
| Generate LibXR Code | `libxr parse -d <projectDir> -o ./.config.yaml`, then `libxr gen -i ./.config.yaml -o ./User/app_main.cpp [--xrobot] --libxr-config ./User/libxr_config.yaml`; the platform (STM32, MSPM0, HPM) is auto-detected |
| Setup action in the LibXR view while `libxr_config.yaml` is absent | `libxr stm32 setup -d . --xrobot`, `libxr mspm0 setup -d . --xrobot` or `libxr hpm setup -d . --xrobot` (or the same with `--no-xrobot`); the extension always passes the XRobot flag explicitly instead of inheriting the previous output's choice |
| STM32 extra actions | `libxr parse`, `libxr gen`, `libxr stm32 flash-info` |
| Show Pin Layout | `libxr pins -d . -c <libxr_config.yaml> -f json [-p <package>]` |
| Select Product | `xrobot gen -c <config>` |
| Add/Edit/Delete Module Instance | `xrobot instance add`, `xrobot instance set`, `xrobot instance remove` (renaming via `xrobot instance rename`) |
| Add/Change/Remove Module Request | `xrobot module add`, a ref change, `xrobot module remove` |
| Add/Edit/Delete Source | `xrobot source` commands editing `Modules/sources.yaml` |
| Create Module | `xrobot new-module` |
| View content and status | `xrobot describe` (refresh); `xrobot setup --frozen`/`--update` and `xrobot format --check` behind view actions |

All `xrobot` invocations carry `-C <workspace root>`.

## Pin layout

"Pin Layout" opens the chip's package drawing. Each refresh runs `libxr pins -d . -c <config> -f json` once (a rerun cancels the previous run and keeps the old drawing until the new result arrives); all chip knowledge lives in the CLI, the extension renders the returned JSON.

- Platform detection matches the CLI: `.ioc` means STM32, `app.yaml` with `boards/*/*.hpmpc` means HPM, `.syscfg` means MSPM0.
- Click a peripheral in the sidebar Peripherals group or a pin in the drawing to select it; panel and sidebar stay in sync, one selection at a time.
- Selected pins are colored by peripheral class and labeled with the pin and function (`PA9 USART1.TX`) or the GPIO label; the dot in the top-left corner marks pin 1.
- Search highlights by pin name, signal or peripheral; Enter walks through the matches. The wheel zooms around the pointer, dragging pans, and a double click restores the full package; the legend filters by category.
- Every recognized peripheral is listed, including ones without a LibXR abstraction (ETH, FMC, OctoSPI, ...). The panel itself is read-only.
- Peripherals selected in the project appear in the sidebar with their pins; each expands to its parameters in `libxr_config.yaml`, editable in place with the code regenerated afterwards.
- MSPM0: the package comes from the SysConfig project (the `--package` of the `.syscfg`, or the LaunchPad its `--board` names); `xrobot.libxr.package` only overrides it. The settings a peripheral carries in `.syscfg` (baud rate, interrupts) show read-only next to its `libxr_config.yaml` values. "Open in SysConfig" starts the standalone SysConfig and needs the `xrobot.libxr.sysconfigTool` and `xrobot.libxr.mspm0SdkDir` settings, or the environment variables `SYSCONFIG_TOOL` and `MSPM0_SDK_INSTALL_DIR`.
- HPM: "Open in HPM Pinmux Tool" opens the `.hpmpc` through HPMicro's `HPMicro.hpm-pinmux-tool` extension and offers to install it or to open the web tool otherwise.

## Common issues

- A view stays empty: the XRobot view needs a workspace with `Modules/modules.yaml`; the LibXR view needs a recognized project at the workspace root. Then check the CLI lookup (next item).
- CLI not found: install `xrobot` and `libxr` as their READMEs describe (pipx keeps console scripts on `PATH`); otherwise add the script directory to `xrobot.cli.extraPath` or set `xrobot.cli.pythonPath` for the `python -m` fallback.
- Generate or pin layout fails on an MSPM0 project: SysConfig is unavailable — set `xrobot.libxr.sysconfigTool` and `xrobot.libxr.mspm0SdkDir`, or build the project once so the SysConfig output under `build*/`, `cmake-build*` or `out` can be reused.
- Pin layout unavailable: the installed libxr lacks `libxr pins` — upgrade, e.g. `pipx install libxr==6.0.1`.
- Opening a pre-1.0 (0.x) BSP: extension 2.0.x targets xrobot 1.0 BSPs. To keep opening a 0.x BSP, install extension 1.0.1 through "Install Specific Version..." in the gear menu of the extension page and turn off "Auto Update" for it.
