---
name: xrobot-contrib
version: 1.0.1
description: Contribute changes to the XRobot/LibXR ecosystem across its public repositories: route each change to the repository that owns it, follow the dev-branch, pull request and release conventions, and apply the coding, Module, BSP, CodeGenerator, extension and documentation practices of each repository. Use when the user prepares or reviews a pull request, asks about branches, releases or Roadmap issues, writes drivers, Modules or BSPs, edits the CodeGenerator, the XRobot CLI or the VS Code extension, or updates website documentation. Trigger phrases (Chinese): 分支 / PR / 发版 / 贡献 / 模块开发 / BSP / 代码风格 / CodeGenerator / VS Code 扩展 / 网站文档 / 新平台驱动
---

# Contributing to the XRobot/LibXR ecosystem

This skill serves contributors preparing code, documentation, or workflow changes for the public XRobot/LibXR repositories: xrobot-org/libxr, xrobot-org/XRobot, xrobot-org/LibXR_CppCodeGenerator, xrobot-org/xr-syntax, xrobot-org/xrobot-vscode-extension, the documentation website (xrobot-org/xrobot-org.github.io), the roadmap repository (xrobot-org/XRobot-Dev-Roadmap), the module catalog, Module repositories, and BSP repositories.

## Version baseline

Baseline: LibXR v2.0.1 / xrobot 1.0.1 / libxr (CodeGenerator) 6.0.1 / VS Code extension 2.0.1.

Check the user's environment before relying on version-specific details:

- `git tag --points-at HEAD` in the relevant clone shows the release tags carried by the checked-out commit. Read a release with this command instead of `git describe --tags` (references/branches-and-releases.md explains the `v1` reference).
- `pip show xrobot` and `pip show libxr` report the installed tool versions; `xrobot --version` and `libxr --version` print the same values.
- The extension version is recorded in its `package.json`.

When the user's versions differ from this baseline, the `--help` output of the installed tools takes precedence: run `xrobot --help`, `libxr --help`, and the `--help` of the specific subcommand before quoting flags or defaults.

## Opening checks

Run these at the start of a task that changes code or reviews a concrete change. A direct answer or a narrow review uses the lightest tier of references/workflow.md and is answered from the references; run the repository-state checks once a repository or a change in it is part of the work.

1. Identify the repository and the branch. Run `git status`, `git log -1`, and `git remote -v`; read the remote URL, the current branch, and any uncommitted work. Leave uncommitted changes in place; do not reset, clean, or stash them.
2. Decide which repository owns the change. Read references/repo-map.md. A change spanning several repositories becomes one pull request per repository, linked through a shared Roadmap issue.
3. Confirm the base branch. Development pull requests target `dev`; `master` receives only release merges. Read references/branches-and-releases.md before opening any pull request.
4. Confirm the environment provides the tools and permissions the step at hand needs. When something is missing for a step that has to run, name the exact action that fills the gap — the command to install or the permission to request — and stop there.

## Workflow

Work runs through five stages — design discussion, implementation, verification, review, and delivery. Each stage does only its own work; see references/workflow.md for the stage gates, work tiers, contract fields, ablation checks, reset rules, and handoff procedure.

## Decision routing

| Task at hand | Read |
| --- | --- |
| Planning or working through a change (stages, records, ablation, resets) | references/workflow.md |
| Deciding which repository owns a change | references/repo-map.md |
| Branch, PR, merge, or release questions | references/branches-and-releases.md |
| Flash a board, including one whose BSP is unknown (read IDCODE/UID through the probe to identify the chip first) | references/testing-and-acceptance.md, section "On-board acceptance" |
| Race conditions, ISR/thread handoff, or `FULL`/`EMPTY` behavior | references/coding-conventions.md, section "Interrupt and thread rules" |
| Changing a public interface or core behavior | references/public-interface-checklist.md |
| Writing code, drivers, or style fixes | references/coding-conventions.md |
| Testing and acceptance evidence | references/testing-and-acceptance.md |
| Writing a Module | references/module-development.md |
| Writing or changing a BSP | references/bsp-development.md |
| Changing the CodeGenerator | references/codegen-development.md |
| Changing the XRobot tool or the VS Code extension | references/tools-and-extension.md |
| Changing website documentation | references/website-docs.md |
| A finding outside the task scope | references/common-mistakes.md |
| A stuck PR or an unexpected failure | references/common-mistakes.md |

## References

| File | Purpose |
| --- | --- |
| repo-map.md | What each repository owns and where a given change belongs. |
| workflow.md | Stage gates, work tiers, task contracts, ablation checks, reset rules, and handoff. |
| branches-and-releases.md | Branch model, PR conventions, CI context rules, and the coordinated release procedure. |
| public-interface-checklist.md | Baseline-versus-changed behavior comparison for public API and core semantics. |
| coding-conventions.md | C++, CMake, and Python style plus formatting and repository hygiene. |
| testing-and-acceptance.md | Test entry points per repository and what counts as acceptance evidence. |
| module-development.md | Module manifest, constructor interface, README, and module CI. |
| bsp-development.md | BSP layout, generated-file boundaries, tool pins, and BSP CI. |
| codegen-development.md | CodeGenerator architecture, platform additions, and test suite. |
| tools-and-extension.md | XRobot CLI internals and the extension's command surface. |
| website-docs.md | Website repository layout, bilingual rules, and local build. |
| common-mistakes.md | Recurring failure patterns and how to recover from them. |

## Before opening a pull request

- The change sits in the repository that owns it (references/repo-map.md).
- The base branch is `dev` (references/branches-and-releases.md).
- The description links the Roadmap issue through `Part of xrobot-org/XRobot-Dev-Roadmap#N` or `Closes xrobot-org/XRobot-Dev-Roadmap#N` (references/branches-and-releases.md).
- Every behavior change is declared in the description (references/public-interface-checklist.md).

## Feedback

Problems in the skill content itself — a wrong or outdated step, command shape, workflow rule, or reference document — go to the skill repository: https://github.com/xrobot-org/xrobot-skills/issues. Quick questions and community help: the page at https://xrobot.work/qq.
