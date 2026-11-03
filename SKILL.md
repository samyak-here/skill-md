---
name: project-bootstrap
description: Do the complete initial project setup for a fresh repository — interview the user, create CLAUDE.md, AGENTS.md, and project docs (PRD, ROADMAP, CONTEXT, STATE, SETUP, ADRs), install only the skills relevant to the project's stack, add a reviewer agent, and fix .gitignore — then verify, commit, and stop. Use when the user says "set up a new project", "bootstrap this repo", "initial project setup", "scaffold this project", or asks to set up a fresh repo for AI coding agents. Do NOT use for adding a feature, fixing a bug, or continuing work on a project that is already set up.
---

# Project Bootstrap

A thin orchestrator. This skill does not contain other skills — it loads the
right one at the right step, runs a deterministic script for file creation,
and fills templates from the user's answers. If a step below conflicts with a
copied-in skill, this skill wins.

## Precedence rules — setup session only

This ordering applies **only during the setup session, while this skill is
active**. When instructions conflict during setup, apply them in this order:

1. **This skill** (`project-bootstrap`) — setup scope, safety rules, stop rule.
2. **The project's own `CLAUDE.md`** — as it is being created.
3. **The stack skill** — e.g. the SwiftUI or design skill for this project type.
4. **The workflow checklist** — `references/workflow.md`, the default process.

Once setup ends, this skill is no longer active and the ordering expires:
**the project's `CLAUDE.md` (plus its docs) is the only standing
instruction set** for future sessions.

Never install two competing workflow frameworks (for example, do not install
both a heavy spec-driven framework and this skill's workflow checklist).
If the user explicitly names a workflow framework, use that one *instead of*
the default checklist and record the choice in `docs/SETUP.md`.

## Safety rules (never overridden)

- Never write secrets, API keys, or tokens into any generated file, and never
  put a server-side secret (e.g. a banking API secret) inside a client app.
- Never overwrite an existing file without the user's go-ahead
  (`scripts/bootstrap.py` refuses by default; `--force` is opt-in only,
  and with `--force` the script first backs each file up to
  `<filename>.pre-bootstrap.bak`).
- Setup only: do not start building product features in this session.

## Workflow

Run these steps in order. Do not skip ahead.

### 1. Interview

Load `references/interview.md`. Ask its questions **one at a time**, and write
each answer into the relevant doc as it arrives — do not hold everything in
conversation memory. If the user answers several questions at once, record
every answer given, mark those questions answered, and continue from the
first unanswered one — never re-ask an answered question. Stop interviewing
when every question has an answer or the user explicitly defers it (record
deferred items in `docs/STATE.md`).

### 2. Run the script

From this skill's directory:

```bash
python3 scripts/bootstrap.py \
  --project-name "<name from interview>" \
  --type <ios|web|python|generic> \
  --purpose "<one-line purpose from interview>" \
  --target <path to the fresh project repo> \
  --allow-placeholders
```

`--allow-placeholders` is required here: at this stage the templates still
contain `{{...}}` fill-in tokens on purpose (Step 3 fills them), so the
script passes verification with a per-file token warning instead of
failing. The target directory must already exist (the fresh project repo);
the script errors on a missing target rather than creating a typo'd path —
pass `--create-target` only if the user explicitly wants the script to
create that directory.

This creates the directories and renders the templates deterministically.
Report exactly what it created, skipped, or overwrote — never claim a file
exists that the script did not report.

### 3. Fill the templates from the interview answers

Replace the remaining fill-in prompts in the generated files with the actual
answers: stack and build/test commands in `CLAUDE.md` / `AGENTS.md`, scope in
`docs/PRD.md`, phases in `docs/ROADMAP.md`, glossary terms in
`docs/CONTEXT.md`. Keep `CLAUDE.md` short — if it passes ~80 lines, move
detail into `docs/` and leave a pointer.

### 4. Install stack skills — pinned, read before install

Load the reference for the project type and install only the skills it lists:

- iOS → `references/ios.md`
- Web → `references/web.md`
- Python / generic → no stack skill by default; note that choice in SETUP.

Every listed skill is **pinned to an exact commit SHA** in the reference's
pinned-skills table. Install means: clone the repo into the project's
`.claude/skills/`, then `git checkout` the pinned SHA — never install from
a moving branch, and never bump a pin without recording the new SHA.

**Read-before-install is mandatory.** After cloning, before the install
counts as complete, for each skill:

1. Read its `SKILL.md` in full (and note anything else it loads by default).
2. Write a 2–3 line summary: what instructions this skill will load into
   future sessions.
3. Flag anything that asks for network access, credential use, or
   destructive commands. Surface flags to the user; do not silently install
   a skill that asks for any of those without the user's go-ahead.

Record in `docs/SETUP.md`, per skill: name, exact source URL, **pinned
SHA**, install date, and the read-summary. Do not copy a skill's contents
into `CLAUDE.md` — the skill stays a separate, loadable unit.

### 5. Set the workflow rule

Write the default loop from `references/workflow.md` into `CLAUDE.md` if it is
not already there: **spec → plan → build → separate review**, one phase per
fresh session, `docs/STATE.md` updated at the end of every session.

### 6. Verify — fresh check, not the Step 2 output

Run verification **now**, fresh, in `--verify` mode (it reads the target
as it currently stands and modifies nothing):

```bash
python3 scripts/bootstrap.py --verify --target <path to the project repo>
```

Do not reuse the Step 2 run's output — that run predates Step 3's fill-in
and Step 4's installs. Do **not** add `--allow-placeholders` to the
verify command — the script rejects that combination outright, because
verification must run against filled files. `--verify` fails on any
leftover fill-in token in the generated files: **if it fails on tokens,
Step 3 was not finished** — go back, fill the remaining tokens, and
re-run `--verify` until it passes. `--verify` also checks content, not
just tokens: the PRD's out-of-scope list must be non-empty, and
`docs/SETUP.md` must record a pinned SHA for each installed skill (or
state that no stack skills were installed). Also:

- Confirm `.gitignore` covers secrets for this stack.
- Confirm the project's empty/template app still builds with the build
  command recorded in `CLAUDE.md` (if a build command exists yet).
- Re-read `docs/SETUP.md`: every installed skill must be listed with its
  source URL, pinned SHA, install date, and read-summary.

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

**Escape hatch:** stop *unless the user explicitly instructs you to
continue*. If they do, recommend — once — that Phase 1 still happens in a
fresh session, then obey the user and continue.

## Reference files — load on demand

| File | Load when |
|---|---|
| `references/interview.md` | Always — Step 1. |
| `references/ios.md` | Project type is `ios`. |
| `references/web.md` | Project type is `web`. |
| `references/workflow.md` | Step 5, and any later session working in a bootstrapped repo. |
