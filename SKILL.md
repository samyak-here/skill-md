---
name: project-bootstrap
description: Do the complete initial project setup for a fresh repository — interview the user, create CLAUDE.md, AGENTS.md, and project docs (PRD, ROADMAP, CONTEXT, STATE, SETUP, ADRs), install only the skills relevant to the project's stack, add a reviewer agent, and fix .gitignore — then verify, commit, and stop. Use when the user says "set up a new project", "bootstrap this repo", "initial project setup", "scaffold this project", or asks to set up a fresh repo for AI coding agents. Do NOT use for adding a feature, fixing a bug, or continuing an already-bootstrapped project — use the workflow in references/workflow.md for those instead.
---

# Project Bootstrap

A thin orchestrator. This skill does not contain other skills — it loads the
right one at the right step, runs a deterministic script for file creation,
and fills templates from the user's answers. If a step below conflicts with a
copied-in skill, this skill wins.

## Precedence rules

When instructions conflict, apply them in this order:

1. **This skill** (`project-bootstrap`) — setup scope, safety rules, stop rule.
2. **The project's own `CLAUDE.md`** — once created, it is the project's law.
3. **The stack skill** — e.g. the SwiftUI or design skill for this project type.
4. **The workflow checklist** — `references/workflow.md`, the default process.

Never install two competing workflow frameworks (for example, do not install
both a heavy spec-driven framework and this skill's workflow checklist).
If the user explicitly names a workflow framework, use that one *instead of*
the default checklist and record the choice in `docs/SETUP.md`.

## Safety rules (never overridden)

- Never write secrets, API keys, or tokens into any generated file, and never
  put a server-side secret (e.g. a banking API secret) inside a client app.
- Never overwrite an existing file without the user's go-ahead
  (`scripts/bootstrap.py` refuses by default; `--force` is opt-in only).
- Setup only: do not start building product features in this session.

## Workflow

Run these steps in order. Do not skip ahead.

### 1. Interview

Load `references/interview.md`. Ask its questions **one at a time**, and write
each answer into the relevant doc as it arrives — do not hold everything in
conversation memory. Stop interviewing when every question has an answer or
the user explicitly defers it (record deferred items in `docs/STATE.md`).

### 2. Run the script

From this skill's directory:

```bash
python3 scripts/bootstrap.py \
  --project-name "<name from interview>" \
  --type <ios|web|python|generic> \
  --purpose "<one-line purpose from interview>" \
  --target <path to the fresh project repo>
```

This creates the directories and renders the templates deterministically.
Report exactly what it created, skipped, or overwrote — never claim a file
exists that the script did not report.

### 3. Fill the templates from the interview answers

Replace the remaining fill-in prompts in the generated files with the actual
answers: stack and build/test commands in `CLAUDE.md` / `AGENTS.md`, scope in
`docs/PRD.md`, phases in `docs/ROADMAP.md`, glossary terms in
`docs/CONTEXT.md`. Keep `CLAUDE.md` short — if it passes ~80 lines, move
detail into `docs/` and leave a pointer.

### 4. Install stack skills — relevant ones only

Load the reference for the project type and install only the skills it lists:

- iOS → `references/ios.md`
- Web → `references/web.md`
- Python / generic → no stack skill by default; note that choice in SETUP.

Clone each selected skill into the project's `.claude/skills/` (or use the
project's existing skill-install method). Then record every installed skill,
its exact source URL, and the install date in `docs/SETUP.md`. Do not copy a
skill's contents into `CLAUDE.md` — the skill stays a separate, loadable unit.

### 5. Set the workflow rule

Write the default loop from `references/workflow.md` into `CLAUDE.md` if it is
not already there: **spec → plan → build → separate review**, one phase per
fresh session, `docs/STATE.md` updated at the end of every session.

### 6. Verify

- Run the script's verification output check: all required files exist.
- Confirm `.gitignore` covers secrets for this stack.
- Confirm the project's empty/template app still builds with the build
  command recorded in `CLAUDE.md` (if a build command exists yet).
- Re-read `docs/SETUP.md`: it must list what was installed, from where, when.

### 7. Commit

One commit, nothing more:

```text
chore: initial project setup
```

Include only the setup files. If git user identity or a remote is not
configured, say so and leave the commit to the user — do not invent either.

### 8. Stop

Show the user the created file tree and `docs/ROADMAP.md`'s Phase 1.
Then stop. Do not start Phase 1, do not build a feature, and do not offer to
"just get the skeleton started" — the next phase belongs in a fresh session
(see `references/workflow.md`).

## Reference files — load on demand

| File | Load when |
|---|---|
| `references/interview.md` | Always — Step 1. |
| `references/ios.md` | Project type is `ios`. |
| `references/web.md` | Project type is `web`. |
| `references/workflow.md` | Step 5, and any later session working in a bootstrapped repo. |
