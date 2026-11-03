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
  -destination 'platform=iOS Simulator,name=iPhone 16'

# Run tests
xcodebuild test -scheme {{SCHEME}} \
  -destination 'platform=iOS Simulator,name=iPhone 16'
```

Verification (SKILL.md Step 6) means: the template app builds with the first
command. A screenshot or simulator launch is the exit evidence for UI phases
in the roadmap — "it compiles" is not proof a screen works.

## Skills to install (Step 4)

Install **both**, into `.claude/skills/`, and record them in `docs/SETUP.md`:

| Skill | Why | Source |
|---|---|---|
| SwiftUI-Agent-Skill ("SwiftUI Pro") | Modern, accessible SwiftUI code | https://github.com/twostraws/SwiftUI-Agent-Skill |
| Apple-Hig-Designer | UI built to Apple's Human Interface Guidelines | https://github.com/axiaoge2/Apple-Hig-Designer |

Do not also install a general web-design skill for an iOS project — its
advice conflicts with HIG conventions.

## iOS-specific rules for CLAUDE.md

- Money and other precise quantities: `Decimal`, never `Double`/`Float`.
- Secrets and access tokens at runtime: Keychain only, never `UserDefaults`,
  never a plist committed to the repo.
- Support Dark Mode and Dynamic Type from the first screen, not as a
  retrofit phase; accessibility is part of every UI phase's exit test.

## Finance-app note (read aloud to the user if the project handles bank data)

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
