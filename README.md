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
means — a skill is just a folder with a `SKILL.md` in it. If you use the
skills CLI, `npx skills add samyak-here/skill-md` installs it the
same way.

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
  --purpose "Personal finance tracker" --target /path/to/repo
```

`--type` is one of `ios`, `web`, `python`, `generic`. The script refuses to
overwrite existing files unless you pass `--force`, so re-running it is safe.

## What a run produces

```text
your-project/
├── CLAUDE.md                  # House rules every Claude session loads (short)
├── AGENTS.md                  # The same rules for non-Claude agents
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
    ├── SETUP.md               # What bootstrap installed, source URLs, date
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
- **Pinned upstreams.** Every external skill a run installs is recorded with
  its exact source URL and install date in `docs/SETUP.md`, so a setup is
  reproducible and auditable later.
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
| Behaviour rules in every `CLAUDE.md` | The 4 rules (think before coding, simplicity first, surgical changes, goal-driven execution), summarised | [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) |
| Workflow checklist reference | Spec → plan → build → review discipline | [obra/superpowers](https://github.com/obra/superpowers) |
| iOS stack skill | Modern, accessible SwiftUI | [twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill) |
| iOS stack skill | Apple Human Interface Guidelines for iOS/macOS UI | [axiaoge2/Apple-Hig-Designer](https://github.com/axiaoge2/Apple-Hig-Designer) |
| Web stack skill | Design taste — stops generic, sloppy AI UI output | [leonxlnx/taste-skill](https://github.com/leonxlnx/taste-skill) |
| Web stack skill | Design language for better-looking generated UI | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) |

## Repo layout

```text
project-bootstrap/
├── SKILL.md            # The skill itself — the conductor
├── README.md
├── templates/          # Every file a run generates, as a template
├── references/         # Loaded on demand: interview, ios, web, workflow
└── scripts/
    └── bootstrap.py    # Deterministic file creation + verification
```

## Licence / credit

Templates and the bootstrap script are original to this repo. Upstream
skills remain under their own licences and are installed from their own
repositories at setup time — see the table above.
