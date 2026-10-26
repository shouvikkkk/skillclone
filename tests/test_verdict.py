"""Tests for skillclone.verdict."""

import unittest

from skillclone.discover import SkillFile
from skillclone.verdict import verdict_for_cluster


def _skill(path, normalized, mtime):
    return SkillFile(path=path, size=len(normalized), mtime=mtime,
                     normalized=normalized, sha256=f"hash-{path}")


def _by_path(cluster):
    return {member.path: member for member in cluster.members}


class TestVerdicts(unittest.TestCase):
    def test_identical_members_are_current(self):
        newest = _skill("new", "line one\nline two", 2000.0)
        old = _skill("old", "line one\nline two", 1000.0)
        old.sha256 = newest.sha256  # identical content, identical hash
        cluster = verdict_for_cluster([old, newest])
        verdicts = _by_path(cluster)
        self.assertEqual(verdicts["old"].verdict, "CURRENT")
        self.assertEqual(verdicts["new"].verdict, "CURRENT")

    def test_all_identical_cluster_carries_upstream_note(self):
        newest = _skill("new", "line one\nline two", 2000.0)
        old = _skill("old", "line one\nline two", 1000.0)
        old.sha256 = newest.sha256
        cluster = verdict_for_cluster([old, newest])
        self.assertTrue(cluster.all_identical)
        self.assertIn("upstream", cluster.note)

    def test_stale_member_missing_lines_only(self):
        newest = _skill("new", "alpha\nbeta\ngamma\ndelta", 2000.0)
        old = _skill("old", "alpha\nbeta", 1000.0)
        verdicts = _by_path(verdict_for_cluster([old, newest]))
        member = verdicts["old"]
        self.assertEqual(member.verdict, "STALE")
        self.assertEqual(member.missing_count, 2)
        self.assertEqual(member.own_count, 0)

    def test_diverged_member_missing_and_own_lines(self):
        newest = _skill("new", "alpha\nbeta\ngamma", 2000.0)
        old = _skill("old", "alpha\nbeta\nlocal tweak", 1000.0)
        # member lacks "gamma" and adds its own line
        verdicts = _by_path(verdict_for_cluster([old, newest]))
        member = verdicts["old"]
        self.assertEqual(member.verdict, "DIVERGED")
        self.assertEqual(member.missing_count, 1)
        self.assertEqual(member.own_count, 1)

    def test_singleton_is_unique(self):
        only = _skill("only", "alpha\nbeta", 1000.0)
        cluster = verdict_for_cluster([only])
        self.assertEqual(cluster.members[0].verdict, "UNIQUE")
        self.assertEqual(cluster.newest_path, "only")

    def test_newest_is_max_mtime(self):
        a = _skill("a", "alpha\nbeta", 3000.0)
        b = _skill("b", "alpha\nbeta\ngamma", 2000.0)
        cluster = verdict_for_cluster([a, b])
        self.assertEqual(cluster.newest_path, "a")
        # b is the member compared against a: it has an own line only
        self.assertEqual(_by_path(cluster)["b"].verdict, "DIVERGED")

    def test_missing_sample_capped_at_ten(self):
        newest_lines = "\n".join(f"line {i}" for i in range(20))
        newest = _skill("new", newest_lines, 2000.0)
        old = _skill("old", "line 0\nline 1", 1000.0)
        member = _by_path(verdict_for_cluster([old, newest]))["old"]
        self.assertEqual(member.verdict, "STALE")
        self.assertEqual(member.missing_count, 18)
        self.assertLessEqual(len(member["missing_lines"]), 10) if False else self.assertLessEqual(len(member.missing_lines), 10)

    def test_newest_member_itself_is_current(self):
        newest = _skill("new", "alpha\nbeta\ngamma", 2000.0)
        old = _skill("old", "alpha", 1000.0)
        verdicts = _by_path(verdict_for_cluster([old, newest]))
        self.assertEqual(verdicts["new"].verdict, "CURRENT")


if __name__ == "__main__":
    unittest.main()
