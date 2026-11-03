# Interview — run before any file is created

Grill-style: **one question at a time**, in the order below. Do not present
the list as a form. For each answer:

- Write it into the target doc immediately (noted in the right column).
- Ask a follow-up only if the answer is ambiguous in a way that changes a
  generated file — otherwise accept and move on.
- If the user defers a question, record it under "Blockers / deferred" in
  `docs/STATE.md` and continue.
- If the user answers several questions at once, record **every** answer
  given, mark those questions answered, and continue from the first
  unanswered one. Do not re-ask a question that was already answered in a
  batch — one-at-a-time is the default pace, not a reason to discard
  answers.

## Questions

| # | Question (ask in your own words, one at a time) | Written to |
|---|---|---|
| 1 | What is the project called? | Everywhere `{{PROJECT_NAME}}` appears |
| 2 | In one line, what does it do? | `{{PURPOSE}}` in CLAUDE.md / PRD.md |
| 3 | Who is it for — who actually uses v1? | PRD.md → Users |
| 4 | What are the v1 features? Push back past ~5: anything beyond the first five goes to question 5. | PRD.md → v1 scope |
| 5 | What is explicitly **out of scope** for v1? ("Not in v1" must be a real list, not blank — an empty out-of-scope list is how scope creeps.) | PRD.md → Out of scope |
| 6 | What stack? (Language/framework, and the project type for the script: `ios`, `web`, `python`, or `generic`.) | CLAUDE.md → Stack; script `--type` |
| 7 | Where does data live? (Local only, a database, files, an API — and how is it persisted?) | PRD.md → Data; CONTEXT.md if terms arise |
| 8 | Does v1 need auth / user accounts? If yes, provided by what? | PRD.md → Scope or Out of scope; CLAUDE.md → Rules |
| 9 | Any external services or APIs? (Payments, maps, AI models, bank data…) For each: is any part of it a **secret that must never ship in a client app**? | PRD.md; CLAUDE.md → Rules (secret handling) |
| 10 | What does "done" look like for v1 — the concrete thing you can point at and say it works? | PRD.md → Success criteria; ROADMAP.md final phase exit test |

## Closing the interview

Before running the script:

1. Read back a 5-line summary: name, purpose, v1 features, out-of-scope
   highlights, stack.
2. Ask: "Anything wrong or missing before I set it up?"
3. Fix corrections in the docs/state notes, then proceed to Step 2 of
   SKILL.md (run `scripts/bootstrap.py` with `--project-name`, `--type`,
   and `--purpose` from questions 1, 6, and 2).
