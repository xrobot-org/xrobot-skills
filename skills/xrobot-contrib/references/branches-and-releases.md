When to read this: Read this file before opening a pull request, when a pull request is ready to merge, or when preparing or checking a coordinated release.

## Branch model

- Every repository in the ecosystem develops on `dev`. Development pull requests target `dev`, and hotfixes land there first.
- `master` receives only pull requests from `dev` — the release merges.
- Do not force-push shared branches (`dev`, `master`). Rewriting their history strands other contributors' clones and can move module commits out from under locks that downstream BSPs hold.
- Pull requests from `dev` into `master` and Module pull requests are merged with a merge commit. `RELEASE.md` in the XRobot repository documents the mechanism for the release merge: after the merge commit, `dev` is fast-forwarded to `master` so both branches point at the same commit. Squash and rebase merges create commits on `master` that `dev` does not have; they break the fast-forward and can leave Module commits locked in BSP `xrobot.lock` files off the release line. When that happens, the `--frozen --release-ref` gate reports an error and prints the refresh command, for example `xrobot setup --update <Module> --context-ref refs/heads/dev`.
- In the XRobot repository, a `source-is-dev` workflow reports pull requests into `master` whose source is not the same repository's `dev` branch.

## Pull request conventions

- Link the Roadmap issue in the description: `Part of xrobot-org/XRobot-Dev-Roadmap#N` while the work continues across releases, or `Closes xrobot-org/XRobot-Dev-Roadmap#N` when the pull request completes the issue.
- `Closes` takes effect when a pull request merges into the default branch (`master`). Development pull requests merge into `dev`, so Roadmap issues close at the release merge into `master`, not when the `dev` pull request lands.
- Cross-repository issues live in the XRobot-Dev-Roadmap repository; a concern specific to the library stays in the libxr repository's own issues. Roadmap issue titles start with a component prefix such as `[LibXR]`, `[XRobot]`, `[CodeGenerator]`, or `[Modules]`.
- Org members can see which release an issue belongs to in the organization Project's `Release` field; if the board is not visible to you, ask the maintainer in the issue.

## Versions and tags

- LibXR, XRobot (PyPI `xrobot`), and LibXR_CppCodeGenerator (PyPI `libxr`) carry independent version numbers and release together. A coordinated release bumps the last digit on each line, for example LibXR 2.0.2 / xrobot 1.0.2 / CodeGenerator 6.0.2. The VS Code extension follows the same flow on its own 2.0.x line.
- Both Python packages pin the same `xr-syntax` version exactly (`xr-syntax==X`); when that version changes, xr-syntax is released first.
- Every new tag is a lowercase `v` plus the version (`v2.0.2`), LibXR Releases included; historical uppercase `V` tags remain as they are.

## Repository moves and redirects

- After a repository transfer, do not create a new repository under the old owner and name. The new repository takes the name, and the transfer redirect that old clone URLs and documentation links resolve through stops working.
- GitHub Pages and GHCR packages do not follow a transfer. The site is redeployed from the new repository and serves at its new address; a container package stays in the original owner's namespace until it is migrated on purpose. Documentation points at the address that serves the content.
- Before deleting or renaming a branch, search for links that point into it: repository documentation, project templates, workflows in other repositories, onboarding repositories. A branch absent from the repository's own text is not evidence that nothing references it.

## CI context rules

Module CI — `module-ci.yml@v1` in the XRobot repository, called by each Module's `build.yml`:

- The context branch is the pull request's target branch, `master` for tag pushes, and the current branch for every other event (feature-branch, `dev`, or `master` pushes, manual dispatch, schedules).
- The `xrobot-ref` and `libxr-ref` inputs override when set; left empty they resolve to the context branch and fall back to `dev` when the repository has no branch of that name (same-or-dev semantics). `dependency-ref` defaults to `refs/heads/<context branch>`; the `xrobot` tool resolves same-or-dev for dependency Modules while resolving the lock.

STM32 BSP CI — `bsp-stm32-ci.yml@v1`:

- The check job installs the pinned tools recorded in `Modules/modules.yaml` (`xrobot:`) and `User/libxr_config.yaml` (`generator:`), regenerates the generated files and compares them with the committed ones, checks line endings, runs `xrobot format --check`, and runs `xrobot setup --frozen --context-ref ... --release-ref ...`.
- The release job runs when a Release is published, a `v*` tag is pushed, or `master` (or `main`) receives a push. A push to `master` tags the next patch version — the highest `vX.Y.Z` tag plus one, `v1.0.0` first; a commit that already carries a `v` tag is published by that tag's own run — and publishes the firmware (`elf`/`hex`/`bin` per configuration, the configuration copy `<project>-<config>-<tag>.yaml`, the reproducible `<project>-<config>-<tag>.tar.gz`, `SHA256SUMS`, `firmware-manifest.json`).
- MSPM0, HPM, CH32 template, and Linux BSP repositories run their own build workflows that compile and check but contain no firmware release job; firmware publishing exists only through the shared STM32 workflow. Some of these repositories add a daily canary build against LibXR `master`.

## Coordinated release procedure

Before publishing, candidate commits are chosen on each repository's `dev` line and checked in this order: `automatic` (LibXR automatic tests), `backends` (platform backend compile matrix), `packages` (both Python packages and the code they generate), `modules` (official Module compile matrix), `docs` (website build), `bsp` (official BSPs regenerated and built with the candidates). BSP hardware testing is arranged by each BSP's maintainers.

`tools/check_release.py` in the XRobot repository compares an acceptance record against the candidate checkouts:

```sh
python tools/check_release.py --libxr ../libxr --xrobot . --codegen ../LibXR_CppCodeGenerator --record release-acceptance.json
```

The check passes only when every checkout is clean and at the recorded commit, each package's `pyproject.toml` version equals the recorded version, both packages pin the recorded `xr-syntax` version, and all six checks are `pass`. The tool only compares; building, tagging, and publishing follow the steps below.

Release order — each step finds what it depends on already in place:

1. LibXR: run the "Build Docs Image" workflow once on `master` and make the GHCR `libxr-docs` package public (the API documentation deployment pulls this image); merge the `dev` into `master` pull request; create the GitHub Release on the merge commit with the tag `v` plus the version.
2. Publish xr-syntax when its version changed.
3. CodeGenerator and XRobot: merge `dev` into `master`; create the GitHub Release with the tag `v` plus the version; the publish workflow builds the package and uploads it to PyPI. A push or pull request runs the checks and the build only; the upload runs on the `release` event, after the tag is compared with the `pyproject.toml` version. The tag only marks the commit, so `pyproject.toml` must already carry the released version. The CodeGenerator publish workflow writes the LibXR `master` commit of that moment as its default checkout, so this step follows the LibXR merge.
4. XRobot advances the `v1` reference — the tag through which Module and BSP repositories call the shared workflows — onto the same commit the XRobot version tag of this release points at, the `dev` into `master` merge commit of step 3. Every 1.x.y release, patch releases included, moves `v1`. A change to a shared workflow that breaks existing callers is cut as `v2`, and the callers move to that name. A caller that needs a reproducible workflow references `@v1.x.y` or a commit sha. Run these in the XRobot repository with that release's own version tag (`v1.0.2` for the release after 1.0.1):
   ```sh
   git tag -f v1 'v1.0.2^{commit}'   # the XRobot version tag created in step 3
   git push -f origin v1
   ```
   The force-push concerns the tag ref only; `dev` and `master` keep their history (Branch model above). The release commit carries two tags, so `git describe --tags` on it returns `v1`; read the version with `git tag --points-at HEAD`.
5. Modules: on `dev`, switch CI to `module-ci.yml@v1` and drop the `xrobot-ref`, `libxr-ref`, and `dependency-ref` inputs that point at `dev`; merge `dev` into `master`. The module Sources (catalogs) merge into `master` afterwards and are redeployed.
6. BSPs: on `dev`, update the LibXR submodule to the commit merged in step 1, switch CI to `bsp-stm32-ci.yml@v1`, resolve `xrobot.lock` again against the Modules' `master` branches, then merge `dev` into `master`. An STM32 BSP's push to `master` receives the next patch tag and publishes firmware; when the merge commit already carries a `v` tag, that tag publishes it. Template repositories update their LibXR submodule the same way.
7. The website merges `dev` into `master`; the push deploys it (the `github-pages` environment must allow `master`). The extension merges `dev` into `master`, pushes the tag `v` plus the version matching `package.json`, and the Release workflow packages the `.vsix` and creates the GitHub Release; the marketplace id is `XRobot.xrobot`.
