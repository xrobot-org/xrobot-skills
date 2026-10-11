# Contributing

This repository contains the Agent Skills for the XRobot / LibXR ecosystem: `xrobot` for developers building robots with the ecosystem, and `xrobot-contrib` for developers contributing changes to it. The skills are versioned together with the ecosystem release set: LibXR, XRobot, CodeGenerator (`libxr` on PyPI) and the VS Code extension release as a set, and the tag of this repository tracks that set.

## Reporting a problem

Errors in skill content - a wrong statement, an outdated command, a missing step - are reported with the "Skill content problem" issue template at https://github.com/xrobot-org/xrobot-skills/issues. Fill in:

- the skill, and the file and section heading concerned;
- what the skill says, quoted from the original text;
- what is actually the case, with the complete command output;
- the versions in use: the output of `xrobot --version` and `libxr --version`, and the platform.

Questions and community help go to https://xrobot.work/qq instead of the issue tracker.

## Changing the skills

Skill text lives in `skills/xrobot/SKILL.md`, `skills/xrobot-contrib/SKILL.md`, and the `references/` directory beside each. The writing conventions:

- Write in English, in the third person, restrained and factual.
- Present command output as an example, never as pasted real-machine output.
- Keep the Chinese trigger phrases in the frontmatter `description`; the body stays English.
- Do not introduce private information: no drive-letter paths, home directories, addresses or credentials. `scripts/check_private.py` scans the repository for the generic patterns.

## Before submitting

Run both checks from the repository root:

```bash
python scripts/check_private.py
python scripts/check_consistency.py
```

`check_consistency.py` requires the same version in `.claude-plugin/marketplace.json`, in the first release heading of `CHANGELOG.md`, and in the `version` field of both SKILL.md frontmatter blocks.

## Versioning

Content changes are recorded in the `Unreleased` section of `CHANGELOG.md` as they are made. When the ecosystem publishes the next release set, the pending entries move under the new `X.Y.Z` heading, and the version is set in `marketplace.json` and both SKILL.md frontmatter blocks in the same change.
