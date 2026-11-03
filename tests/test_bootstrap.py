#!/usr/bin/env python3
"""Tests for scripts/bootstrap.py — Python stdlib only (unittest + tempfile).

Run from the repo root:
    python3 -m unittest discover -s tests -v
    # or
    python3 tests/test_bootstrap.py
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "bootstrap.py"

_spec = importlib.util.spec_from_file_location("bootstrap_under_test", SCRIPT)
bootstrap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bootstrap)  # type: ignore[union-attr]
# Fills use the script's own notion of a token (known template names), so
# prose like {{...}} and other engines' examples survive a fill untouched.
FILL_TEXT = "Not in v1: a concrete example non-goal."

NO_SKILLS_SENTENCE = "No stack skills installed for this project."

EXPECTED_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "docs/PRD.md",
    "docs/ROADMAP.md",
    "docs/CONTEXT.md",
    "docs/STATE.md",
    "docs/SETUP.md",
    "docs/adr/0000-template.md",
    "docs/plans/PLAN.md",
    ".claude/agents/reviewer.md",
    ".gitignore",
]
EXPECTED_DIRS = ["docs", "docs/adr", "docs/plans", ".claude/agents", ".claude/skills"]


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=60)


def setup_args(target: Path, *extra: str, ptype: str = "ios",
               purpose: str = "Personal finance tracker") -> list[str]:
    return ["--project-name", "Ledgerly", "--type", ptype,
            "--purpose", purpose, "--target", str(target), *extra]


def snapshot_tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def fill_all_tokens(root: Path) -> None:
    """Fill generated .md files the way SKILL.md Step 3 does: replace only
    genuine bootstrap tokens (uppercase-start pattern), leaving prose —
    including any token-shaped prose — untouched.

    Fixture choice for the SETUP content check: after the generic token
    fill, SETUP.md's skills table contains no real 40-char SHA, so the
    fixture writes the documented none-sentence on its own line — the
    same thing an agent does for a project with no stack skills (see
    templates/docs/SETUP.md.tmpl). That is what lets --verify's SETUP
    check pass on the standard fixture.
    """
    for rel in EXPECTED_FILES:
        path = root / rel
        if path.suffix == ".md" and path.is_file():
            text = path.read_text(encoding="utf-8")
            text = bootstrap.BRACE_RE.sub(
                lambda m: FILL_TEXT if bootstrap._is_token(m.group(0)) else m.group(0),
                text)
            path.write_text(text, encoding="utf-8")
    setup = root / "docs" / "SETUP.md"
    if setup.is_file():
        text = setup.read_text(encoding="utf-8")
        # Standalone-line check (not substring): the template's own
        # instructions mention the sentence mid-line, which must not
        # count — the script's check requires it on a line of its own.
        if not any(line.strip() == NO_SKILLS_SENTENCE
                   for line in text.splitlines()):
            # Do what the template tells an agent to do: delete the table
            # rows, then state the sentence on its own line.
            kept = []
            in_table = False
            for line in text.splitlines():
                if line.lstrip().startswith("|") and "pinned sha" in line.lower():
                    in_table = True
                if in_table and line.lstrip().startswith("|"):
                    continue
                in_table = False
                kept.append(line)
            setup.write_text("\n".join(kept) + "\n\n" + NO_SKILLS_SENTENCE + "\n",
                             encoding="utf-8")


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.target = self.tmp / "proj"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # (a) fresh ios run creates all files and passes with --allow-placeholders
    def test_a_fresh_ios_run_with_allow_placeholders(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for rel in EXPECTED_FILES:
            self.assertTrue((self.target / rel).is_file(), f"missing {rel}")
        for rel in EXPECTED_DIRS:
            self.assertTrue((self.target / rel).is_dir(), f"missing dir {rel}")
        self.assertIn("--allow-placeholders", result.stdout)
        self.assertIn("Verification passed", result.stdout)

    # (b) fresh run WITHOUT --allow-placeholders fails verification (tokens)
    def test_b_fresh_run_without_allow_placeholders_fails(self):
        result = run_script(*setup_args(self.target, "--create-target"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Verification FAILED", result.stdout)
        self.assertIn("unfilled template tokens", result.stdout)

    # (c) after replacing tokens, --verify passes and modifies nothing
    def test_c_verify_passes_after_tokens_filled(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fill_all_tokens(self.target)
        before = snapshot_tree(self.target)
        result = run_script("--verify", "--target", str(self.target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Verification passed", result.stdout)
        self.assertEqual(before, snapshot_tree(self.target),
                         "--verify must not create/modify anything")

    # (d) idempotent second run skips and changes nothing
    def test_d_idempotent_second_run(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        before = snapshot_tree(self.target)
        result = run_script(*setup_args(self.target, "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skipped", result.stdout)
        self.assertEqual(before, snapshot_tree(self.target))

    # (e) --force creates .pre-bootstrap.bak backups and restores template content
    def test_e_force_creates_backups(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        claude = self.target / "CLAUDE.md"
        claude.write_text(claude.read_text(encoding="utf-8") + "\nMARKER-LINE\n",
                          encoding="utf-8")
        state = self.target / "docs" / "STATE.md"
        state.write_text(state.read_text(encoding="utf-8") + "\nUSER STATE\n",
                         encoding="utf-8")
        result = run_script(*setup_args(self.target, "--force",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("MARKER-LINE", claude.read_text(encoding="utf-8"))
        claude_bak = self.target / "CLAUDE.md.pre-bootstrap.bak"
        state_bak = self.target / "docs" / "STATE.md.pre-bootstrap.bak"
        self.assertTrue(claude_bak.is_file())
        self.assertIn("MARKER-LINE", claude_bak.read_text(encoding="utf-8"))
        self.assertTrue(state_bak.is_file())
        self.assertIn("USER STATE", state_bak.read_text(encoding="utf-8"))

    # (f) a purpose containing "{{DATE}}" is NOT re-expanded
    def test_f_purpose_with_token_text_not_reexpanded(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders",
                                        purpose="Launch on {{DATE}} please"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        text = (self.target / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Launch on {{DATE}} please", text)

    # (g) missing target: errors without --create-target, succeeds with it
    def test_g_missing_target_guard(self):
        missing = self.tmp / "does-not-exist"
        result = run_script(*setup_args(missing))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(missing.exists(),
                         "missing target must not be silently created")
        result = run_script(*setup_args(missing, "--create-target",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((missing / "CLAUDE.md").is_file())

    # (h) hand-mangled .gitignore (END before START): clean error, file unchanged
    def test_h_mangled_gitignore(self):
        self.target.mkdir(parents=True)
        gitignore = self.target / ".gitignore"
        mangled = ("# <<< project-bootstrap <<<\n"
                   "my-entry/\n"
                   "# >>> project-bootstrap (generated — edits inside this "
                   "block are replaced on --force) >>>\n")
        gitignore.write_text(mangled, encoding="utf-8")
        result = run_script(*setup_args(self.target, "--allow-placeholders"))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("mangled", result.stderr)
        self.assertEqual(gitignore.read_text(encoding="utf-8"), mangled)

    # (i) pre-existing custom .gitignore entry is preserved
    def test_i_custom_gitignore_entry_preserved(self):
        self.target.mkdir(parents=True)
        (self.target / ".gitignore").write_text("my-custom-entry/\n",
                                                encoding="utf-8")
        result = run_script(*setup_args(self.target, "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        text = (self.target / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("my-custom-entry/", text)
        self.assertIn("# >>> project-bootstrap", text)

    # (j) bad --type is rejected
    def test_j_bad_type_rejected(self):
        result = run_script("--project-name", "X", "--type", "rust",
                            "--purpose", "Y", "--target", str(self.target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    # (k) regression: fill the way Step 3 does (real templates, prose
    # survives), then --verify passes; Jinja/prose examples don't trip it
    def test_k_regression_fill_like_step3_and_verify_passes(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders", ptype="web"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fill_all_tokens(self.target)
        reviewer = (self.target / ".claude" / "agents" / "reviewer.md") \
            .read_text(encoding="utf-8")
        # The gate paragraph's prose survived the fill (v2 bug: the helper
        # blanket-replaced it, and the old prose itself tripped the scan).
        self.assertIn("leftover double-brace template tokens", reviewer)
        # Non-bootstrap template syntax in filled docs must not be flagged.
        context = self.target / "docs" / "CONTEXT.md"
        context.write_text(context.read_text(encoding="utf-8")
                           + "\nUse {{ user.name }} in the template.\n",
                           encoding="utf-8")
        state = self.target / "docs" / "STATE.md"
        state.write_text(state.read_text(encoding="utf-8")
                         + "\nToken syntax looks like {{...}} in prose.\n",
                         encoding="utf-8")
        result = run_script("--verify", "--target", str(self.target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Verification passed", result.stdout)

    # (l) --verify refuses --allow-placeholders
    def test_l_verify_rejects_allow_placeholders(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = run_script("--verify", "--target", str(self.target),
                            "--allow-placeholders")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--allow-placeholders is not allowed with --verify",
                      result.stderr)

    # (m) repeated --force runs never overwrite an earlier backup
    def test_m_force_backups_never_overwritten(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        claude = self.target / "CLAUDE.md"
        claude.write_text(claude.read_text(encoding="utf-8") + "\nVERSION-ONE\n",
                          encoding="utf-8")
        result = run_script(*setup_args(self.target, "--force",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        claude.write_text(claude.read_text(encoding="utf-8") + "\nVERSION-TWO\n",
                          encoding="utf-8")
        result = run_script(*setup_args(self.target, "--force",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        first = self.target / "CLAUDE.md.pre-bootstrap.bak"
        second = self.target / "CLAUDE.md.pre-bootstrap.bak.1"
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())
        self.assertIn("VERSION-ONE", first.read_text(encoding="utf-8"))
        self.assertNotIn("VERSION-TWO", first.read_text(encoding="utf-8"))
        self.assertIn("VERSION-TWO", second.read_text(encoding="utf-8"))

    # (n) appending the block to a user's .gitignore creates no backup
    def test_n_gitignore_append_creates_no_backup(self):
        self.target.mkdir(parents=True)
        (self.target / ".gitignore").write_text("my-custom-entry/\n",
                                                encoding="utf-8")
        result = run_script(*setup_args(self.target, "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        backups = [p for p in self.target.rglob("*.pre-bootstrap.bak*")]
        self.assertEqual(backups, [])

    # (o) PRD out-of-scope list emptied -> --verify fails the content check
    def test_o_prd_out_of_scope_emptied_fails_verify(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fill_all_tokens(self.target)
        prd = self.target / "docs" / "PRD.md"
        lines = prd.read_text(encoding="utf-8").splitlines()
        in_section = False
        for i, line in enumerate(lines):
            if line.startswith("## "):
                in_section = "out of scope" in line.lower()
                continue
            if in_section and line.lstrip().startswith("- "):
                lines[i] = "- TODO"
        prd.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = run_script("--verify", "--target", str(self.target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("out-of-scope list is empty", result.stdout)

    # (p) SETUP.md with neither a pinned SHA nor the none-sentence fails
    def test_p_setup_without_sha_or_sentence_fails_verify(self):
        result = run_script(*setup_args(self.target, "--create-target",
                                        "--allow-placeholders"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fill_all_tokens(self.target)
        # Sanity: the filled fixture passes (none-sentence present).
        result = run_script("--verify", "--target", str(self.target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        setup = self.target / "docs" / "SETUP.md"
        text = setup.read_text(encoding="utf-8")
        setup.write_text(text.replace(NO_SKILLS_SENTENCE, "Skills: TBD"),
                         encoding="utf-8")
        result = run_script("--verify", "--target", str(self.target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no skills table", result.stdout)
        # sentence AND leftover rows contradict each other
        setup.write_text(text + "\n" + self._skills_md(
            "| A | https://example.com | main | d | s |\n"), encoding="utf-8")
        result = run_script("--verify", "--target", str(self.target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("delete the rows", result.stdout)

    # (q) hand-lowercased leftover token is still caught; foreign engines' braces are not
    def test_q_lowercase_leftover_flagged_foreign_braces_not(self):
        run_script(*setup_args(self.target, "--create-target", "--allow-placeholders"))
        fill_all_tokens(self.target)
        ctx = self.target / "docs" / "CONTEXT.md"
        ctx.write_text(ctx.read_text(encoding="utf-8") +
                       "\nJinja: {{ user.name }} {{ count }} {{ User }} {{...}}\n",
                       encoding="utf-8")
        result = run_script("--verify", "--target", str(self.target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        ctx.write_text(ctx.read_text(encoding="utf-8") + "\nleft {{stack}} over\n",
                       encoding="utf-8")
        result = run_script("--verify", "--target", str(self.target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("{{stack}}", result.stdout)

    # (r) trivial out-of-scope items do not satisfy the check
    def test_r_trivial_out_of_scope_items_rejected(self):
        for trivial in ("n/a", "none", "TBD", "x"):
            md = "## Out of scope — explicitly\n\n- %s\n" % trivial
            self.assertFalse(bootstrap.prd_out_of_scope_ok(md), trivial)
        self.assertTrue(bootstrap.prd_out_of_scope_ok(
            "## Out of scope\n- No user accounts in v1\n"))

    def _skills_md(self, rows: str) -> str:
        return ("| Skill | Source URL | Pinned SHA | Date installed | Read-summary |\n"
                "|---|---|---|---|---|\n" + rows)

    # (s) SETUP: EVERY row needs a full SHA matching the reference pin + a summary
    def test_s_setup_every_row_checked(self):
        url = "https://github.com/twostraws/SwiftUI-Agent-Skill"
        pin = bootstrap.known_pins()[url]
        summary = "Loads SwiftUI coding rules; no network or credentials."
        good = f"| A | {url} | {pin} | 2026-11-03 | {summary} |\n"
        self.assertEqual(bootstrap.setup_record_problems(self._skills_md(good)), [])
        # second row with no SHA: the old 'any SHA anywhere' check passed this
        bad = good + f"| B | https://example.com/b | main | 2026-11-03 | {summary} |\n"
        self.assertTrue(bootstrap.setup_record_problems(self._skills_md(bad)))
        # wrong SHA for a known pinned skill
        wrong = f"| A | {url} | {'a' * 40} | 2026-11-03 | {summary} |\n"
        self.assertTrue(any("differs" in p for p in
                            bootstrap.setup_record_problems(self._skills_md(wrong))))
        # missing read-summary
        nosum = f"| A | {url} | {pin} | 2026-11-03 | ok |\n"
        self.assertTrue(any("read-summary" in p for p in
                            bootstrap.setup_record_problems(self._skills_md(nosum))))

    # (t) the pins in references/ are well-formed and cover all four skills
    def test_t_reference_pins_wellformed(self):
        self.assertEqual(len(bootstrap.known_pins()), 4)

    # (u) reviewer template: no shell, packet required, ignored by git
    def test_u_reviewer_template_contract(self):
        text = (REPO_ROOT / "templates" / "agents" / "reviewer.md.tmpl").read_text(
            encoding="utf-8")
        tools = re.search(r"^tools:\s*(.+)$", text, re.M).group(1)
        self.assertNotIn("Bash", tools)
        for needle in (".review/diff.patch", ".review/test-output.txt",
                       "self-reported"):
            self.assertIn(needle, text)
        gi = (REPO_ROOT / "templates" / "gitignore" / "generic.txt").read_text(
            encoding="utf-8")
        self.assertIn(".review/", gi)


if __name__ == "__main__":
    unittest.main()
