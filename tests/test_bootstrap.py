#!/usr/bin/env python3
"""Tests for scripts/bootstrap.py — Python stdlib only (unittest + tempfile).

Run from the repo root:
    python3 -m unittest discover -s tests -v
    # or
    python3 tests/test_bootstrap.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "bootstrap.py"

TOKEN_RE = re.compile(r"\{\{[^}]+\}\}")

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
    """Replace every leftover {{...}} token in generated .md files."""
    for rel in EXPECTED_FILES:
        path = root / rel
        if path.suffix == ".md" and path.is_file():
            path.write_text(TOKEN_RE.sub("FILLED", path.read_text(encoding="utf-8")),
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


if __name__ == "__main__":
    unittest.main()
