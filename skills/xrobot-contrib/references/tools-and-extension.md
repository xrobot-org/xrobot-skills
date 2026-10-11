When to read this: developing the XRobot CLI tool or the XRobot VS Code extension — local runs, tests, the command surface, packaging, and the integration points with CodeGenerator and modules.

# XRobot tool and VS Code extension development

Versions: XRobot `v1.0.1` (https://github.com/xrobot-org/XRobot) and extension `v2.0.1` (https://github.com/xrobot-org/xrobot-vscode-extension, extension id `XRobot.xrobot`). Re-check commands against the tag in use.

## XRobot tool

XRobot is the module manager and main function generator for LibXR: it resolves module requests, checks out each module at a locked commit, and generates `User/xrobot_main.hpp` from the YAML configurations under `User/`. It is published as the PyPI package `xrobot`; the console script `xrobot` maps to `xrobot.cli:run`.

### Local run and tests

Install from source (README installation section):

```bash
git clone https://github.com/xrobot-org/XRobot.git
pip install .
```

Run the unittest suite (README test section):

```bash
python -m unittest discover -s tests -v
```

Python style is held to ruff 0.16.9 alongside the unittest suite; the per-repository verification commands are collected on the contribution guide page ([how to contribute](https://xrobot.work/docs/con_guide/con-guide-how2con)).

### Command surface

Every command acts on the BSP that contains the current directory — the nearest directory at or above it with `Modules/modules.yaml`; `-C DIR` starts the search at `DIR`, and `-c CONFIG` selects a product configuration. Output is bilingual, selected by `XR_LANG`.

| Command | Purpose |
| --- | --- |
| `xrobot init` | create `Modules/modules.yaml`, `Modules/sources.yaml`, `User/xrobot.yaml`, and the `.gitignore`/`.gitattributes` entries |
| `xrobot setup` | resolve Modules, check every config, regenerate `User/xrobot_main.hpp`; flags include `--update`, `--frozen`, `--offline`, `--context-ref`, `--release-ref`, `--leave-local`, `-f`, `--no-line-directives` |
| `xrobot gen` | generate `User/xrobot_main.hpp` for one config and select that config |
| `xrobot describe` | print the BSP state as JSON for editors (drives the extension's XRobot view) |
| `xrobot sync` | add new fields and parameters with defaults, drop removed ones |
| `xrobot format` | rewrite configs in the canonical layout (`--check` reports only) |
| `xrobot instance add / set / remove / rename` | edit one Module instance in a config |
| `xrobot module add / remove / show` | edit the module requests, or print a module's manifest and constructors |
| `xrobot new-module` | create a Module skeleton: header with manifest, `CMakeLists.txt`, README, CI workflow |
| `xrobot check-module` | resolve like setup and write a compile-only constructor probe for module CI |
| `xrobot source list / search / get / find` | query the module sources |
| `xrobot source create-sources / add-source / create-index / add-index` | maintain `sources.yaml` and `index.yaml` |

Run `xrobot <command> --help` for the exact options of each command. User-facing semantics are documented on the site under [Project management](https://xrobot.work/docs/proj_man).

### Branches and PRs

Development PRs target `dev`; `master` receives release merges. Branch conventions are described in [repositories and branches](https://xrobot.work/docs/con_guide/con-guide-branch); release mechanics live in the repository's `RELEASE.md`.

## VS Code extension

The extension (VS Code `^1.108.0`, `extensionKind: ["workspace"]`, TypeScript compiled to `out/extension.js`) contributes an activity-bar container with two views:

- XRobot view — renders the JSON of `xrobot describe` for BSPs containing `Modules/modules.yaml`; every edit runs an `xrobot` command.
- LibXR view — for STM32CubeMX (`.ioc`), MSPM0 (`.syscfg`), and HPM (`app.yaml` + `boards/*/*.hpmpc`) projects; shows `libxr_config.yaml` and the internal flash layout, and runs CodeGenerator commands.

### Commands and settings

`package.json` contributes these commands (grouped; hidden helpers included):

| Group | Commands |
| --- | --- |
| Generic | `xrobot.refreshAll`, `xrobot.collapseAllViews`, `xrobot.runCli` (hidden executor for tree-node actions), `xrobot.openFile`, `xrobot.openUrl`, `xrobot.editYamlScalar` (hidden) |
| LibXR | `xrobot.showPinLayout`, `xrobot.generateLibxrCode`, `xrobot.openVendorTool` (hidden), `xrobot.pickLibxrConfigPath`, `xrobot.pickLibxrAppMainPath` |
| XRobot | `xrobot.selectProduct` (runs `xrobot gen -c`), `xrobot.createModuleWizard` (runs `xrobot new-module`), `xrobot.addModuleInstance` / `xrobot.editModuleInstance` / `xrobot.deleteModuleInstance`, `xrobot.addRepo` / `xrobot.editRepoVersion` / `xrobot.deleteRepo`, `xrobot.addSource` / `xrobot.editSourceUrl` / `xrobot.editSourcePriority` / `xrobot.deleteSource` |
| Scaffold | `xrobot.helloWorld` (kept intentionally, per the repository's `AGENTS.md`) |

Workspace settings cover CLI discovery and LibXR paths: `xrobot.cli.extraPath`, `xrobot.cli.pythonPath`, `xrobot.libxr.iocFile`, `xrobot.libxr.package`, `xrobot.libxr.configPath`, `xrobot.libxr.appMainPath`, `xrobot.libxr.sysconfigTool`, `xrobot.libxr.mspm0SdkDir`; untrusted workspaces ignore the executable-path settings.

The CLI is resolved first as a console script (PATH, the pip user script directory, `xrobot.cli.extraPath`) with a fallback to `python -m libxr` / `python -m xrobot`; the LibXR view requires libxr 6.0.0 or newer. libxr commands run at the workspace root.

The pin layout panel renders the output of `libxr pins -d . -c <configPath> -f json [-p <package>]` (the pin-layout command construction in `src/cli/xrobotCli.ts`, the pin-layout data fetch in `src/pinsService.ts`). The extension itself only draws the result — the comment in `src/providers/pinView.ts` states "The CLI decides what is on the chip; this only draws it." Changes to `*.ioc`, `app.yaml`, `boards/*/*.hpmpc`, `*.syscfg`, `main.c`, `Modules/*.yaml`, `xrobot.lock`, and `User/**` refresh the views (the file-watcher refresh wiring in `src/libxrView.ts`).

### Local development, tests, packaging

Build and test from the repository root:

```bash
npm ci
npm run compile       # tsc -p ./
npm run lint          # eslint src
npm test              # mocha unit tests (out/test/unit)
npm run test:vscode   # extension-host tests
```

`npm run watch` recompiles on save; the launch configuration of type `extensionHost` in `.vscode/launch.json` starts the Extension Development Host for debugging.

Package a `.vsix` locally with:

```bash
npm run package       # vsce package
```

The Release workflow (`.github/workflows/release.yml`) builds the distributable on a `v*` tag push or a manual run with an existing tag: `npm ci` → the tag is checked against the `package.json` version → `npm run compile` → `npm test` → `npx vsce package --out "xrobot-$VERSION.vsix"` → the `## [<version>]` section of `CHANGELOG.md` becomes the release notes (a missing section fails the workflow) → `gh release create "$TAG" "xrobot-$VERSION.vsix" --notes-file notes.md --verify-tag`. The `.vsix` is published as a GitHub Release asset; publishing to the VS Code Marketplace is done manually by the maintainer. The CI workflow (`.github/workflows/ci.yml`) compiles, lints, tests, and packages a `.vsix` artifact on Linux and Windows.

Conventions from the repository's `AGENTS.md` shape the code: the `cli/` adapter layer avoids importing `vscode` so its logic stays unit-testable; processes spawn without a shell and workspace Python code stays unexecuted; every CLI exit code is checked and the CLI's stderr is surfaced; deletions ask for confirmation; the official module source `https://xrobot.work/xrobot-modules/index.yaml` is treated as read-only.

### Integration points

- Extension ↔ CodeGenerator CLI: Generate LibXR Code runs `libxr parse -d <projectDir> -o ./.config.yaml` and then `libxr gen -i ./.config.yaml -o ./User/app_main.cpp [--xrobot] --libxr-config ./User/libxr_config.yaml` (the LibXR code-generation command chain in `src/providers/viewProviders.ts`); setup actions call `libxr stm32 setup -d . [--xrobot]`, `libxr mspm0 setup -d .`, or `libxr hpm setup -d .`. The extension always passes the XRobot flag explicitly, based on whether the workspace is an XRobot BSP, where the CLI alone would keep the current output-file choice (the XRobot-flag decision in `src/libxrView.ts`).
- Extension ↔ XRobot tool: the XRobot view wraps `xrobot` subcommands (`describe`, `gen`, `setup`, `format`, `instance`, `module`, `new-module`, `init`) with a `-C <root>` prefix (the `-C <root>` argument assembly in `src/cli/xrobotCli.ts`) and works from `Modules/modules.yaml`.
- XRobot tool ↔ CodeGenerator: `Modules/modules.yaml` pins the tool version with `xrobot:` and `User/libxr_config.yaml` pins the generator version with `generator:`; BSP CI installs both pinned tools from these fields. `xrobot instance add` points at `terminal_source` / `database.enable` in `libxr_config.yaml` when a RamFS or Database dependency needs a CodeGenerator-generated object, suggesting `libxr stm32 setup -d .` afterwards. In the other direction, CodeGenerator setups that find no `Modules/modules.yaml` suggest `xrobot init`, `xrobot module add`, `xrobot setup`, and `xrobot instance add` (the XRobot-integration section of the CodeGenerator repository's `README.md`).
