# Reference: Web projects

Load when `--type web`. Defaults below go into the generated `CLAUDE.md` and
`docs/SETUP.md` unless the interview produced different answers.

## Default stack choices

- **Framework:** Next.js (App Router) + TypeScript + Tailwind CSS, unless
  the interview named something else — then record the actual stack and its
  commands instead of these defaults.
- **Package manager:** use the one already present in the repo (lockfile
  wins); if none exists, default to `npm` and record the choice in SETUP.md.
- **Structure:** routes under `app/`, shared UI in `components/`, server-only
  code kept out of client components, environment access centralised in one
  module — never scatter `process.env` reads across components.

## Build / test commands

Record the equivalents for the actual stack in `CLAUDE.md`. Next.js/npm
defaults:

```bash
npm run dev      # local development
npm run build    # production build — the pre-commit verification
npm run lint     # lint
npm test         # tests, if a test script exists
```

Verification (SKILL.md Step 6) means `npm run build` passes on the untouched
template app before any feature work is planned.

## Skills to install (Step 4)

Install **both**, into `.claude/skills/`, and record them in `docs/SETUP.md`:

| Skill | Why | Source |
|---|---|---|
| taste-skill | Design taste — prevents generic, sloppy default AI UI | https://github.com/leonxlnx/taste-skill |
| impeccable | A design language that makes generated UI look deliberate | https://github.com/pbakaus/impeccable |

They are complementary (taste/judgement + a concrete design language), not
competing workflow frameworks, so installing both does not violate the
one-workflow rule in SKILL.md.

## Web-specific rules for CLAUDE.md

- Secrets live in `.env.local` / the host's environment only — `.env*` is
  gitignored (except `.env.example`, which lists names with no values).
  Anything prefixed for client exposure (e.g. `NEXT_PUBLIC_`) is public by
  definition; never put a real secret behind such a prefix.
- No placeholder/lorem copy in shipped pages: if real copy doesn't exist
  yet, the phase plan must say who provides it.
- Every page must work at a mobile width and in Dark Mode if the design
  system defines one — checked in the phase's review step, not at the end.
