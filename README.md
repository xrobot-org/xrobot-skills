# XRobot Skills

XRobot / LibXR 生态的 Agent Skill 集合，供支持 Agent Skill 的编程助手（Claude Code、Codex 及其他读取 `.agents/skills` 目录的工具）使用。仓库包含两个 Skill：

| Skill | 读者 | 用途 |
|---|---|---|
| `xrobot` | 用 XRobot / LibXR 做机器人的开发者 | 搭环境、新建工程、生成代码、管理模块、编译烧录、使用 LibXR 接口、排查问题 |
| `xrobot-contrib` | 向生态提交改动的人 | 分支与发版流程、接口与驱动约定、代码与文档写法、测试与验收、模块与 BSP 开发 |

Agent Skills for the XRobot / LibXR ecosystem, for coding assistants that support the Agent Skills format (Claude Code, Codex, and other tools that read `.agents/skills`). The repository contains two skills: `xrobot` for building robots with XRobot and LibXR, and `xrobot-contrib` for contributing changes to the ecosystem.

## 安装 / Installation

### Claude Code

```bash
claude plugin marketplace add xrobot-org/xrobot-skills
claude plugin install xrobot@xrobot-skills
```

开发者按需安装贡献版：`claude plugin install xrobot-contrib@xrobot-skills`。

Install the contributor skill with `claude plugin install xrobot-contrib@xrobot-skills`.

### Codex 及其他支持 `.agents/skills` 的工具

```bash
git clone https://github.com/xrobot-org/xrobot-skills.git
mkdir -p ~/.agents/skills
cp -r xrobot-skills/skills/xrobot ~/.agents/skills/
```

Windows 下用资源管理器或 `Copy-Item -Recurse` 复制，或建立目录联接（junction）。

On Windows, copy the directory with Explorer or `Copy-Item -Recurse`, or create a junction.

### 手动复制

把 `skills/` 下的目录复制到所用工具的 skill 目录，例如 `~/.claude/skills/`。手动复制安装后，可通过 SKILL.md frontmatter 中的 `version` 字段确认副本版本。

Copy the directories under `skills/` into the skill directory of the tool in use, for example `~/.claude/skills/`. After a manual copy install, confirm the copy's version with the `version` field in the SKILL.md frontmatter.

## 更新 / Update

Claude Code 中运行 `claude plugin marketplace update xrobot-skills`，再运行 `claude plugin update <插件名>`。

其他安装方式：重新执行对应的安装命令。

In Claude Code, run `claude plugin marketplace update xrobot-skills` followed by `claude plugin update <plugin>`. For other installation methods, re-run the corresponding install command.

## 版本对应 / Version Compatibility

Skill 内容基于以下版本：LibXR v2.0.1、XRobot 1.0.1、CodeGenerator（PyPI `libxr`）6.0.1、VS Code 扩展 2.0.1。Skill 会先检查环境的实际版本；版本更新后以 `--help` 输出为准。

The skills are based on: LibXR v2.0.1, XRobot 1.0.1, CodeGenerator (`libxr` on PyPI) 6.0.1, VS Code extension 2.0.1. Each skill checks the installed versions first; after an upgrade, follow the `--help` output.

## 反馈 / Feedback

技能内容本身的问题（步骤、命令形态或排查条目有误、过时）请到 https://github.com/xrobot-org/xrobot-skills/issues 反馈，仓库提供 issue 模板。软件本身的问题如何分流，见技能内的 Help and feedback（`xrobot` SKILL.md 末尾）。快速提问与社区交流请访问 https://xrobot.work/qq。想参与修改本仓库，请先阅读 CONTRIBUTING.md。

For problems with the skill content itself (wrong or outdated steps, command forms, or troubleshooting entries), open an issue at https://github.com/xrobot-org/xrobot-skills/issues; the repository provides an issue template. For how software problems are triaged, see the Help and feedback section at the end of the `xrobot` SKILL.md. For quick questions and community discussion, visit https://xrobot.work/qq. To contribute changes to this repository, start with CONTRIBUTING.md.

## License

[Apache License 2.0](LICENSE)（与 LibXR 一致 / same as LibXR）。
