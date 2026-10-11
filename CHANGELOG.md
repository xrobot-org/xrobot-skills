# Changelog

All notable changes to the skills in this repository are documented here.
The skill repository is versioned together with the XRobot ecosystem releases:
LibXR, XRobot, CodeGenerator (`libxr` on PyPI) and the VS Code extension release
as a set, and the tag of this repository tracks that set.

## Unreleased

- Both skills: the Help and feedback sections route skill-content problems to the xrobot-skills repository, name the community page at xrobot.work/qq, and carry a `version` field in the SKILL.md frontmatter for manually copied installs.
- `xrobot`: troubleshooting.md opens with a symptom index table mapping each entry by user-visible keywords; the Still unresolved section lists the same skill-repository routing.
- `xrobot`: env-setup.md gains a Windows section (pipx, native vendor toolchains, `sysconfig_cli.bat`, POSIX-shell examples); modules.md states the trust obligation for module sources behind a Source.
- `xrobot-contrib`: repo-map.md covers this repository; codegen-development.md and tools-and-extension.md replace line-number citations with file-and-symbol citations.
- Repository: CONTRIBUTING.md, a skill-content issue template with a community contact link, and `scripts/check_consistency.py` (marketplace.json / CHANGELOG / SKILL.md frontmatter version agreement) plus a GitHub Actions workflow running it together with `check_private.py`; a root `.gitattributes` (`* text=auto`) keeps LF line endings across platforms.

## 1.0.1 - 2026-10-11

- `xrobot-contrib`: new `references/workflow.md` - the working stages (design, implementation, verification, review, delivery), work tiers, task contract, design records, ablation checks, reset rules, verification budget, review independence, handoff and baseline discipline.
- `xrobot-contrib`: public-interface checklist requires maintainer agreement before implementation and makes a changed interface fail loudly for old call sites; testing reference adds ablation experiment design and on-board conclusion discipline.
- `xrobot`: troubleshooting grows to 26 symptom entries (serial console silent, PWM frequency mismatch, DAC initial value, watchdog resets, timer rollover, single-slot queue, CRC table race, ISP and BSL flashing, platform errata); a complete interrupt-to-thread handoff example and the SysConfig interrupt checklist guidance are added.
- Both skills: command outputs are presented as examples, the released-version-only rule is stated, and the repository owner reference points to the documentation site's about page.
- Both skills: the decision routing tables gain entries for flashing a board whose chip or BSP is unknown and for concurrency, ISR and `FULL`/`EMPTY` questions; the version baseline is stated as a baseline line.
- `xrobot`: container reference lists the remaining `src/structure/` containers, uses the `SLOT_` state names of `SlotPool` and states the `LatestSnapshot` single-writer and lock-free atomic requirements; `XR_REGISTER(name, ...)` is written in its variadic form; ESP32 sections reduce to the website link; the troubleshooting entries for CAN, USB CDC, watchdog and HPM ISP state their conditions as operating rules, and the CAN entry covers `GetErrorState` and `Register`.
- `xrobot-contrib`: release procedure states the `v1` movement rule, the merge-commit rule, the firmware release files and the marketplace id; coding conventions list the HPM driver set of LibXR v2.0.1 and cross-link the HPM platform contracts; workflow and testing references use positive statements.
- `.claude-plugin/marketplace.json` version follows the release set (1.0.1).

## 1.0.0 - 2026-10-11

- Initial release.
- `xrobot`: end-user skill for XRobot / LibXR - environment setup, project
  creation per platform (STM32, MSPM0, HPM, CH32, ESP32, Linux), code
  generation, module management, VS Code extension, build/flash/debug, LibXR
  usage (Topics, Events, RamFS, Database, Logger, containers, power
  management), and a troubleshooting guide.
- `xrobot-contrib`: contributor skill covering the repository map, branch/PR/
  release workflow, public-interface checklist, coding conventions, testing
  and acceptance, module development, BSP development, CodeGenerator and VS
  Code extension development, and website documentation.
