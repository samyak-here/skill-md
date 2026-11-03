#!/usr/bin/env python3
"""project-bootstrap — deterministic initial file setup for a fresh repo.

Renders the templates bundled with the project-bootstrap skill into a target
project directory, substituting {{PROJECT_NAME}}, {{PROJECT_TYPE}},
{{PURPOSE}} and {{DATE}} in a single pass (values are never re-scanned, so a
purpose containing "{{DATE}}" stays literal). Other {{TOKENS}} in the
templates are deliberate fill-in prompts for the orchestrating agent / user.

Python 3, standard library only.

Usage:
    # Setup run (Step 2 of SKILL.md — placeholders are expected at this stage)
    python3 bootstrap.py --project-name NAME --type {ios,web,python,generic} \
        --purpose "ONE LINE" [--target DIR] [--create-target] \
        [--allow-placeholders] [--force]

    # Verification only (Step 6 of SKILL.md) — creates/modifies nothing
    python3 bootstrap.py --verify [--target DIR]

Behaviour:
  * Creates docs/, docs/adr/, docs/plans/, .claude/agents/, .claude/skills/.
  * Refuses to overwrite existing files unless --force (skips are reported).
    With --force, every overwritten file is first backed up to
    <filename>.pre-bootstrap.bak in the same directory (an existing backup
    is never overwritten — the next backup gets a .1, .2, ... suffix).
  * The target must already exist unless --create-target is passed; a typo
    in the path is an error, not a silently created directory tree.
  * .gitignore: built from the generic + stack fragments (de-duplicated).
    If a .gitignore already exists, the bootstrap block is appended between
    markers; a block already present is skipped (or replaced with --force),
    so re-running never corrupts or duplicates it. A mangled block (end
    marker before start marker) is a clean error, file left untouched.
  * Verification checks that required dirs/files exist AND scans every
    generated file for leftover fill-in tokens (a token is a {{NAME}} whose
    NAME — case-insensitively — is used by the bundled templates). Leftover tokens fail
    verification unless --allow-placeholders is passed (the Step 2 setup
    run), in which case they are reported as a per-file warning.
    --allow-placeholders is rejected together with --verify: Step 6
    verification must run against filled files.
  * A fill-in token is a {{NAME}} whose NAME (case-insensitive) is one the
    bundled templates use ({{STACK}}, {{BUILD_COMMAND}}, ...). Prose like
    {{...}} and other engines' examples ({{ user.name }}) are NOT flagged,
    while a hand-lowercased leftover such as {{stack}} IS.
  * Verification also checks content, not just existence: the PRD's
    out-of-scope list must have a real (non-trivial) item, and
    docs/SETUP.md must either state that no stack skills were installed or
    list EVERY installed skill with a full 40-hex SHA (equal to the pin in
    references/ for known skills) and a real read-summary. In a setup run
    with --allow-placeholders these checks are warnings only.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"

PROJECT_TYPES = ("ios", "web", "python", "generic")

# (template path relative to templates/, destination relative to target)
FILE_MAP = [
    ("CLAUDE.md.tmpl", "CLAUDE.md"),
    ("AGENTS.md.tmpl", "AGENTS.md"),
    ("docs/PRD.md.tmpl", "docs/PRD.md"),
    ("docs/ROADMAP.md.tmpl", "docs/ROADMAP.md"),
    ("docs/CONTEXT.md.tmpl", "docs/CONTEXT.md"),
    ("docs/STATE.md.tmpl", "docs/STATE.md"),
    ("docs/SETUP.md.tmpl", "docs/SETUP.md"),
    ("docs/adr/0000-template.md", "docs/adr/0000-template.md"),
    ("docs/plans/PLAN.md.tmpl", "docs/plans/PLAN.md"),
    ("agents/reviewer.md.tmpl", ".claude/agents/reviewer.md"),
]

REQUIRED_DIRS = [
    "docs",
    "docs/adr",
    "docs/plans",
    ".claude/agents",
    ".claude/skills",
]

GITIGNORE_START = "# >>> project-bootstrap (generated — edits inside this block are replaced on --force) >>>"
GITIGNORE_END = "# <<< project-bootstrap <<<"

CLAUDE_LINE_WARN = 80

# Any {{...}} span; whether it is a *bootstrap* token is decided by name
# (see known_token_names), not by its shape. Prose like {{...}} and other
# engines' examples ({{ user.name }}, {{ count }}) have no known name and
# are never flagged; a hand-edited {{stack}} IS flagged because STACK is a
# name the templates use.
BRACE_RE = re.compile(r"\{\{[^{}]*\}\}")
TOKEN_NAME_RE = re.compile(r"^\{\{\s*([A-Za-z][A-Za-z0-9_]*)(?![A-Za-z0-9_])")
UPPER_NAME_RE = re.compile(r"[A-Z][A-Z0-9_]*")

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PIN_ROW_RE = re.compile(r"(https://github\.com/[^\s|)]+)\s*\|\s*`([0-9a-f]{40})`")
NO_SKILLS_SENTENCE = "No stack skills installed for this project."
OUT_OF_SCOPE_HEADING_RE = re.compile(r"out.of.scope", re.IGNORECASE)
TRIVIAL_ITEMS = {"todo", "tbd", "n/a", "na", "none", "nothing", "-", "?", "..."}
MIN_ITEM_CHARS = 8
MIN_SUMMARY_CHARS = 20

_KNOWN_NAMES: set[str] | None = None
_KNOWN_PINS: dict[str, str] | None = None


def known_token_names() -> set[str]:
    """Upper-case token names used anywhere in the bundled templates and
    references — the only names verification treats as fill-in tokens."""
    global _KNOWN_NAMES
    if _KNOWN_NAMES is None:
        names: set[str] = set()
        for root in (TEMPLATES, SKILL_ROOT / "references"):
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in (".tmpl", ".md"):
                    for m in BRACE_RE.finditer(path.read_text(encoding="utf-8")):
                        n = TOKEN_NAME_RE.match(m.group(0))
                        if n and UPPER_NAME_RE.fullmatch(n.group(1)):
                            names.add(n.group(1))
        _KNOWN_NAMES = names
    return _KNOWN_NAMES


def known_pins() -> dict[str, str]:
    """{repo URL: pinned SHA} parsed from the references' pinned-skills tables."""
    global _KNOWN_PINS
    if _KNOWN_PINS is None:
        pins: dict[str, str] = {}
        for path in (SKILL_ROOT / "references").glob("*.md"):
            for m in PIN_ROW_RE.finditer(path.read_text(encoding="utf-8")):
                pins[m.group(1).rstrip("/")] = m.group(2)
        _KNOWN_PINS = pins
    return _KNOWN_PINS


def _is_token(span: str) -> bool:
    n = TOKEN_NAME_RE.match(span)
    return bool(n) and n.group(1).upper() in known_token_names()


def strip_tokens(text: str) -> str:
    return BRACE_RE.sub(lambda m: "" if _is_token(m.group(0)) else m.group(0), text)


class BootstrapError(Exception):
    """A clean, human-readable failure (printed without a traceback)."""


def render(text: str, values: dict[str, str]) -> str:
    """Substitute the known tokens in a single regex pass.

    re.sub never re-scans replacement text, so a value that itself contains
    something like {{DATE}} is inserted literally. Unknown {{TOKENS}} are
    left untouched (they are fill-in prompts).
    """
    if not values:
        return text
    pattern = re.compile(r"\{\{(" + "|".join(re.escape(k) for k in values) + r")\}\}")
    return pattern.sub(lambda m: values[m.group(1)], text)


def find_tokens(text: str) -> list[str]:
    """Distinct leftover {{...}} tokens, in order of first appearance."""
    seen: list[str] = []
    for match in BRACE_RE.finditer(text):
        token = match.group(0)
        if _is_token(token) and token not in seen:
            seen.append(token)
    return seen


def backup_file(path: Path, report: dict[str, list[str]]) -> None:
    """Copy path to <filename>.pre-bootstrap.bak next to it, before overwrite.

    An existing backup is never overwritten: if the plain .bak name is
    taken, use .bak.1, .bak.2, ... so each backup keeps the distinct
    content it preserved.
    """
    backup = path.with_name(path.name + ".pre-bootstrap.bak")
    counter = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.pre-bootstrap.bak.{counter}")
        counter += 1
    backup.write_bytes(path.read_bytes())
    report["backed_up"].append(str(backup))


def build_gitignore_block(project_type: str, date: str) -> str:
    """Concatenate generic + stack fragments, de-duplicating lines."""
    fragments = ["generic"]
    if project_type != "generic":
        fragments.append(project_type)

    seen: set[str] = set()
    lines: list[str] = [GITIGNORE_START, f"# Generated by project-bootstrap on {date}"]
    for name in fragments:
        frag_path = TEMPLATES / "gitignore" / f"{name}.txt"
        if not frag_path.is_file():
            raise FileNotFoundError(f"Missing gitignore fragment: {frag_path}")
        lines.append("")
        lines.append(f"# --- from templates/gitignore/{name}.txt ---")
        for raw in frag_path.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            if line and not line.startswith("#"):
                if line in seen:
                    continue
                seen.add(line)
            lines.append(line)
    lines.append(GITIGNORE_END)
    return "\n".join(lines) + "\n"


def handle_gitignore(target: Path, project_type: str, date: str, force: bool,
                     report: dict[str, list[str]]) -> None:
    path = target / ".gitignore"
    block = build_gitignore_block(project_type, date)

    if not path.exists():
        path.write_text(block, encoding="utf-8")
        report["created"].append(".gitignore")
        return

    existing = path.read_text(encoding="utf-8")
    if GITIGNORE_START in existing and GITIGNORE_END in existing:
        start = existing.index(GITIGNORE_START)
        end_marker = existing.index(GITIGNORE_END)
        if end_marker < start:
            raise BootstrapError(
                ".gitignore is mangled: the project-bootstrap end marker "
                f"({GITIGNORE_END}) appears before the start marker. "
                "Fix or remove the marked block by hand, then re-run. "
                "The file was left unchanged.")
        if not force:
            report["skipped"].append(".gitignore (bootstrap block already present)")
            return
        # Replace just the old bootstrap block, preserving user entries.
        end = end_marker + len(GITIGNORE_END)
        if existing[end:end + 1] == "\n":
            end += 1
        backup_file(path, report)
        updated = existing[:start] + block + existing[end:]
        path.write_text(updated, encoding="utf-8")
        report["overwritten"].append(".gitignore (bootstrap block replaced)")
        return

    # Existing user .gitignore without a bootstrap block: append, never
    # replace. No backup is made here — appending destroys nothing, the
    # user's original content stays in the file untouched.
    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    path.write_text(existing + separator + block, encoding="utf-8")
    report["created"].append(".gitignore (bootstrap block appended to existing file)")


def prd_out_of_scope_ok(text: str) -> bool:
    """True if the PRD's out-of-scope section lists at least one real item.

    Only list items count — the section's intro sentence is present in the
    template even when the list itself was never filled in, so counting
    prose would make this check useless. An item counts if, after removing
    any leftover template tokens from it, something real remains (not
    trivial: at least MIN_ITEM_CHARS characters, and not TODO/TBD/n/a/none).
    """
    lines = text.splitlines()
    in_section = False
    for line in lines:
        if line.lstrip().startswith("#"):
            if OUT_OF_SCOPE_HEADING_RE.search(line):
                in_section = True
                continue
            if in_section:
                break  # next heading: section ended
        if not in_section:
            continue
        item = re.match(r"\s*[-*]\s+(.*)$", line)
        if not item:
            continue
        content = strip_tokens(item.group(1)).strip()
        content = content.strip("`*_ ").strip()
        if len(content) >= MIN_ITEM_CHARS and content.lower() not in TRIVIAL_ITEMS:
            return True
    return False


def setup_record_problems(text: str) -> list[str]:
    """Problems with docs/SETUP.md's installed-skills record ([] when fine).

    Either the none-sentence stands on a line of its own, or the skills
    table ("Pinned SHA" column) has at least one data row and EVERY row has
    a full 40-hex SHA, a read-summary of real length, and — when the repo
    URL is one of the pinned skills in references/ — exactly the pinned SHA.
    """
    lines = text.splitlines()
    has_sentence = any(line.strip() == NO_SKILLS_SENTENCE for line in lines)

    header_idx = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and "pinned sha" in line.lower():
            header_idx = i
            break
    if has_sentence and header_idx is None:
        return []
    if header_idx is None:
        return [f'no skills table with a "Pinned SHA" column and no '
                f'"{NO_SKILLS_SENTENCE}" statement']

    cols = [c.strip().lower() for c in lines[header_idx].strip().strip("|").split("|")]
    sha_i = next(i for i, c in enumerate(cols) if "pinned sha" in c)
    url_i = next((i for i, c in enumerate(cols) if "url" in c), None)
    sum_i = next((i for i, c in enumerate(cols) if "summary" in c), None)

    problems: list[str] = []
    rows = 0
    for line in lines[header_idx + 1:]:
        if not line.lstrip().startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue  # separator row
        rows += 1
        name = cells[0] if cells else f"row {rows}"
        sha = cells[sha_i] if sha_i < len(cells) else ""
        if not FULL_SHA_RE.match(sha):
            problems.append(f"{name}: pinned SHA is not a full 40-hex SHA ({sha!r})")
        elif url_i is not None and url_i < len(cells):
            pin = known_pins().get(cells[url_i].rstrip("/"))
            if pin and pin != sha:
                problems.append(
                    f"{name}: SHA {sha[:12]}… differs from the pin in "
                    f"references/ ({pin[:12]}…) — bump the reference first")
        if sum_i is not None:
            summary = strip_tokens(cells[sum_i]) if sum_i < len(cells) else ""
            if len(summary.strip()) < MIN_SUMMARY_CHARS:
                problems.append(f"{name}: read-summary missing or too short")
    if has_sentence:
        # The sentence claims nothing was installed: leftover table rows
        # contradict it, so they must be deleted.
        return (["the none-sentence is present but the skills table still "
                 "has rows — delete the rows"] if rows else [])
    if rows == 0:
        problems.append("skills table has no rows and no none-sentence")
    return problems


def verify_target(target: Path, allow_placeholders: bool,
                  skipped: set[str] | None = None) -> int:
    """Check dirs, files, .gitignore block, CLAUDE.md length, leftover tokens.

    Prints a full report. Returns 0 on pass, 1 on failure. The token scan
    covers every generated file on disk — including files the current run
    skipped (pre-existing files are exactly where stale tokens hide).
    """
    skipped = skipped or set()
    print("\nVerification:")
    failures: list[str] = []

    for rel in REQUIRED_DIRS:
        ok = (target / rel).is_dir()
        print(f"  [{'ok' if ok else 'MISSING'}] dir  {rel}")
        if not ok:
            failures.append(f"missing directory: {rel}")

    for _, dest_rel in FILE_MAP:
        ok = (target / dest_rel).is_file()
        print(f"  [{'ok' if ok else 'MISSING'}] file {dest_rel}")
        if not ok:
            failures.append(f"missing file: {dest_rel}")

    gitignore_path = target / ".gitignore"
    gitignore_ok = gitignore_path.is_file() and \
        GITIGNORE_START in gitignore_path.read_text(encoding="utf-8")
    print(f"  [{'ok' if gitignore_ok else 'MISSING'}] file .gitignore (with bootstrap block)")
    if not gitignore_ok:
        failures.append("missing or unmarked .gitignore")

    claude_path = target / "CLAUDE.md"
    if claude_path.is_file():
        line_count = len(claude_path.read_text(encoding="utf-8").splitlines())
        print(f"  CLAUDE.md line count: {line_count}")
        if line_count > CLAUDE_LINE_WARN:
            print(f"  WARNING: CLAUDE.md is {line_count} lines (>{CLAUDE_LINE_WARN}). "
                  "Move detail into docs/ and keep CLAUDE.md short.")

    # Leftover fill-in token scan over every generated file.
    token_files: dict[str, list[str]] = {}
    for _, dest_rel in FILE_MAP:
        path = target / dest_rel
        if path.is_file():
            tokens = find_tokens(path.read_text(encoding="utf-8"))
            if tokens:
                token_files[dest_rel] = tokens
    if token_files:
        total = sum(len(t) for t in token_files.values())
        if allow_placeholders:
            print(f"\n  WARNING: {total} distinct unfilled template token(s) in "
                  f"{len(token_files)} file(s) — allowed by --allow-placeholders "
                  "(expected during the Step 2 setup run; Step 3 must fill them):")
            for dest_rel, tokens in token_files.items():
                origin = " (pre-existing/skipped file)" if dest_rel in skipped else ""
                print(f"    - {dest_rel}{origin}: {len(tokens)} token(s): "
                      + ", ".join(tokens))
        else:
            print("\n  Unfilled template tokens found:")
            for dest_rel, tokens in token_files.items():
                origin = " (pre-existing/skipped file)" if dest_rel in skipped else ""
                print(f"    - {dest_rel}{origin}: {len(tokens)} token(s): "
                      + ", ".join(tokens))
                failures.append(
                    f"unfilled template tokens in {dest_rel}"
                    f"{' (pre-existing/skipped file)' if dest_rel in skipped else ''}: "
                    + ", ".join(tokens))

    # Content checks — existence and token-freeness alone don't prove the
    # docs were actually filled in with decisions. In a setup run with
    # --allow-placeholders these are warnings only: Step 3 (fill-in) and
    # Step 4 (skill installs) have not happened yet at that point.
    content_failures: list[str] = []

    prd_path = target / "docs" / "PRD.md"
    if prd_path.is_file():
        prd_ok = prd_out_of_scope_ok(prd_path.read_text(encoding="utf-8"))
        print(f"  [{'ok' if prd_ok else 'FAIL'}] docs/PRD.md out-of-scope list "
              "is non-empty")
        if not prd_ok:
            content_failures.append(
                "docs/PRD.md: the out-of-scope list is empty — the interview "
                "rule is that it must not be blank (record at least one "
                "explicit non-goal)")

    setup_path = target / "docs" / "SETUP.md"
    if setup_path.is_file():
        setup_problems = setup_record_problems(setup_path.read_text(encoding="utf-8"))
        print(f"  [{'ok' if not setup_problems else 'FAIL'}] docs/SETUP.md: every "
              "installed skill has its pinned SHA + read-summary (or none installed)")
        for problem in setup_problems:
            content_failures.append(f"docs/SETUP.md: {problem}")

    if content_failures:
        if allow_placeholders:
            print("\n  WARNING: content checks not yet satisfied "
                  "(expected during the Step 2 setup run; Steps 3–4 "
                  "complete them):")
            for failure in content_failures:
                print(f"    - {failure}")
        else:
            failures.extend(content_failures)

    if failures:
        print("\nVerification FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nVerification passed.")
    return 0


def run_verify(target: Path, allow_placeholders: bool) -> int:
    if not target.is_dir():
        print(f"ERROR: --verify target does not exist: {target}", file=sys.stderr)
        return 2
    print(f"project-bootstrap --verify -> {target}")
    return verify_target(target, allow_placeholders)


def run_setup(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()

    if not target.exists():
        if not args.create_target:
            print(f"ERROR: target directory does not exist: {target}\n"
                  "Create it first (e.g. `git init` your project there), or pass "
                  "--create-target if this path is really where the new project "
                  "should be created.", file=sys.stderr)
            return 2
        target.mkdir(parents=True, exist_ok=True)
    elif not target.is_dir():
        print(f"ERROR: target exists but is not a directory: {target}", file=sys.stderr)
        return 2

    if not (target / ".git").exists():
        print(f"WARNING: {target} is not a git repository. Files will be set up "
              "anyway, but the commit step (SKILL.md Step 7) will need "
              "`git init` first.")

    date = datetime.date.today().isoformat()
    values = {
        "PROJECT_NAME": args.project_name,
        "PROJECT_TYPE": args.project_type,
        "PURPOSE": args.purpose,
        "DATE": date,
    }

    report: dict[str, list[str]] = {
        "created": [], "overwritten": [], "skipped": [], "backed_up": []}

    # 1. Directories
    for rel in REQUIRED_DIRS:
        (target / rel).mkdir(parents=True, exist_ok=True)
    # Keep the otherwise-empty skills dir visible to git.
    gitkeep = target / ".claude" / "skills" / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")
        report["created"].append(".claude/skills/.gitkeep")

    # 2. Templated files
    for template_rel, dest_rel in FILE_MAP:
        template_path = TEMPLATES / template_rel
        if not template_path.is_file():
            print(f"ERROR: missing template: {template_path}", file=sys.stderr)
            return 2
        dest = target / dest_rel
        existed = dest.exists()
        if existed and not args.force:
            report["skipped"].append(dest_rel)
            continue
        if existed:
            backup_file(dest, report)
        dest.parent.mkdir(parents=True, exist_ok=True)
        rendered = render(template_path.read_text(encoding="utf-8"), values)
        dest.write_text(rendered, encoding="utf-8")
        report["overwritten" if existed else "created"].append(dest_rel)

    # 3. .gitignore
    try:
        handle_gitignore(target, args.project_type, date, args.force, report)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except BootstrapError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    # Summary
    print(f"project-bootstrap: {args.project_name} ({args.project_type}) -> {target}")
    print(f"Date: {date}")
    for label in ("created", "overwritten", "skipped", "backed_up"):
        items = report[label]
        print(f"\n{label.capitalize().replace('_', ' ')} ({len(items)}):")
        for item in items:
            print(f"  - {item}")
        if not items:
            print("  (none)")

    skipped_dests = {item for item in report["skipped"]}
    return verify_target(target, args.allow_placeholders, skipped=skipped_dests)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic initial file setup for a fresh project repo.")
    parser.add_argument("--verify", action="store_true",
                        help="Verify an already-bootstrapped target and exit; "
                             "creates/modifies nothing. --project-name/--type/"
                             "--purpose are not required in this mode.")
    parser.add_argument("--project-name", help="Project name (setup mode)")
    parser.add_argument("--type", choices=PROJECT_TYPES, dest="project_type",
                        help="Project type (setup mode)")
    parser.add_argument("--purpose", help="One-line project purpose (setup mode)")
    parser.add_argument("--target", default=".",
                        help="Target project directory (default: current directory)")
    parser.add_argument("--create-target", action="store_true",
                        help="Create the target directory if it does not exist "
                             "(by default a missing target is an error)")
    parser.add_argument("--allow-placeholders", action="store_true",
                        help="Pass verification despite leftover {{...}} fill-in "
                             "tokens (expected for the Step 2 setup run; Step 3 "
                             "fills them and Step 6 verifies without this flag)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing files instead of skipping them; "
                             "each overwritten file is backed up first to "
                             "<filename>.pre-bootstrap.bak")
    args = parser.parse_args(argv)

    target = Path(args.target).expanduser().resolve()

    if args.verify:
        if args.allow_placeholders:
            print("ERROR: --allow-placeholders is not allowed with --verify: "
                  "verification must run against filled files "
                  "(see SKILL.md Step 6).", file=sys.stderr)
            return 2
        return run_verify(target, args.allow_placeholders)

    missing = [flag for flag, value in (
        ("--project-name", args.project_name),
        ("--type", args.project_type),
        ("--purpose", args.purpose),
    ) if not value]
    if missing:
        parser.error("setup mode requires: " + ", ".join(missing) +
                     " (or use --verify to only check an existing target)")

    return run_setup(args)


if __name__ == "__main__":
    sys.exit(main())
