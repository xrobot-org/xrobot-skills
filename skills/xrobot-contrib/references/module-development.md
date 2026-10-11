When to read this: Writing, documenting, testing, or publishing an XRobot Module repository.

# Module development

A Module is an ordinary C++ class in its own Git repository. XRobot resolves the repository, checks it out at a locked commit, and generates the construction of module instances into the BSP's `User/xrobot_main.hpp`. The public constructor is the module's interface: XRobot reads it from the header together with a manifest comment block, and the BSP configuration supplies the arguments.

[BlinkLED](https://github.com/xrobot-org/BlinkLED) runs through this page as the minimal example. Its repository contains five files:

```text
BlinkLED.hpp                 module header: manifest block, class, constructor
CMakeLists.txt               adds the include path and sources to the xr target
README.md                    bilingual documentation in numbered sections
LICENSE                      Apache-2.0
.github/workflows/build.yml  one job that calls the shared module CI
```

`xrobot new-module` scaffolds the same layout and leaves the license to the author.

## The CMakeLists.txt

A module integrates through the `xr` target that the XRobot tooling wires into the build. BlinkLED's complete `CMakeLists.txt` (13 lines):

```cmake
# CMakeLists.txt for BlinkLED

# Add module to include path
target_include_directories(xr PUBLIC ${CMAKE_CURRENT_LIST_DIR})

# Auto-include source files
file(GLOB MODULE_BLINKLED_SRC
    "${CMAKE_CURRENT_LIST_DIR}/*.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/*.c"
)

target_sources(xr PRIVATE ${MODULE_BLINKLED_SRC})
```

(excerpt: complete file.) The `CMakeLists.txt` that `xrobot new-module` generates follows the same pattern and adds `CONFIGURE_DEPENDS` to the source glob; use the generated file as the baseline for new modules.

## The manifest block

The module header opens with a manifest comment block wrapped in `// clang-format off` / `// clang-format on`. BlinkLED's header (excerpt from `BlinkLED.hpp`):

```cpp
// clang-format off
/* === MODULE MANIFEST V2 ===
module_description: LED 周期闪烁与致命错误指示模块 / Module that blinks an LED periodically and indicates fatal errors
depends: []
=== END MANIFEST === */
// clang-format on

#include <memory>

#include "gpio.hpp"
// ...
```

(excerpt.)

The manifest has three keys; XRobot 1.0.1 reads MANIFEST V2 blocks only:

- `module_description` — one line describing the module. The established convention is Chinese and English on a single line, separated by ` / `.
- `depends` — a list of Module requests, written exactly like the entries of a BSP's `Modules/modules.yaml`: `owner/Repo@ref`, or a mapping `{id, ref, context_ref}`. A module that only uses LibXR declares `depends: []`, as BlinkLED does. A module that builds on other modules lists them:

  ```yaml
  depends:
    - QDU-Robomaster/CMD
    - id: QDU-Robomaster/Motor
      ref: same-or-dev
  ```

- `standalone` — optional, default `true`. `standalone: false` marks a source-only library module: instances are not created from it, and the CI probe compiles a single `#include` of the header. `Motor`, `CameraBase`, `VisionPreview` and `DurationStatistics` are library modules in this sense.

The parser reports an error for pre-1.0 keys (`module_name`, `constructor_args`, `template_args`, `required_hardware`), for unknown keys, for a `depends` value that is not a list, and for a second manifest block. Everything else the configuration needs is read from the C++ declarations themselves: constructor parameters, template parameters and their defaults come from the source, and the manifest leaves them out. `xrobot module show <owner>/<Repo>` prints the parsed manifest and the constructor declaration for verification.

## The constructor is the interface

Constructor parameters come in two groups in a fixed order: dependency parameters first, then configuration parameters with defaults.

BlinkLED's constructor (excerpt from `BlinkLED.hpp`):

```cpp
BlinkLED(
    LibXR::GPIO& led,
    uint32_t blink_cycle = 250)
```

(excerpt.)

- `LibXR::GPIO& led` is a dependency: an object the BSP provides through its `XR_REGISTER` registrations. Dependencies take no defaults.
- `uint32_t blink_cycle = 250` is a configuration parameter with a source default. `xrobot instance add` and `xrobot sync` copy these defaults into the BSP configuration.

CanIMU shows the full pattern: four dependencies followed by one aggregate configuration parameter (excerpt from `CanIMU.hpp`):

```cpp
explicit CanIMU(LibXR::CAN& can_bus, LibXR::UART& uart, LibXR::Database& database,
                LibXR::RamFS& ramfs,
                const Param& param = {.accl_topic = "imu_accl",
                                      .gyro_topic = "imu_gyro",
                                      .quat_topic = "imu_quat",
                                      .eulr_topic = "imu_eulr",
                                      .task_stack_depth_uart = 1536,
                                      .task_stack_depth_can = 1536})
```

(excerpt; the `Param` struct declares exactly the six fields shown.)

Rules the generator applies to parameters:

- A bare name in the configuration (`led: LED`) names a registered object; the generator takes its address for reference and pointer parameters. A quoted value `'&name'` passes the address as written. An unused optional dependency is written `nullptr` in the configuration.
- Required objects are declared as references; optional objects as pointers.
- Template parameters are declared separately (`--template` in `xrobot new-module`) and supplied per instance as `template_args`.
- A module may offer several compliant constructors; the configuration selects one of them. The generated code constructs every instance as a function-local `static` object in `XRobotMain`, in configuration order.

Scaffold a new module with:

```bash
xrobot new-module MySensor \
    --desc "Reads a sensor over I2C / Reads a sensor over I2C" \
    --constructor "MySensor(LibXR::I2C& i2c, uint32_t rate = 400)"
```

The command creates `MySensor.hpp` (manifest plus constructor), `CMakeLists.txt`, `README.md` and `.github/workflows/build.yml`. It auto-includes `libxr.hpp` and the LibXR driver headers used by the declaration (`i2c.hpp` among them); `--include` adds more headers, `--depends owner/Repo` appends manifest dependencies (a missing ref is recorded as `@same-or-dev`), and `--template-arg` produces the JSON for the CI's `template-args`. When validation fails, the command creates no files.

## Topics are constructor parameters

Topic dependencies are declared through ordinary constructor parameters; the manifest has no Topic key. Two shapes appear in the sample modules.

SharedTopicClient takes a list of Topic configurations (excerpt from `SharedTopicClient.hpp`):

```cpp
struct TopicConfig
{
  const char* name;                         ///< Topic 名称 Topic name
  const char* domain = "libxr_def_domain";  ///< Topic 所在的 domain Domain of the Topic
  // ...
};

SharedTopicClient(LibXR::UART& uart, uint32_t slot_count = 16,
                  std::initializer_list<TopicConfig> topic_configs =
                      {"topic1", {"topic2", "libxr_def_domain"}})
```

(excerpt.) In the BSP configuration, an initializer list is written as one single-quoted C++ text value (excerpt from the SharedTopicClient README):

```yaml
modules:
  - module: xrobot-org/SharedTopicClient
    id: shared_topic_client
    args:
      - uart: usb_otg_hs_cdc
      - slot_count: 16
      - topic_configs: '{"ahrs_quaternion"}'
```

CanIMU instead names its Topics through string fields of the `Param` struct (excerpt from `CanIMU.hpp`):

```cpp
struct Param
{
  const char* accl_topic;  ///< 订阅的加速度 Topic 名称
  ///< Name of the subscribed acceleration Topic
  // ...
};
```

(excerpt; `Param` also carries the gyro, quaternion and Euler Topic names and two stack depths.)

Both shapes amount to the same contract: the constructor looks the Topics up by name and subscribes. Topics must exist before the subscribing instance is constructed. The configuration satisfies this through ordering: instances that create the Topics are listed above the subscribing instance in `modules:`, and Topics created by the BSP itself are created in the entry source before `XROBOT_MAIN()`. SharedTopicClient documents the requirement in its README: a Topic that is not found is logged as `Topic not found` and enters the LibXR fatal error handler.

Document every Topic in the README's Topic section as a table with direction, payload type and default name. CanIMU's table (excerpt from the CanIMU README; the quaternion and Euler rows follow the same pattern):

| Topic | Direction | Type | Meaning |
| --- | --- | --- | --- |
| `accl_topic` (default `imu_accl`) | Subscribe | `Eigen::Matrix<float, 3, 1>` | Acceleration in g |
| `gyro_topic` (default `imu_gyro`) | Subscribe | `Eigen::Matrix<float, 3, 1>` | Angular velocity in rad/s |

## README

Module READMEs follow the five numbered sections that `xrobot new-module` generates; BlinkLED's README is the reference shape:

1. 模块作用 / Purpose — what the module does after construction, in one Chinese and one English paragraph.
2. 构造接口 / Constructor — the constructor signature, then the dependency and configuration parameters grouped and explained.
3. Topic — the Topic table from the previous section; "无 / None" when the module uses no Topics.
4. 配置示例 / Configuration Example — the instance YAML written by `xrobot instance add`.
5. 依赖与硬件 / Dependencies and Hardware — the dependency list (LibXR plus other modules) and the hardware the BSP must provide and register.

A module that defines a wire or file format inserts that section between Purpose and Constructor; CanIMU documents its UART and CAN frame layouts there (six sections in total).

BlinkLED's configuration section shows the instance with `led` filled from the BSP's registration (excerpt from the BlinkLED README):

```yaml
modules:
  - module: xrobot-org/BlinkLED
    id: blink_led
    args:
      - led: LED_B
      - blink_cycle: 250
```

(excerpt.)

## CI

Each module repository carries the same short workflow. `.github/workflows/build.yml` is identical in BlinkLED, SharedTopicClient and CanIMU, and `xrobot new-module` generates the same text:

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

(excerpt: complete file.)

No ref inputs are passed, so the shared workflow `module-ci.yml@v1` resolves everything from the event context:

- Context branch: a pull request uses its target branch; a tag push uses `master`; every other event (branch pushes, `workflow_dispatch`, `schedule`) uses the current branch.
- The XRobot tool, LibXR and every dependency resolve to that context, falling back to `dev` when the repository has no branch of that name. A PR against a module branch therefore builds that module against the LibXR and XRobot branches of the same name.
- Probe: the workflow runs `xrobot check-module`, which resolves the module like `setup` and writes `module_check.cpp` — a `XRobotCompileCheck()` function that is compiled and not executed, with dependency parameters as `void*` placeholders. Library modules (`standalone: false`) compile a single `#include` instead.
- Build: a C++20 CMake configure-and-build against the LibXR Linux backend in `ghcr.io/xrobot-org/docker-image-linux:main`. The default build type `RelWithDebInfo` compiles with `-O2 -g` and `-DLIBXR_DEBUG_BUILD=ON`, so assertions stay active. An optional `ctest` stage is controlled by `ctest-regex` and `ctest-timeout` (default 15 seconds).
- Remaining inputs: `xrobot-ref`, `libxr-ref` and `dependency-ref` (explicit overrides used during migrations; remove them before the release merge into master), `template-args` (a JSON list; when omitted, the remaining template parameters must have defaults), `sources` (additional index URLs, listed after the official index), `apt-packages`, `cmake-options` and `image`.

Release rhythm: PRs target `dev`, and official modules keep `dev` and `master` with the release merge into master. Both branches build in CI under the context rules above. The three reference modules carry no version tags; `@same-or-dev` requests track the branch pair, and explicit tags remain valid refs for modules that want an independent release cadence.

## Publishing to the module index

Consumers discover modules through index files ("sources"). A BSP's `Modules/sources.yaml` lists them with priorities. `xrobot init` writes a plain template without comments; committed BSP files add a comment above each entry, as in this excerpt from `bsp_stm32f103/Modules/sources.yaml`:

```yaml
# XRobot sources.yaml template. List your module repository index.yaml files, supports official and custom mirrors.
# Official example (already filled in by default):
sources:
  - url: https://xrobot.work/xrobot-modules/index.yaml
    priority: 0
```

Requests name a module as `owner/Repo@ref`. The ref may be a branch, a tag, a 7–40 digit commit, a full `refs/...` path, `same`, or `same-or-dev`; an omitted ref means the repository's default branch. `same-or-dev` resolves to the branch (or tag) named like the current context — the BSP branch `xrobot setup` runs on, or the tag being released — and falls back to `dev` when the module repository has no branch of that name. With a tag as context, the same-named branch or tag is required and resolution reports an error when it is missing. The context propagates down the dependency chain: `same`, `same-or-dev`, tag and commit requests keep the original context, while an explicit branch request becomes the context for its own subtree.

An index is an `index.yaml` with `modules:` and `bsps:` lists. Entries are plain Git URLs or mappings with the fields `id` (derived as owner/repo from a GitHub URL when omitted), `type` (`module` or `bsp`), `repo`, and the status metadata `status`, `tested_ref` and `tested_libxr`. `status` is `community` by default; `verified` and `official` require `tested_ref` and `tested_libxr`. BSP entries carry repository-discovery metadata only. The package identity is the canonical `owner/Repo`; a fork under another owner is a distinct package, and a short name (`BlinkLED` without owner) resolves only when exactly one candidate exists across the active sources.

Publish a module by listing its repository in an index:

- Own index: `xrobot source create-index` writes a local `index.yaml`, and `xrobot source add-index <repo-url> --index <file>` appends the module repository. Host the file (GitHub Pages works) and point consumers at it with `xrobot source add-source <url> --priority N`; lower priority numbers win.
- Existing index: the xrobot-org official index and the QDU-Robomaster module index (`https://qdu-robomaster.github.io/qdu-future-modules/index.yaml`) are the public ones; listing a module there is arranged with the index operators.

`xrobot source list`, `source search`, `source get` and `source find` inspect the active sources from a BSP.

## Static assembly: obligations for module authors

XRobot's generation model constructs the application statically, and the module interface carries the corresponding obligations:

- Instances are constructed in `XRobotMain` as function-local `static` objects, in the order of `modules:` in the configuration. Initialization belongs in the constructor; periodic work belongs in `OnMonitor()`, which the generated monitor loop calls followed by `LibXR::Thread::Sleep(monitor_sleep_ms)`. Keep `OnMonitor()` returning `void`: when the generator cannot confirm the return type, it emits a `static_assert` that fails the build.
- Bindings are compile-time. The generated header passes registered objects by reference; there is no runtime registry, and every name in the configuration is checked at generation time against the module's constructor and the BSP's `XR_REGISTER` registrations.
- The generator reads `XR_REGISTER(name, ...)` syntactically, one name with one type, before preprocessing. Registrations inside `#if`/`#ifdef` blocks or macros produce bindings that mismatch the compiled code, so registrations stay unconditional. This mostly concerns BSP entry sources, and module READMEs that reference registered names point to the registration.
- The configuration can define typed constants (`constexprs`); module arguments may reference them.
- The lock belongs to the application: `xrobot.lock` records the resolved commit of every module in a BSP, and module repositories carry no lock. `xrobot setup` resolves the requested modules together with their dependencies, and `xrobot setup --update <Module>` re-resolves named modules.

## Tool version pinning and module selection

A BSP fixes the XRobot tool in the first line of `Modules/modules.yaml`:

```yaml
xrobot: 1.0.1
modules:
- xrobot-org/BlinkLED@same-or-dev
```

(excerpt from `bsp_stm32f103/Modules/modules.yaml`.)

The pin names the manager version that performs module selection. BSP CI installs exactly that version, and `xrobot setup --frozen` stops with an error when the installed version differs from the pin or the pin is missing. The pin fixes the tool; which modules are used, and at which commits, is decided by the request list, the refs, and the resolution recorded in `xrobot.lock`.

For a module author this means:

- `@same-or-dev` ties resolution to the consumer's branch: a BSP on `dev` consumes the module's `dev`, and a BSP on `master` or on a release tag consumes `master` (a tag requires a same-named module tag). Keep both branches building; the module CI applies the same context rules on every push and PR.
- Tool releases (LibXR, xrobot, CodeGenerator) roll together, and modules follow their own branch line; compatibility is enforced by the module CI and by the BSPs' locked rebuilds.
- When a BSP updates its `xrobot:` pin, module selection changes only through re-resolution (`xrobot setup --update`), which refreshes `xrobot.lock`.

Project documentation: [Module creation](https://xrobot.work/docs/proj_man/proj-man-create-mod), [Sources and registries](https://xrobot.work/docs/proj_man/proj-man-source-man), [Setup and resolution](https://xrobot.work/docs/proj_man/proj-man-setup), [CI](https://xrobot.work/docs/proj_man/proj-man-ci), [Generated main](https://xrobot.work/docs/proj_man/proj-man-gen-main).
