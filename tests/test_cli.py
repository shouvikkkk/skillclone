"""End-to-end tests for skillclone.cli over synthetic SKILL.md corpora."""

import contextlib
import io
import json
import os
import tempfile
import unittest

from skillclone.cli import main

BASE_LINES = [
    "# Example Skill for Testing Clone Detection Thoroughly",
    "This skill teaches the assistant how to review code changes carefully every single day",
    "First read the entire change before commenting on any individual line of code",
    "Second check for security issues such as injection unsafe deserialization and secrets",
    "Third verify that tests cover the new behavior and edge cases fully always",
    "Fourth suggest concrete improvements instead of vague praise or generic criticism here",
    "Fifth keep the review focused short actionable and respectful toward the original author",
    "When uncertain about a pattern ask a clarifying question before making strong claims",
    "Avoid repeating the same feedback across multiple files in the same review session",
    "Summarize findings at the end with severity labels and suggested next steps clearly",
    "Never approve a change that leaks credentials exposes private data or breaks compatibility",
    "Follow the repository style guide and existing conventions unless there is good reason",
]
BASE = "\n".join(BASE_LINES) + "\n"

UNRELATED = "\n".join(
    "Cooking line number %d about saffron risotto simmered slowly with butter parmesan broth herbs" % i
    for i in range(12)
) + "\n"

OWN_LINE = "Local teams add their own checklist item here for internal review purposes only today"


def write_skill(root, name, content, mtime):
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    skill_path = os.path.join(path, "SKILL.md")
    with open(skill_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(content)
    os.utime(skill_path, (mtime, mtime))
    return skill_path


def run_cli(args):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(args)
    return code, buffer.getvalue()


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()


class TestCli(CliTestCase):
    def test_verbatim_copies_exit_zero_and_current(self):
        write_skill(self.root, "a", BASE, 1000)
        write_skill(self.root, "b", BASE, 2000)
        code, output = run_cli(["scan", self.root])
        self.assertEqual(code, 0)
        self.assertIn("CURRENT", output)

    def test_crlf_and_trailing_whitespace_variant_matches(self):
        crlf = BASE.replace("\n", "\r\n").replace("skill", "skill   ")
        write_skill(self.root, "a", BASE, 1000)
        write_skill(self.root, "b", crlf, 2000)
        code, output = run_cli(["scan", self.root])
        self.assertEqual(code, 0)
        self.assertIn("CURRENT", output)

    def test_provenance_key_copy_matches_parent(self):
        copy = BASE + "derived-from: upstream/example-skill\n"
        write_skill(self.root, "a", BASE, 1000)
        write_skill(self.root, "b", copy, 2000)
        code, output = run_cli(["scan", self.root])
        self.assertEqual(code, 0)
        self.assertIn("CURRENT", output)

    def test_stale_member_exits_two(self):
        stale = "\n".join(BASE_LINES[:-2]) + "\n"
        write_skill(self.root, "old", stale, 1000)
        write_skill(self.root, "new", BASE, 2000)
        code, output = run_cli(["scan", self.root])
        self.assertEqual(code, 2)
        self.assertIn("STALE", output)

    def test_diverged_member_exits_zero(self):
        diverged = "\n".join(BASE_LINES[:-1] + [OWN_LINE]) + "\n"
        write_skill(self.root, "old", diverged, 1000)
        write_skill(self.root, "new", BASE, 2000)
        code, output = run_cli(["scan", self.root])
        self.assertEqual(code, 0)
        self.assertIn("DIVERGED", output)

    def test_singleton_is_unique(self):
        write_skill(self.root, "only", BASE, 1000)
        code, output = run_cli(["scan", self.root])
        self.assertEqual(code, 0)
        self.assertIn("UNIQUE", output)

    def test_empty_dir_exits_zero(self):
        code, output = run_cli(["scan", self.root])
        self.assertEqual(code, 0)
        self.assertIn("0 skill(s)", output)

    def test_tiny_skill_is_skipped(self):
        write_skill(self.root, "tiny", "tiny skill words only here\n", 1000)
        code, output = run_cli(["scan", self.root])
        self.assertEqual(code, 0)
        self.assertIn("Skipped", output)

    def test_unrelated_skills_stay_separate(self):
        write_skill(self.root, "a", BASE, 1000)
        write_skill(self.root, "b", UNRELATED, 2000)
        code, output = run_cli(["scan", self.root])
        self.assertEqual(code, 0)
        self.assertEqual(output.count("UNIQUE"), 2)

    def test_json_report_shape(self):
        stale = "\n".join(BASE_LINES[:-2]) + "\n"
        write_skill(self.root, "old", stale, 1000)
        write_skill(self.root, "new", BASE, 2000)
        code, output = run_cli(["scan", self.root, "--format", "json"])
        self.assertEqual(code, 2)
        data = json.loads(output)
        self.assertEqual(data["total_skills"], 2)
        self.assertEqual(data["stale_count"], 1)
        self.assertEqual(len(data["clusters"]), 1)
        member = data["clusters"][0]["members"][0]
        self.assertIn("missing_lines_sample", member)
        self.assertLessEqual(len(member["missing_lines_sample"]), 10)

    def test_high_threshold_breaks_the_pair(self):
        stale = "\n".join(BASE_LINES[:-2]) + "\n"
        write_skill(self.root, "old", stale, 1000)
        write_skill(self.root, "new", BASE, 2000)
        code, output = run_cli(["scan", self.root, "--threshold", "0.99"])
        self.assertEqual(code, 0)
        self.assertIn("UNIQUE", output)

    def test_version_flag(self):
        code, output = run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("skillclone", output)

    def test_no_command_is_usage_error(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main([])
        self.assertEqual(code, 1)

    def test_nonexistent_root_is_error(self):
        code, _ = run_cli(["scan", "/definitely/not/a/real/path/skillclone"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
