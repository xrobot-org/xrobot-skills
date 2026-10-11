When to read this: Read this file first to decide which repository a change belongs to and how the repositories depend on each other.

A concrete picture ties the map together: a board project such as bsp_stm32f103 contains a CubeMX project that the CodeGenerator turns into `User/app_main.cpp`, a `Modules/modules.yaml` through which XRobot pulls the BlinkLED Module and locks its commit, a LibXR submodule that provides the drivers, and a README that points at the website docs. Each piece lives in a different repository; the table below says which.

## Repository map

| Repository | Owns | Entry point — send changes here when the change touches |
| --- | --- | --- |
| [xrobot-org/libxr](https://github.com/xrobot-org/libxr) | The C++20 embedded framework: core (`src/core`), middleware, data structures, system layers (`system/`), platform drivers (`driver/st`, `ch`, `esp`, `hpm`, `mspm0`, `linux`, `webots`, `webasm`), the XRUSB stack, in-repository tests and Doxygen docs. | Library APIs, platform drivers, system layers, CMake options, framework tests or in-repository documentation. |
| [xrobot-org/LibXR_CppCodeGenerator](https://github.com/xrobot-org/LibXR_CppCodeGenerator) | The pip package `libxr` (command `libxr`): parses CubeMX `.ioc`, SysConfig `.syscfg`, and HPM Pinmux projects; generates `User/app_main.*`, `User/libxr_config.yaml`, `flash_map.hpp`, and the LibXR CMake integration; ships pin-layout data. | Parsing, code generation, pin data, the `libxr` CLI, or the generator's tests. |
| [xrobot-org/XRobot](https://github.com/xrobot-org/XRobot) | The pip package `xrobot`: module requests and locking (`Modules/modules.yaml`, `Modules/sources.yaml`, `xrobot.lock`, same-or-dev resolution), configuration parsing, `XRobotMain` generation; the shared CI workflows `module-ci.yml` and `bsp-stm32-ci.yml` that Module and BSP repositories reference as `@v1`; `RELEASE.md` and `tools/check_release.py`. | The `xrobot` CLI, lock or generation logic, the shared workflows, or the release procedure documents. |
| [xrobot-org/xr-syntax](https://github.com/xrobot-org/xr-syntax) | The C++ parser published on PyPI as `xr-syntax`, shared by both Python packages. | C++ parsing behavior used by `xrobot` and `libxr`. |
| [xrobot-org/xrobot-vscode-extension](https://github.com/xrobot-org/xrobot-vscode-extension) | The VS Code extension `XRobot.xrobot`: an XRobot view that drives the `xrobot` CLI and a LibXR view that drives the `libxr` CLI (code generation, pin layout); the Release workflow publishes a `.vsix` to GitHub Releases. | Extension UI, commands, or the CLI adapter layer. |
| [xrobot-org/xrobot-org.github.io](https://github.com/xrobot-org/xrobot-org.github.io) | The documentation website deployed to [xrobot.work](https://xrobot.work/): Docusaurus sources in `docs/` (Chinese) mirrored in `i18n/en/` (English); a push to `master` deploys the site. | Documentation pages, tutorials, or reference material. |
| [xrobot-org/XRobot-Dev-Roadmap](https://github.com/xrobot-org/XRobot-Dev-Roadmap) | Cross-repository roadmap and task tracking through GitHub Issues. | Filing or discussing cross-repository work items that pull requests then reference. |
| [xrobot-org/xrobot-modules](https://github.com/xrobot-org/xrobot-modules) | The official module Source: publishes the module index that BSP `Modules/sources.yaml` files point to (`https://xrobot.work/xrobot-modules/index.yaml`); merging `dev` into `master` redeploys it. | Adding or updating index entries for Modules or BSPs. |
| Module repositories, for example [xrobot-org/BlinkLED](https://github.com/xrobot-org/BlinkLED) and [xrobot-org/BMI088](https://github.com/xrobot-org/BMI088) | One Git repository per Module: a main header holding the `MODULE MANIFEST V2` block, the public constructor as the interface, `CMakeLists.txt`, a README, and CI that calls `module-ci.yml@v1`. | A Module's code, manifest, README, or CI wiring. |
| BSP and template repositories, for example [xrobot-org/bsp_stm32f103](https://github.com/xrobot-org/bsp_stm32f103), [xrobot-org/bsp-mspm0g3507-mini](https://github.com/xrobot-org/bsp-mspm0g3507-mini), [xrobot-org/CH32V307_LibXR_Template](https://github.com/xrobot-org/CH32V307_LibXR_Template), [QDU-Robomaster/bsp-dev-c](https://github.com/QDU-Robomaster/bsp-dev-c) | BSPs: LibXR as a git submodule, `Modules/modules.yaml` plus `Modules/sources.yaml` plus `xrobot.lock`, `User/` configurations, vendor project files, and CI wiring. | A board's configuration, User Code areas, module requests, or CI wiring. |
| [xrobot-org/xrobot-skills](https://github.com/xrobot-org/xrobot-skills) | This repository: the two Agent Skills (the end-user skill `xrobot` and the contributor skill `xrobot-contrib`), versioned together with the ecosystem release set. | The guidance itself — a wrong or outdated step, command shape, troubleshooting entry, workflow rule, or reference document. |

The website's contribution guide ([how to contribute](https://xrobot.work/docs/con_guide/con-guide-how2con)) carries the same repository routing from the contributor's point of view.

## How the repositories depend on each other

- LibXR sits at the base. Each BSP includes it as a git submodule (`Middlewares/Third_Party/LibXR` in CubeMX-based BSPs, `libxr/` in the others), so a LibXR change reaches end users when BSPs bump the submodule during a release.
- The CodeGenerator is distributed through PyPI as `libxr`; each BSP pins the generator version in `User/libxr_config.yaml` (`generator:`). Its publish workflow records the LibXR `master` commit of that moment as the default checkout, so CodeGenerator releases follow LibXR releases.
- XRobot and the CodeGenerator both pin the same `xr-syntax` version exactly, so xr-syntax releases first whenever its version changes.
- Module repositories are discovered through the index published by the module Source repository; a BSP lists its Sources in `Modules/sources.yaml` and records the resolved commits in `xrobot.lock`. Requests written as `@same-or-dev` follow the BSP's branch context.
- The extension drives the two CLIs (`xrobot`, `libxr`) and parses no C++ itself; a CLI behavior change usually requires a matching extension update.
- The website documents the whole flow, and the API reference ([xrobot.work/libxr/](https://xrobot.work/libxr/)) is generated from LibXR.

Dependency direction: LibXR ← tools (XRobot, CodeGenerator) ← Modules ← BSPs; the extension and the website build on top.

## Ownership

Reviewer and ownership questions are answered on the documentation site's about page (https://xrobot.work/docs/about). The repositories do not carry `CODEOWNERS` files; do not infer maintainers from git history or issue threads.
