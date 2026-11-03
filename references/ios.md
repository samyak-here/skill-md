# Reference: iOS / SwiftUI projects

Load when `--type ios`. Defaults below go into the generated `CLAUDE.md` and
`docs/SETUP.md` unless the interview produced different answers.

## Default stack choices

- **UI:** SwiftUI. **Minimum target:** iOS 17+ unless the user says otherwise.
- **Persistence:** SwiftData for local app data (SwiftData needs iOS 17+).
- **Architecture:** MVVM — views stay declarative and thin; state and side
  effects live in observable view models / model layer, never networking or
  business rules inside a `View` body.
- **Project creation:** the user creates the blank app in Xcode and commits
  it before bootstrap. Do not hand-generate an `.xcodeproj`.

## Build / test commands

Record these in `CLAUDE.md`, replacing the scheme and app name:

```bash
# Build for the simulator
xcodebuild build -scheme {{SCHEME}} \
  -destination 'platform=iOS Simulator,name=<SIMULATOR>'

# Run tests
xcodebuild test -scheme {{SCHEME}} \
  -destination 'platform=iOS Simulator,name=<SIMULATOR>'
```

Do **not** guess a simulator name (e.g. a specific iPhone model) — it may
not exist in the user's Xcode install. During setup, discover an installed
device with `xcrun simctl list devices available` (macOS only — iOS
development requires a Mac in any case), pick one iPhone from the list,
and record that exact name in place of `<SIMULATOR>` in `CLAUDE.md`'s
build/test commands. That recorded name is what every future session uses.

Verification (SKILL.md Step 6) means: the template app builds with the first
command. A screenshot or simulator launch is the exit evidence for UI phases
in the roadmap — "it compiles" is not proof a screen works.

## Skills to install (Step 4)

Install **both**, into `.claude/skills/`, **pinned to the exact commits
below** (verified 2026-11-03), then follow SKILL.md Step 4's
read-before-install: read each skill's `SKILL.md` in full, summarise what
it will load into future sessions, flag anything asking for network
access, credential use, or destructive commands, and record URL + SHA +
date + read-summary in `docs/SETUP.md`.

| Skill | Why | Source URL | Pinned SHA | Pinned date |
|---|---|---|---|---|
| SwiftUI-Agent-Skill ("SwiftUI Pro") | Modern, accessible SwiftUI code | https://github.com/twostraws/SwiftUI-Agent-Skill | `f2920b63995263f57b3e198674e89a602efba6d2` | 2026-11-03 |
| Apple-Hig-Designer | UI built to Apple's Human Interface Guidelines | https://github.com/axiaoge2/Apple-Hig-Designer | `ff17b91ff2903ecd52940afabf97de5a73c9cd1b` | 2026-11-03 |

Install commands (pinned — never install from a moving branch):

```bash
git clone https://github.com/twostraws/SwiftUI-Agent-Skill .claude/skills/SwiftUI-Agent-Skill
git -C .claude/skills/SwiftUI-Agent-Skill checkout f2920b63995263f57b3e198674e89a602efba6d2

git clone https://github.com/axiaoge2/Apple-Hig-Designer .claude/skills/Apple-Hig-Designer
git -C .claude/skills/Apple-Hig-Designer checkout ff17b91ff2903ecd52940afabf97de5a73c9cd1b
```

Do not also install a general web-design skill for an iOS project — its
advice conflicts with HIG conventions.

## iOS-specific rules for CLAUDE.md

- Money and other precise quantities: `Decimal`, never `Double`/`Float`.
- Secrets and access tokens at runtime: Keychain only, never `UserDefaults`,
  never a plist committed to the repo.
- Support Dark Mode and Dynamic Type from the first screen, not as a
  retrofit phase; accessibility is part of every UI phase's exit test.

## Finance-app note (surface this prominently to the user during setup if the project handles bank data)

A banking or aggregator **secret key must never be embedded in an iOS app** —
anything shipped in the binary is public. Bank connections (e.g. Plaid) work
like this: the app talks to a small backend *you* control; the backend holds
the secret, performs the token exchange (`link_token` / `access_token`), and
the app only ever receives short-lived, client-safe tokens. Therefore:

- "Connect a bank account" is **two** roadmap phases, not one: a backend
  phase and an app phase.
- Until that backend exists, v1 data entry is manual entry and file import
  (e.g. CSV export from the bank/card app) — record this in PRD.md scope so
  the limitation is a decision, not a surprise.
