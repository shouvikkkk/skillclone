"""Tests for skillclone.normalize."""

import unittest

from skillclone.normalize import normalize_text


class TestNormalize(unittest.TestCase):
    def test_crlf_becomes_lf(self):
        self.assertEqual(normalize_text("a\r\nb\r\nc"), "a\nb\nc")

    def test_lone_cr_becomes_lf(self):
        self.assertEqual(normalize_text("a\rb"), "a\nb")

    def test_trailing_whitespace_stripped_per_line(self):
        self.assertEqual(normalize_text("a   \nb\t \nc"), "a\nb\nc")

    def test_trailing_blank_lines_dropped(self):
        self.assertEqual(normalize_text("a\nb\n\n\n"), "a\nb")

    def test_derived_from_line_stripped(self):
        text = "title\nderived-from: some/skill\nbody"
        self.assertEqual(normalize_text(text), "title\nbody")

    def test_derived_from_hash_line_stripped(self):
        text = "title\nderived-from-hash: abc123\nbody"
        self.assertEqual(normalize_text(text), "title\nbody")

    def test_provenance_copy_matches_parent(self):
        parent = "title line here\nbody line here\n"
        copy = "title line here\nderived-from: upstream/repo\nbody line here\n"
        self.assertEqual(normalize_text(parent), normalize_text(copy))

    def test_case_is_preserved(self):
        self.assertEqual(normalize_text("README --Flag"), "README --Flag")

    def test_empty_text(self):
        self.assertEqual(normalize_text(""), "")

    def test_prose_mentioning_derived_from_is_kept(self):
        text = "This skill is derived-from an old idea"
        self.assertEqual(normalize_text(text), text)


if __name__ == "__main__":
    unittest.main()
