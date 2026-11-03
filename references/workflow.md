# Reference: the workflow every bootstrapped project follows

This is the default process written into each project's `CLAUDE.md` at setup
(SKILL.md Step 5). It is a checklist, deliberately — not a framework install.
It synthesises the spec → plan → build → review discipline popularised by
[obra/superpowers](https://github.com/obra/superpowers); if the user chose a
different workflow framework at setup, this file no longer applies and
`docs/SETUP.md` says so.

## The loop — per roadmap phase

Work **one phase of `docs/ROADMAP.md` at a time**, in this order:

1. **Spec** — copy `docs/plans/PLAN.md` for this phase. State the phase goal,
   what's in scope, what's out, and how completion is proven (its exit test).
   Get the user's approval of the spec before writing code.
2. **Plan** — break the spec into small tasks in the same file: each task is
   one sitting of work, names the files it touches, and is checkable on its
   own. No task like "build the dashboard" — that's a phase, not a task.
3. **Build** — one task at a time. Tests first for anything with a provably
   right answer (calculations, parsing, data transforms). After each task:
   run the project's build/test commands from `CLAUDE.md`, then commit that
   task alone with a message that says what it did.
4. **Review — separate from building** — when the phase's tasks are done, run
   the project's reviewer agent (`.claude/agents/reviewer.md`) in a **separate
   pass/session** from the one that wrote the code. The reviewer checks and
   reports; it never edits. Fix its findings, re-run build/tests, and only
   then tick the phase's exit test in `ROADMAP.md`.

A phase is done when its exit test passes **and** the review is clean — not
when the code merely exists.

## Fresh session per phase (non-negotiable)

- Start each phase in a **fresh agent session**. Long single sessions rot:
  context fills, early decisions get half-remembered, quality drops in
  exactly the phases that are hardest to redo.
- Never start the next phase in the same session that finished the previous
  one, however tempting "just keep going" is. Setup (SKILL.md) ends with
  Stop for the same reason.

## STATE.md resume protocol

`docs/STATE.md` is how a fresh session picks up cold. Every session, without
exception:

- **At the start:** read `CLAUDE.md`, then `docs/STATE.md`, then the current
  phase in `docs/ROADMAP.md` (and its plan file, if one exists). That is the
  entire catch-up — if it isn't in those files, it effectively didn't happen,
  which is why the next rule exists.
- **At the end:** update `STATE.md` before finishing — current phase, what
  this session actually did (not what it intended), the single next step,
  and any blockers or deferred decisions. A session that ends without
  updating STATE.md has left a trap for the next one.

## Standing rules inside the loop

- **Surgical changes:** a task touches only what its plan entry names.
  Unrelated clean-ups are new tasks, proposed — never smuggled in.
- **Decisions get ADRs:** any choice a future session might relitigate
  (library, data model, vendor) gets a short record from
  `docs/adr/0000-template.md`, numbered sequentially.
- **Secrets:** never in code, docs, plans, or commits. If a task needs one,
  it references the environment variable name only.
