When to read this: writing or reviewing documentation pages for the XRobot documentation site (xrobot.work) — repository layout, URL rules, bilingual workflow, style rules, local build, and the PR checklist.

# Website documentation

The site is a Docusaurus project in https://github.com/xrobot-org/xrobot-org.github.io , deployed at https://xrobot.work/ .

## Site layout

- Chinese is the default locale: source pages live in `docs/` and their URLs carry no language prefix. English versions live in `i18n/en/docusaurus-plugin-content-docs/current/`, mirroring the `docs/` tree file by file, and are served under `/en/docs/...`. A documentation change updates both locations.
- The docs plugin publishes 151 pages. Site pages outside the docs (`/`, `/qq`) and the static entries `/XRobot-Onboarding/` and `/libxr/` live in `src/pages/` and `static/`.
- `trailingSlash` is disabled and `onBrokenLinks` is configured to throw: a broken internal link fails the build.

Top-level documentation sections: `intro` / `quick_start` / `concept` / `about` (portals), `env_setup`, `basic_coding` (LibXR usage), `code_gen` (CodeGenerator), `proj_man` (XRobot), `adv_coding`, `xrusb`, `debug`, `perf`, and `con_guide` (contribution guides).

## URL derivation — the common mistake

A leaf page's URL is built from the parent directory path plus the frontmatter `id`, not from the file name:

- `README.md` in each directory is that directory's index page and maps to `/docs/<directory path>`.
- Any other `.md` maps to `/docs/<parent directory path>/<frontmatter id>`.
- One page overrides this with an explicit `slug:` — `docs/basic_coding/middleware/message/overview.md` declares `slug: /basic_coding/middleware/message`.

Real example: `docs/xrusb/id.md` declares `id: xrusb-id`, so the published URL is https://xrobot.work/docs/xrusb/xrusb-id — a link written as `/docs/xrusb/id` returns 404. Two more pages under the same rule: `core-cb.md` → https://xrobot.work/docs/basic_coding/core/core-callback and `perf-dap.md` → https://xrobot.work/docs/perf/perf-daplink .

Take link targets from the published pages (for example from the site's sitemap) instead of constructing them from file names, and re-verify every existing link when moving or renaming pages. In-page `/docs/...` absolute links are resolved by Docusaurus at build time; a failed resolution stops the build.

## Writing rules

The normative style guide is the [documentation style](https://xrobot.work/docs/con_guide/con-guide-doc-style) page of the contribution guide. The rules that carry the most weight while drafting:

- Keep a neutral, third-person register; reserve imperative step text for tutorials and keep introductory text declarative.
- Describe what a thing is and does. Skip identity negations ("it is not a ...") and corner-case warnings nobody asked about.
- Describe actual behavior instead of giving absolute guarantees: prefer "setup stops and explains the reason when a module has uncommitted changes" over "never discards local work".
- One page covers one project. Usage of another project is linked, not restated — XRobot pages link to the CodeGenerator installation pages instead of repeating them.
- Introduce concepts through one concrete scenario (one board, one IMU, one LED) with a small "concept → what it is in this scenario" table; introduce each term where first needed. Keep the fixed vocabulary: Module, Source, BSP, Configuration, Instance, Registration, Entry source, XRobotMain, lock.
- Keep the document type honest: repository READMEs introduce, website tutorials step through from zero, website references hold the complete rules; README text stays short and links to the site for options and rules.
- Bilingual layout: Chinese paragraphs first, English paragraphs after, each language flowing on its own; no sentence-by-sentence mechanical pairing; the content stays identical in both languages.
- Command output comes from real runs, with machine-specific paths replaced by `<BSP>` or relative paths; code blocks carry a language; when a command and its output appear together, the command line starts with `$ `.
- Mark excerpts with `// ...`, and show the source of every concept used in the text (for example, where a registration name comes from).
- State the platform scope of a technical page, tie claims to source, tests, or build output, and make tutorial examples build as written; the full list is in references/coding-conventions.md, section "Documentation". A long concurrency, lifecycle, or architecture topic follows the bounded-parts order of the section "Explaining complex architecture" in the same file.

## Local build

The repository's `package.json` provides the npm scripts; the contribution guide lists the site verification command ([how to contribute](https://xrobot.work/docs/con_guide/con-guide-how2con)):

```bash
npm run build
```

Because `onBrokenLinks` throws, the build doubles as a link check: a broken internal link fails the build and names the offending reference. Documentation PRs target `dev`; merging `dev` into `master` deploys the site (branch conventions: [repositories and branches](https://xrobot.work/docs/con_guide/con-guide-branch)).

## PR checklist

- URL check: every new or moved page's link follows the frontmatter `id` rule (or the directory-index rule), and each link in the changed pages points to a URL that exists on the deployed site.
- Both sides updated: `docs/` (Chinese) and `i18n/en/docusaurus-plugin-content-docs/current/` (English) carry the same change, Chinese paragraphs first, English paragraphs after, no mechanical pairing.
- Register and terminology match the doc-style page: neutral third person, fixed vocabulary, identity negations removed, actual behavior described.
- Scope: the page documents one project only; other projects are linked to their own documentation.
- Platform scope: a technical page names the platform its behavior belongs to, and tutorial examples build as written.
- Commands and outputs: from real runs, with generic paths, labeled code blocks, and `$ ` prefixes where output follows.
- Version references match the current release set (LibXR 2.0.1 / xrobot 1.0.1 / CodeGenerator 6.0.1 / extension 2.0.1) unless the page documents history explicitly.
- `npm run build` passes from the repository root.
