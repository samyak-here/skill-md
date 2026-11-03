# project-bootstrap

A Claude Code skill that does the **complete initial setup of a new project
repo in one run** — interview, rubric files, project docs, stack-relevant
skills, reviewer agent, `.gitignore`, verification, commit — and then stops,
before a single product feature is written.

The problem it solves: every new AI coding session starts blank. Without
files in the repo telling agents the rules, you become the instruction
manual, re-explaining your stack, conventions, and scope in every session.
`project-bootstrap` writes those files once, properly, so every future agent
session in the repo inherits them.

## Install

Clone this repo into your Claude Code skills directory:

```bash
git clone https://github.com/samyak-here/skill-md.git \
  ~/.claude/skills/project-bootstrap
```

Or copy this folder to `~/.claude/skills/project-bootstrap` by any other
means — a skill is just a folder with a `SKILL.md` in it.

## Run it

1. Create your fresh project repo (for iOS, creating the blank app in Xcode
   first is recommended — generating an `.xcodeproj` by hand is flaky).
2. Open Claude Code in that repo.
3. Say: **"Bootstrap this repo"** (or "Set up a new project" / "Do the
   initial project setup").

The skill interviews you one question at a time, runs its deterministic
setup script, fills the templates from your answers, installs only the
skills your stack needs, verifies everything, and makes one commit:
`chore: initial project setup`. It then stops — feature work starts in a
fresh session, from the roadmap it wrote.

You can also run the file-creation step yourself, without an agent:

```bash
python3 scripts/bootstrap.py --project-name "Ledgerly" --type ios \
  --purpose "Personal finance tracker" --target /path/to/repo \
  --allow-placeholders
```

`--type` is one of `ios`, `web`, `python`, `generic`. The script refuses to
overwrite existing files unless you pass `--force` (and `--force` backs
each file up to `<filename>.pre-bootstrap.bak` first), so re-running it is
safe. `--allow-placeholders` is needed on a setup run because the
templates deliberately contain `{{...}}` fill-in tokens at that stage;
after filling them in, check the result with
`python3 scripts/bootstrap.py --verify --target /path/to/repo`, which
fails if any token remains.

## What a run produces

```text
your-project/
├── CLAUDE.md                  # House rules every Claude session loads (short)
├── AGENTS.md                  # Mirror of CLAUDE.md for non-Claude agents
├── .gitignore                 # Generic + stack-specific, secrets excluded
├── .claude/
│   ├── agents/
│   │   └── reviewer.md        # Review-only agent: checks, never edits
│   └── skills/                # Only the skills this stack actually needs
└── docs/
    ├── PRD.md                 # What v1 is — and explicitly what it is not
    ├── ROADMAP.md             # Phases, each with an exit test
    ├── CONTEXT.md             # Glossary and domain terms
    ├── STATE.md               # Where the project is; the resume file
    ├── SETUP.md               # What bootstrap installed: URL, pinned SHA, date, read-summary
    ├── adr/
    │   └── 0000-template.md   # Architecture decision record template
    └── plans/
        └── PLAN.md            # Per-phase spec + task-list template
```

## Design principles

- **Thin orchestrator, not a mega-skill.** This skill references and loads
  other skills at the right step. It never copies their contents into one
  giant file — merged mega-skills bloat every session's context and their
  instructions contradict each other.
- **Deterministic where it counts.** File and folder creation is done by
  `scripts/bootstrap.py` (Python 3, standard library only) rendering checked-in
  templates — same inputs, same tree, every run. The model only fills in
  project-specific content.
- **Templates, not improvisation.** Every generated document starts from a
  template in `templates/`, so quality doesn't depend on the model's mood.
- **Pinned upstreams — actually pinned.** Every external skill has an
  exact commit SHA pinned in `references/ios.md` / `references/web.md`
  (alongside its source URL and the pin date). A run clones the repo and
  checks out that SHA — never a moving branch — and records SHA + URL +
  install date + a read-summary of the skill's `SKILL.md` in
  `docs/SETUP.md`, so a setup is reproducible and auditable later. To bump
  a pin deliberately: update the SHA and pin date in the reference file,
  re-read the skill, update `docs/SETUP.md`, and commit that change on its
  own. Anyone can check a pin: `git ls-remote <repo-url>` shows the repo's
  current HEAD, or clone the repo and run `git cat-file -t <sha>` to
  confirm the pinned commit exists.
- **`CLAUDE.md` is canonical; `AGENTS.md` mirrors it.** The two files carry
  the same rules for different agent tools. When you edit one, update the
  other in the same commit — they are a mirror pair, not two sources of
  truth.
- **One workflow, no framework wars.** The default process is a checklist —
  spec → plan → build → separate review, one phase per fresh session.
  Competing workflow frameworks are never installed on top of each other.
- **Setup stops.** The skill's last step is to stop. Building features in
  the setup session is how context rots and early decisions get sloppy.

## Upstream skills it orchestrates

Nothing below is vendored into this repo. The bootstrap loads or installs
these at the step where each is needed, and records them in `docs/SETUP.md`.

| Used for | Skill | Source |
|---|---|---|
| Interview style | Grill-style interviewing — one question at a time, decisions written down as they are made | Concept only; no code copied (popularised by Matt Pocock's `grill-me` in [mattpocock/skills](https://github.com/mattpocock/skills)) |
| Behaviour rules in every `CLAUDE.md` | The 4 rules (think before coding, simplicity first, surgical changes, goal-driven execution), distilled from Andrej Karpathy's public posts about LLM coding pitfalls, as packaged by the third-party repo multica-ai/andrej-karpathy-skills | [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) |
| Workflow checklist reference | Spec → plan → build → review discipline | [obra/superpowers](https://github.com/obra/superpowers) |
| iOS stack skill | Modern, accessible SwiftUI | [twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill) |
| iOS stack skill | Apple Human Interface Guidelines for iOS/macOS UI | [axiaoge2/Apple-Hig-Designer](https://github.com/axiaoge2/Apple-Hig-Designer) |
| Web stack skill | Design taste — stops generic, sloppy AI UI output | [leonxlnx/taste-skill](https://github.com/leonxlnx/taste-skill) |
| Web stack skill | Design language for better-looking generated UI | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) |

The four stack skills (SwiftUI-Agent-Skill, Apple-Hig-Designer,
taste-skill, impeccable) are pinned to exact commit SHAs in
`references/ios.md` and `references/web.md` — see those tables for the
SHAs, pin dates, and install commands.

## Repo layout

```text
project-bootstrap/
├── SKILL.md            # The skill itself — the conductor
├── README.md
├── templates/          # Every file a run generates, as a template
├── references/         # Loaded on demand: interview, ios, web, workflow
├── scripts/
│   └── bootstrap.py    # Deterministic file creation + verification
└── tests/
    └── test_bootstrap.py  # Stdlib unittest suite for the script
```

## Uninstall / rollback

**For a project that was bootstrapped:** setup lands as a single commit
(`chore: initial project setup`), so the clean rollback is to revert it:

```bash
git revert <setup-commit>
```

Alternatively, by hand: delete the generated files listed in
`docs/SETUP.md` (the docs set, `CLAUDE.md`, `AGENTS.md`,
`.claude/agents/reviewer.md`, and anything under `.claude/skills/` that
setup installed) and remove the marked block — between
`# >>> project-bootstrap` and `# <<< project-bootstrap <<<` — from
`.gitignore`. Leave the rest of `.gitignore` alone; your own entries were
preserved, not replaced.

**For the skill itself:** delete the folder —
`rm -rf ~/.claude/skills/project-bootstrap`. Nothing else on your system
was touched by installing it.

## Changelog — v4 (2026-11-03)

Fixes from a third critical review:

- **Tokens are recognised by name, not shape.** A `{{NAME}}` is a leftover
  fill-in token if NAME (case-insensitive) is one the bundled templates
  use. A hand-lowercased `{{stack}}` is now caught; `{{ user.name }}`,
  `{{ User }}` and `{{...}}` in a project's own docs are still ignored.
- **The reviewer can now see what changed.** It still has no shell, so the
  building session leaves a review packet: `.review/diff.patch`
  (`git log -p --stat <base>..HEAD`, so removed secrets stay visible) and
  `.review/test-output.txt`. No diff means **Blocked**; the reviewer treats
  the test output as self-reported and says so. `.review/` is gitignored.
- **`--verify` content checks are per-skill.** Every row of the SETUP.md
  skills table needs a full 40-hex SHA (equal to the pin in `references/`
  for known skills) and a real read-summary; the none-sentence cannot
  coexist with leftover rows. Out-of-scope items must be non-trivial
  (not `n/a`, `none`, `TBD`, or under 8 characters).
- Tests now import the script's own token logic, so fixtures cannot drift
  from it; new tests cover each item above.

Not fixed on purpose: the reviewer's tests remain unverifiable by the
reviewer itself (no shell), and `AGENTS.md` still mirrors `CLAUDE.md` by
convention only.

## Changelog — v3 (2026-11-03)

Fixes from a second critical review, which caught v2's verify gate
failing on its own reviewer template:

- **Reviewer false-positive fixed, scanner pattern narrowed.** The
  reviewer template's gate paragraph no longer contains token-shaped
  prose, and the token scanner only flags bootstrap-style tokens (inner
  content starting with an uppercase letter) — prose like `{{...}}` and
  other engines' examples (`{{ user.name }}`) are no longer flagged.
- **`--verify` refuses `--allow-placeholders`** (exit 2): verification
  must run against filled files, and a tired agent can no longer "fix" a
  failing Step 6 by adding the flag.
- **Backup handling fixed.** A `--force` backup never overwrites an
  earlier one (`.bak.1`, `.bak.2`, ...), no backup is written for a
  `.gitignore` append (nothing is destroyed by appending), and the
  generated `.gitignore` now ignores `*.pre-bootstrap.bak*` so backups
  don't pollute `git status`.
- **`*.key` restored** to the generic secrets fragment — security wins
  over the nuisance of ignoring the odd harmless key file.
- **Reviewer read-only is now enforced by its tool list** (Read, Grep,
  Glob — no edit tools, no shell) instead of by prose. It reviews test
  evidence supplied by the building session or CI, and without any its
  verdict cannot be a clean Pass.
- **`--verify` checks content, not just tokens:** the PRD's out-of-scope
  list must be non-empty, and `docs/SETUP.md` must record a pinned skill
  SHA or state that no stack skills were installed.
- **Regression tests added**, including a fill that works the way
  SKILL.md Step 3 does (only genuine tokens are replaced — v2's test
  helper blanket-replaced everything, which hid the false-positive).

## Changelog — v2 (2026-11-03)

Fixes from a full critical review of v1:

- Verification now **fails on leftover `{{...}}` template tokens** (with a
  per-file listing), plus a `--verify` mode that re-checks a bootstrapped
  project fresh, and an `--allow-placeholders` flag for the setup run
  where tokens are expected.
- Upstream skills are **pinned to exact commit SHAs** and there is a
  mandatory **read-before-install** step: read each skill's `SKILL.md`,
  summarise what it loads, flag network/credential/destructive requests,
  and record all of it in `docs/SETUP.md`.
- iOS `.gitignore` fixed: no more `*.xcworkspace` ignore or the
  meaningless `!default.xcworkspace`; the user-data inside
  `*.xcodeproj/project.xcworkspace` is ignored instead, and
  `GoogleService-Info.plist` is no longer ignored by default (it's client
  config, commonly committed).
- Reviewer agent honesty fix: it states plainly that read-only is an
  instruction, not a tooling guarantee (it has Bash, needed for tests),
  the hardcoded model pin is gone, and it must refuse to review against
  placeholder docs.
- Script hardening: single-pass rendering (values are never re-expanded),
  a missing `--target` is an error instead of a silently created tree, a
  mangled `.gitignore` marker order is a clean error with the file left
  untouched, `--force` backs up every overwritten file to
  `<filename>.pre-bootstrap.bak` first, and skipped (pre-existing) files
  are token-checked too.
- A real test suite for the script (`tests/test_bootstrap.py`, stdlib
  unittest — 10 tests covering fresh runs, token failure, verify mode,
  idempotency, force backups, target and gitignore guards).
- Consistency: the CLAUDE.md length warning now matches the documented
  ~80-line rule; the iOS reference no longer hardcodes a simulator model
  (discover one with `xcrun simctl list devices available` and record it);
  README corrections (the unverified `npx skills add` install claim is
  removed, and the Karpathy credit now says where the 4 rules actually
  come from).

## Licence / credit

Templates and the bootstrap script are original to this repo. Upstream
skills remain under their own licences and are installed from their own
repositories at setup time — see the table above.
