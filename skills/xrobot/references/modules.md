When to read this: Editing `Modules/modules.yaml`, `Modules/sources.yaml`, `xrobot.lock` or `User/xrobot.yaml`, or running `xrobot setup` / `xrobot gen`.

# Modules, sources and generation

XRobot resolves module repositories, checks each one out at a locked commit, and generates the construction of module instances into `User/xrobot_main.hpp`. Four files carry this:

| File | Role | Edited by |
| --- | --- | --- |
| `Modules/modules.yaml` | which modules to request, at which refs, and the pinned `xrobot` tool version | hand, or `xrobot module add/remove` |
| `Modules/sources.yaml` | which module indexes to consult | hand, or `xrobot source add-source` |
| `xrobot.lock` | the resolved commit of every module | `xrobot setup` only |
| `User/xrobot.yaml` | the module instances to construct and their arguments | hand, or the `xrobot instance` commands |

`xrobot init` creates the skeleton files in a new BSP (`-C DIR` names the directory). Every command acts on the BSP that contains the current directory: the nearest directory at or above it holding `Modules/modules.yaml`. The project-management documentation at https://xrobot.work/docs/proj_man explains the underlying concepts; this page collects the file formats and the resolution and generation workflow.

## modules.yaml

The [bsp_stm32f103](https://github.com/xrobot-org/bsp_stm32f103) file (complete):

```yaml
xrobot: 1.0.1
modules:
- xrobot-org/BlinkLED@same-or-dev
```

[bsp-dev-c](https://github.com/QDU-Robomaster/bsp-dev-c) requests its RoboMaster modules the same way (excerpt):

```yaml
xrobot: 1.0.1
modules:
- QDU-Robomaster/CMD@same-or-dev
- QDU-Robomaster/Chassis@same-or-dev
- QDU-Robomaster/DMMotor@same-or-dev
- QDU-Robomaster/DR16@same-or-dev
// ...
```

(excerpt.)

- The only top-level keys are `xrobot` and `modules`.
- `xrobot:` pins the XRobot tool version — a release number or a 40-digit commit. Install the pinned release (`pipx install xrobot==1.0.1` for the current pin); `xrobot --version` prints the installed one.
- Each entry is one request: a string `owner/Repo@ref`, or a mapping with `id`, `ref` and `context_ref`. The ref may be a branch, a tag, a commit (7–40 hex digits), `refs/heads/...`, `refs/tags/...`, `same` or `same-or-dev`; without a ref, the repository's default branch is used.
- `xrobot module add QDU-Robomaster/DR16` appends a request and writes `@same-or-dev` when no ref is given; `xrobot module remove` deletes one.

### The same-or-dev semantics

`same` and `same-or-dev` follow the BSP's context ref: the branch given with `--context-ref`, or the BSP's current Git branch.

- `same` checks out the branch or tag whose name matches the context; when the repository has none, resolution stops with an error.
- `same-or-dev` tries the same-name branch or tag first and falls back to `refs/heads/dev`. It reports an error when the context is a tag and the repository has no branch or tag of that name, when the context name is `dev` (name an explicit ref instead), or when the repository has no `dev` branch.
- The context travels down the dependency chain: `same`, `same-or-dev` and explicit tag/commit requests pass the initial context to the next level, while a plain branch request makes its resolved branch the context of the next level.

This is what makes stacked module development work: while a module sits on a feature branch, its `@same-or-dev` dependencies resolve onto branches of the same name, and they fall back to `dev` once those branches are merged and deleted.

## sources.yaml and the public indexes

`sources.yaml` lists module indexes (`index.yaml` URLs); for a package, the entry with the lowest `priority` number wins. The template written by `xrobot init` and `xrobot source create-sources`:

```yaml
sources:
  - url: https://xrobot.work/xrobot-modules/index.yaml
    priority: 0
```

BSPs that also use QDU-Robomaster modules carry both indexes ([bsp-dev-c](https://github.com/QDU-Robomaster/bsp-dev-c), complete file):

```yaml
sources:
- url: https://xrobot.work/xrobot-modules/index.yaml
  priority: 0
- url: https://qdu-robomaster.github.io/qdu-future-modules/index.yaml
  priority: 0
```

`xrobot source add-source <url>` appends an index. Two same-priority sources listing the same package id with different repositories stop resolution until the priorities differ; mirror sources only provide clone addresses and stay out of the priority choice.

Sources are trusted input: any Git repository an index lists is cloned by `xrobot setup` and compiled into the firmware. Confirm a third-party source's publisher and contents before adding it. The ambiguity stop above keeps a package from silently moving to another repository, and `xrobot.lock` pins the commit that resolution produced.

### Finding modules

- The official xrobot-org index is published at https://xrobot.work/xrobot-modules/index.yaml; QDU-Robomaster publishes its RoboMaster index at https://qdu-robomaster.github.io/qdu-future-modules/index.yaml. Both are plain `index.yaml` files listing Git repositories, read through the configured sources.
- Search by text (case-insensitive):

```text
$ xrobot source search BMI
xrobot-org/BMI088 [module] https://github.com/xrobot-org/BMI088.git
```

- Package ids are `owner/Repo` (`xrobot-org/BMI088`, `QDU-Robomaster/Chassis`). A bare `Repo` resolves only while unique across the active sources; ambiguous ids report the candidates. `xrobot source list` lists packages, `xrobot source get <id>` prints one entry, `xrobot source find <id>` lists every source providing it.
- `xrobot module show <owner/Repo>` prints a locked module's manifest and constructor declarations.

## xrobot.lock

`xrobot setup` writes `xrobot.lock` with the resolved identity of every module and checks the repositories out at those commits under `Modules/<owner>/<Repo>/` (detached HEAD). From bsp_stm32f103 (complete file):

```yaml
# Generated by `xrobot setup`; do not edit by hand.
version: 1
requests:
- id: xrobot-org/BlinkLED
  ref: same-or-dev
modules:
  xrobot-org/BlinkLED:
    repo: https://github.com/xrobot-org/BlinkLED.git
    source: https://xrobot.work/xrobot-modules/index.yaml
    requested: same-or-dev
    resolved_ref: master
    ref_kind: branch
    commit: 0ca1620261fea84a3a391ff219199b7bef4d9a1e
```

The lock is the single source of module state: checkouts outside it (old caches, manual clones) are ignored, every listed module must sit at its locked commit, and each resolution re-verifies the dependency closure against the modules' manifests. Commit the lock with the BSP — CI runs `xrobot setup --frozen` against it.

## xrobot setup

`xrobot setup` resolves and checks out the modules, checks every configuration under `User/`, and regenerates `User/xrobot_main.hpp` for the selected config.

| Option | Behavior |
| --- | --- |
| `--update [MODULE...]` | Re-resolve the named modules (all when none is named) and sync every config; the way to move modules to newer commits. Modules with unpushed local commits are refused. |
| `--frozen` | Check out exactly `xrobot.lock`. Requests that differ from the lock are an error, the lock stays untouched, and the installed XRobot must match the `xrobot:` pin. |
| `--offline` | Work without network access: use the checkouts already in `Modules/`. Requires a `xrobot.lock` consistent with `modules.yaml`. |
| `--context-ref REF` | Resolve `same`/`same-or-dev` against `REF` (a full `refs/heads/...` or `refs/tags/...`) instead of the BSP's current branch. Required when the BSP is not a Git checkout or is in detached HEAD. |
| `--release-ref REF` | Release gate: refuse commits outside the target release line (the dev line for `dev`, the master line for `master`/`main`/tags). Mainly used by CI. |
| `--leave-local MODULE...` | Move the named modules to their resolved commits while keeping unpushed local commits on the original branch or in the reflog (printed first). Uncommitted changes are refused without `-f`, which discards them for the named modules. |
| `--no-line-directives` | Write the generated header without `#line` directives. |

`--update` and `--frozen` are mutually exclusive, and argument parsing rejects the combination. `--update` with `--offline` passes argument parsing and raises an error when the command runs.

### When --frozen fails

`xrobot setup --frozen` reports an error instead of resolving, and leaves the lock untouched, when:

1. combined with `--update` or `--offline`;
2. `xrobot.lock` is missing (run `xrobot setup` without `--frozen` once);
3. the requests in `Modules/modules.yaml` differ from the lock's records (order- and case-insensitive; the error lists additions, removals and changes);
4. the installed XRobot version differs from the `xrobot:` pin, or no pin is present;
5. resolving would change `xrobot.lock`;
6. the lock format is outdated (a version other than `1`, removed entry fields, or a commit that is not a 40-digit hash) — rerun `xrobot setup --update` to regenerate it.

## xrobot gen and User/xrobot.yaml

Every `*.yaml` under `User/` except `libxr_config.yaml` is an application config; the entry source file is the only `User/` source that calls `XROBOT_MAIN()`. From bsp_stm32f103 (complete file):

```yaml
modules:
  - module: xrobot-org/BlinkLED
    id: blink_led
    args:
      - led: LED
      - blink_cycle: 250
settings:
  monitor_sleep_ms: 1000
```

An IMU instance from [bsp-dev-c](https://github.com/QDU-Robomaster/bsp-dev-c) shows the value forms (excerpt):

```yaml
  - module: xrobot-org/BMI088
    id: bmi088
    args:
      - spi: spi1
      - database: database
      - param:
          gyro_freq: BMI088::GyroFreq::GYRO_1000HZ_BW116HZ
          rotation: '{0.707, 0.0, 0.0, 0.707}'
          gyro_topic_name: "bmi088_gyro"
// ...
```

(excerpt.) Hardware names such as `LED` and `spi1` come from `XR_REGISTER` calls in the BSP's entry source, and earlier instance ids can be referenced the same way. A hardware name in `args` is available once the peripheral is enabled in the vendor project and registered by the `libxr ... setup --xrobot` run; a missing name is the case described in the troubleshooting entry "Generation reports errors around XR_REGISTER" (references/troubleshooting.md).

- An entry keys `module` (`owner/Repo`), `id` (a unique C++ identifier), `args` (an ordered list following the constructor: dependency parameters first, then configuration parameters with defaults), and optionally `template_args`.
- Values: unquoted or single-quoted text is C++ code written as-is; double-quoted text is a C++ string literal; empty means unfilled, and generation reports the dependency candidates. YAML anchors, aliases and tags are rejected.
- `settings.monitor_sleep_ms` is the sleep between monitor rounds. `constexprs` (with `constexpr_namespace` and `constexpr_includes`) define typed C++ constants that `args` can reference.
- Prefer the editing commands: `xrobot instance add <owner/Repo>` writes an instance filled from the constructor defaults (dependency arguments stay unfilled, with the candidates printed; the default id is the lowercase module name plus `_<n>`, counting from 0, and `--id` sets another), `xrobot instance set ID PATH VALUE` replaces one value, `xrobot sync` adds and removes parameters after a module interface change, `xrobot format [--check]` normalizes the layout.
- BSPs with several products keep one config per file — for example a debug-oriented config with a minimal instance set next to a full-featured one (bsp-dev-c: `User/RobotConfig/hero.yaml`, `sentry.yaml`, ...). `xrobot gen -c <config>` selects a config and generates for it; without `-c`, the selected config (recorded in the header) or `User/xrobot.yaml` is used.

### What gen writes

`xrobot gen` (also run by `xrobot setup`) reads the selected config, collects `XR_REGISTER(name, ...)` registrations from the entry source, and writes `User/xrobot_main.hpp`: module includes, one `static <Type> <id>(...)` per instance in config order, `[[noreturn]] static inline void XRobotMain(...)` taking the registered hardware names, and a monitor loop calling each instance's `OnMonitor()` followed by `LibXR::Thread::Sleep(monitor_sleep_ms)`. `#line` directives map compiler errors back to the YAML lines.

The header records its inputs and a digest; LibXR's CMake recomputes it during the build and stops with a stale-header message when a config, the entry source, or a module changed without regenerating:

```text
<bsp>/User/xrobot_main.hpp is stale: ...
Run `xrobot gen -c User/xrobot.yaml` in <bsp> before building.
```

### The split between xrobot and libxr generation

`libxr ... setup` and `libxr gen` write the platform layer — `User/app_main.cpp`, `User/app_main.h`, STM32's `User/flash_map.hpp`, `User/libxr_config.yaml`, and the CMake integration — and leave `User/xrobot_main.hpp` to XRobot. Among these, `User/app_main.cpp` is the generated file with a hand-editable interior, the User Code regions described below; `User/libxr_config.yaml` carries user parameters and keeps them across regeneration. After regenerating the platform layer, run `xrobot gen`; the libxr tools print the reminder themselves:

```text
[INFO] Next: run `xrobot gen` to bring User/xrobot_main.hpp up to date; libxr setup does not update it
```

The reverse direction exists too: when an instance argument should come from a CodeGenerator-generated object (RamFS, Database), `xrobot instance add` reports the missing candidate and asks to set `terminal_source` or `database.enable: true` in `User/libxr_config.yaml` and rerun `libxr stm32 setup -d .`.

### User Code regions

Inside the platform layer, the hand-editable place is the interior of the User Code regions. `libxr gen` writes `User/app_main.cpp` with three marker pairs:

```c
/* User Code Begin 1 */
/* ... user code ... */
/* User Code End 1 */
```

The body between `Begin N` and its matching `End N` belongs to the user: regeneration copies those bodies back into the freshly generated file. Interrupt setup for a key, an extra `XR_REGISTER`, and application code in general go there — the third region runs before the generated module entry. Code inside a region that uses a driver class, the flash region macros, or a HAL handle pulls the matching include and `extern` declaration into the generated file.

Everything outside the markers, and `User/app_main.h`, is generated content: their headers read "Generated by `libxr gen`; do not edit by hand.", and an edit there is replaced by the next run.

A marker that is malformed, renamed, duplicated, unpaired, missing, or placed inside a preprocessor conditional would silently drop the code around it, so generation refuses the file and writes nothing:

```text
existing User Code markers cannot be preserved safely; nothing was written. Fix the markers and regenerate:
  User Code Begin 2 has no matching End marker
```

`XROBOT_MAIN()` is emitted after the third region. A hand-written `XROBOT_MAIN()` call or a loop that never returns inside a region therefore leaves the firmware running with no module executing — the generator clears its own default endless loop when a region holds exactly that loop, and nothing else.

## Writing a new module

To create a module, scaffold with `xrobot new-module NAME`. The full process is described in the module-development reference of the `xrobot-contrib` skill (repository https://github.com/xrobot-org/xrobot-skills) and in the project-management documentation at https://xrobot.work/docs/proj_man/proj-man-create-mod.
