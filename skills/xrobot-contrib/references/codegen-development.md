When to read this: extending or modifying the LibXR code generator (repository `LibXR_CppCodeGenerator`, PyPI package `libxr`) — package layout, generated-file boundaries, tests, the new-platform checklist, and release mechanics.

# CodeGenerator development

Facts below reflect tag `v6.0.1` of https://github.com/xrobot-org/LibXR_CppCodeGenerator ; citations name files and symbols rather than line numbers. Re-check them against the tag in use.

## Package layout

`src/libxr/` is a flat module package. Entry points come from `pyproject.toml`: the console script `libxr` maps to `libxr.cli:main`, and `python -m libxr` is equivalent. Nine pre-6.0 console scripts (`xr_parse`, `xr_gen_code`, ...) stay registered through `libxr.legacy`, name the corresponding new subcommand when run, and are scheduled for removal in 7.0.0.

Modules by area:

| Area | Files |
| --- | --- |
| CLI and infrastructure | `cli.py`, `output.py`, `update_notice.py`, `legacy.py`, `cmake_text.py`, `libxr_config_file.py` |
| Platform generators | `generator_code_stm32.py`, `generator_code_mspm0.py`, `generator_code_hpm.py` — all three platforms have one |
| Platform analyzers | `peripheral_analyzer_stm32.py`, `peripheral_analyzer_mspm0.py`, `peripheral_analyzer_hpm.py` — all three platforms have one |
| STM32-specific | `config_cubemx_project.py` (setup), `generator_stm32_cmake.py` (CMake integration), `cubemx_generator.py` (`cubemx-gen`), `stm32_flash_generator.py` (`flash-info`), `stm32_toolchain_switch.py`, `STM32FlashLayoutRules.xml` |
| Pins | `pin_layout.py`, `pin_project.py`, `pin_data/` |
| Generated-code layout | `cpp_layout.py` |

The MSPM0 and HPM generators reuse shared helpers from the STM32 module (`load_configuration`, `load_libxr_config`, `libxr_config_text`, `_write_if_changed`, `_report_files`; the shared-helper definitions in `generator_code_mspm0.py`). The STM32 analyzer defines one `PeripheralParser` subclass per peripheral class; each reads the `.ioc` key=value table, the results are aggregated in a `ConfigurationManager`, and the aggregate is written to the project YAML (the module docstring of `peripheral_analyzer_stm32.py`).

### Pin data

`src/libxr/pin_data/` holds 39 files shipped as package data (`pyproject.toml`, `[tool.setuptools.package-data]`):

- STM32: `stm32.json.gz` (index) plus 31 per-family shards `stm32-<family>.json.gz` (C0 through WL5), loaded on demand to keep startup fast (the on-demand shard loading in `pin_layout.py`).
- MSPM0: `mspm0.json.gz` (derived from TI SysConfig device data) and `mspm0_boards.json` (LaunchPad board definitions).
- HPM: `hpm.json.gz` (derived from the HPM SDK iomux headers and the HPM5300 datasheet).
- License texts: `LICENSE-ST.txt`, `LICENSE-TI.txt`, `LICENSE-TI-BOARDS.txt`, `LICENSE-HPM.txt`.

Regenerate the data with `scripts/build_pin_data.py`, passing the data sources as flags: `--st-data <STM32_open_pin_data checkout>`, `--sysconfig <TI SysConfig installation>`, `--mspm0-sdk <TI MSPM0 SDK checkout>`, and `--hpm-sdk <HPM SDK checkout>` plus `--hpm-datasheet`/`--hpm-series` for HPM. The STM32 source is https://github.com/STMicroelectronics/STM32_open_pin_data .

### How generated code is produced

Generators assemble C++ statements from Python line lists and f-strings. `cpp_layout.py` performs the line breaking itself, following LibXR's `.clang-format` style (Google based, column limit 90, Allman braces; `COLUMN_LIMIT = 90`), so the output depends on the generator alone; the tests compare the generated files against clang-format 21.1.8. `app_main.h` is the constant `APP_MAIN_HEADER` in `generator_code_stm32.py`.

## Platform recognition

`libxr parse` and `libxr gen` dispatch on the project directory (the platform dispatch in `src/libxr/cli.py`). `PLATFORMS` is an ordered tuple; the first matching shape wins:

1. `stm32` — the directory contains an `.ioc` file.
2. `hpm` — the root contains `app.yaml` and a `.hpmpc` under `boards/*/`. A root `.syscfg` alongside them still counts as HPM (the `_has_hpm()` detector in `cli.py`).
3. `mspm0` — the root contains a `.syscfg` file.

An unrecognized directory produces an error listing the three shapes and exits with code 1 (the unrecognized-directory error in `cli.py`). Keep the order when editing `PLATFORMS`: it defines the recognition priority, and the VS Code extension applies the same rules.

## Generated files and hand-edited regions

`libxr stm32 setup` produces ten kinds of files:

| File | Role |
| --- | --- |
| `Middlewares/Third_Party/LibXR/` | LibXR git submodule, checked out at the commit pinned by `src/libxr/libxr_version.py` |
| `.gitignore` | created when missing; ignores build output, `.history`, `.cache`, `CMakeFiles`, `.config.yaml` |
| `.gitattributes` | created when missing, or completed with the standard `text=auto` / eol lines |
| `.config.yaml` | project YAML written by parse (gitignored) |
| `User/app_main.cpp` | entry source with the peripheral objects and `app_main()` |
| `User/app_main.h` | fixed header |
| `User/flash_map.hpp` | STM32 only; flash sector table, removed when it cannot be derived |
| `User/libxr_config.yaml` | generator settings |
| `cmake/LibXR.CMake` | CMake integration |
| `CMakeLists.txt` | gains a single include line for `LibXR.CMake` (the CMakeLists include-line edit in `generator_stm32_cmake.py`) |

`libxr mspm0 setup` and `libxr hpm setup` produce a subset: `.gitignore`, `.config.yaml`, `User/app_main.cpp`, `User/app_main.h`, `User/libxr_config.yaml` (`_setup_without_cubemx` in `cli.py`).

Writing rules:

- Every file is generated in memory first and written only when the whole generation finishes without errors; files whose content is unchanged are skipped, so their mtime stays (the write-if-changed output stage of `generator_code_stm32.py`).
- Regeneration overwrites the generated regions: the generated areas of `app_main.cpp`/`app_main.h`, `flash_map.hpp`, the non-settings blocks of `LibXR.CMake`, and `.config.yaml`.
- Byte stability is part of the contract: output is independent of `PYTHONHASHSEED`, written with LF, and repeats identically on unchanged inputs. A change that moves bytes for an unchanged project blocks the release.
- A branch that parses a configuration and emits no object warns or counts. Silence is a defect in either direction: a configuration that yields neither an object nor a message, and an object the library cannot construct — a UART with TX pins assigned but no TX DMA enabled, an ADC enabled with no regular channel.
- Signals without a LibXR driver are recorded for display instead of emitted: the HPM analyzer sorts UART, SPI, CAN, ACMP and a capture-input GPTMR into `Other` (the `Other` classification in `peripheral_analyzer_hpm.py`).
- A GPTMR comparator produces a PWM object only on a SoC without a dedicated PWM peripheral (the GPTMR-comparator branch in `peripheral_analyzer_hpm.py`); on a PWM SoC the instance stays in `Other` and the duty-or-frequency load moves to the PWM peripheral instance.
- The object-name check in `generator_code_stm32.py` covers C++ keywords and reserved identifiers, the CubeMX macros derived from GPIO labels, CMSIS/HAL macros and IRQ names, and identifiers the generated code already uses. Extend it together with the names the generated code introduces.

Three regions belong to the user and survive regeneration:

1. `/* User Code Begin N */` ... `/* User Code End N */` blocks in `app_main.cpp` (marker expressions in the user-code region handling of `generator_code_stm32.py`). Malformed or unpaired markers abort the run and no file is written. Include/extern lines for driver classes, `FLASH_REGIONS`, or HAL handles used in user code are kept automatically (the user-line preservation logic in `generator_code_stm32.py`).
2. `User/libxr_config.yaml` is loaded with ruamel round-trip: comments, user keys, and modifications survive, and the `generator` key is written once and then preserved (the config load and save handling in `generator_code_stm32.py`).
3. `cmake/LibXR.CMake` has a fixed structure — Project settings, LibXR, Application, Library optimization, Firmware images (the LibXR.CMake section layout in `generator_stm32_cmake.py`). The "Project settings" block is the user-editable area and is preserved on rewrite; user additions and former library-optimization options move into the "Kept from the earlier LibXR.CMake" block (the rewrite-and-preserve logic in `generator_stm32_cmake.py`).

A numeric validation failure aborts the whole generation and names the file, key, and value (the numeric-validation section of the CodeGenerator `README.md`).

## Tests

Run the unittest suite from the repository root (commands as given in the test section of the CodeGenerator `README.md`):

```bash
pip install clang-format==21.1.8
python -m unittest discover -s tests -v
```

The format tests compare generated output against clang-format 21.1.8 and are skipped when that exact version is absent. `tests/fixtures.py` reloads `generator_code_stm32` before each test to clear the module-level registries and settings; `tests/data/` holds sample projects (DevC and MC02 CubeMX projects, MSPM0 and HPM samples). Bilingual docstrings are enforced by `tests/test_docstrings.py`: every module, class, and function in `src/libxr`, `scripts`, and `tests` carries an English plus Chinese docstring.

CI lives in `.github/workflows/python-publish.yml`:

- `lint` pins ruff==0.16.9 and runs `ruff format --check src tests scripts` plus `ruff check src tests scripts` on Python 3.12.
- `libxr-version` runs `scripts/gen_libxr_version.py`, so the tested LibXR commit is the default checkout of the release.
- `release-version` requires the tag (optional `v`/`V` prefix) to equal the `pyproject.toml` version.
- `stm32-target-test` runs the target scripts of an external test-project matrix inside `ghcr.io/xrobot-org/docker-image-stm32:main`.
- `build` installs the wheel on ubuntu/windows × Python 3.10-3.14, runs the suite, and performs a BSP compatibility check (`libxr stm32 setup -d .` in `xrobot-org/bsp_stm32f103`).
- `publish` runs only on a release event, after the jobs above pass, and uploads the single ubuntu/Python 3.12 artifact through Trusted Publishing.

Parser regression method:

- Before adding a branch for vendor keys, enumerate the key shapes that the peripheral's prefix uses across real project files. Each shape gets a branch, or an explicit skip that warns.
- A test copies only the relevant keys of a real example, names that example in a comment, and asserts the whole parsed result. Parser tests assert parsed data; generator tests take project dictionaries.
- A test written for a parser fix fails against the code before the fix.
- Rerun the real-project comparison after any parser change: the difference is empty, or each remaining difference is explained.

## CubeMX automation in CI

`cubemx-gen` drives the vendor GUI through its scripting bridge, so the surrounding environment decides whether a run works.

- Run an OS-native CubeMX installation. A Windows installation mounted into a Linux container lacks the JxBrowser platform libraries for that OS, and the run dies inside the GUI layer instead of reporting a configuration problem.
- CubeMX state and installed firmware packages belong to the Java process's home directory. Pre-warm one archive per operating system and restore it under the exact `user.home` the JVM is started with (`cubemx_generator.py` passes `-Duser.home` from the current home and a preferences root inside it).
- Script-mode `login`, `swmgr install`, and `xcubedl` answer KO on CubeMX 6.17, so CI cannot fill an empty repository. Build on the pre-warmed repository and keep no dependency on an interactive ST login: a login dialog stops the automation.
- Set `ProjectManager.UnderRoot=true`, or pass an explicit code-generation directory. With that key false, generation opens the "Choose Code generation Folder" dialog and waits on it.
- Wait for the Java process to exit before comparing the generated files — the script returns while generation is still running — and compare with `--ignore-cr-at-eol`, because CubeMX writes CRLF while the repository stores LF.

## Adding a platform

Derive the work from the three existing platforms:

1. `src/libxr/peripheral_analyzer_<plat>.py` — implement `parse_project(directory, output)`; this signature is what the CLI depends on (the `parse_project` call sites in `cli.py`).
2. `src/libxr/generator_code_<plat>.py` — implement `generate(input_path, output_path, use_xrobot, libxr_config)`; reuse the STM32 module helpers, with the MSPM0 generator as the reference (the `generate()` implementation in `generator_code_mspm0.py`).
3. `src/libxr/cli.py` — add a `_has_<ext>()` detector, extend the `PLATFORMS` tuple (order sets recognition priority), add `_<plat>_parse`/`_<plat>_gen` (following the existing per-platform parse/gen handlers in `cli.py`), and for a platform without a vendor-GUI step reuse `_setup_without_cubemx` in `cli.py` with `cmd_<plat>_setup` and `_add_<plat>_setup` (following the existing per-platform setup-command pattern in `cli.py`); register the command group in `build_parser` in `cli.py`. `--verbose` is attached automatically by the shared parser setup in `cli.py`.
4. Pin data — extend `scripts/build_pin_data.py` with the platform's data source so it emits `src/libxr/pin_data/<plat>.json.gz` plus a license text; `[tool.setuptools.package-data]` already includes `pin_data/*`.
5. `src/libxr/pin_layout.py` — add `layout_<plat>()` and `recognize_<plat>()`, register them in `RECOGNIZERS` and in the platform table `PLATFORMS` in `pin_layout.py`; add the project-overlay branch for already-selected signals in `src/libxr/pin_project.py`.
6. Tests — `tests/test_generator_code_<plat>.py`, `tests/test_peripheral_analyzer_<plat>.py`, platform cases in `tests/test_cli.py`, and optionally `tests/data/<plat>/` samples. Bilingual docstrings are mandatory (see Tests).
7. VS Code extension (optional, to make the extension support the platform) — extend the `LibxrPlatform` type, `setupAction`, and `cliActions` in `src/libxrView.ts`; add platform branches in `src/pins/model.ts` and `src/pins/project.ts`; extend `watcherPatterns()` with the project-file patterns.

## Python conventions

- ruff: `line-length = 100`, `target-version = "py310"`, lint select `["E","F","I","UP","B","SIM"]`, ignore `["E501"]` (`pyproject.toml`, `[tool.ruff]`). CI pins ruff==0.16.9 on purpose: a newer ruff may format differently.
- User-visible messages go through `tr(english, chinese)` provided by the `xr-syntax==0.2.0` dependency.
- Generated C++ follows LibXR's `.clang-format` (Google, width 90, Allman) via `cpp_layout.py`.

## Release

- The PyPI package name is `libxr`; the version is 6.0.1, aligned with the coordinated release set (LibXR 2.0.1, XRobot 1.0.1, extension 2.0.1).
- The dependency `xr-syntax==0.2.0` is pinned with `==`; coordinated releases keep the same xr-syntax version across both Python packages.
- `pyproject.toml` must already carry the release version when the tag is created; the `release-version` CI job enforces tag and version equality.
- The publish job runs on release events only, after lint, target tests, and the build matrix pass, and uploads through Trusted Publishing.
- The default LibXR checkout commit is locked by `scripts/gen_libxr_version.py`; `check_generator_pin()` warns when the version fixed in `User/libxr_config.yaml` differs from the installed one (`check_generator_pin()` in `generator_code_stm32.py`).

User-facing documentation lives on the site: [Code generation](https://xrobot.work/docs/code_gen) with the per-platform pages [STM32](https://xrobot.work/docs/code_gen/stm32), [MSPM0](https://xrobot.work/docs/code_gen/mspm0), and [HPM](https://xrobot.work/docs/code_gen/hpm), plus [pin layout](https://xrobot.work/docs/code_gen/code-gen-pins) and [XRobot integration](https://xrobot.work/docs/code_gen/code-gen-xrobot-inter).
