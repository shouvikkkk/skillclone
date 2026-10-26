"""Tests for skillclone.cluster."""

import unittest

from skillclone.cluster import UnionFind, build_clusters, verbatim_pairs
from skillclone.discover import SkillFile


def _skill(path, sha):
    return SkillFile(path=path, size=10, mtime=1000.0, sha256=sha)


class TestUnionFind(unittest.TestCase):
    def test_transitive_merge(self):
        union_find = UnionFind(4)
        union_find.union(0, 1)
        union_find.union(1, 2)
        self.assertEqual(union_find.find(0), union_find.find(2))
        self.assertNotEqual(union_find.find(0), union_find.find(3))


class TestVerbatimPairs(unittest.TestCase):
    def test_identical_hash_pairs(self):
        skills = [_skill("a", "h1"), _skill("b", "h1"), _skill("c", "h2")]
        self.assertEqual(verbatim_pairs(skills), [(0, 1)])

    def test_empty_hash_ignored(self):
        skills = [_skill("a", ""), _skill("b", "")]
        self.assertEqual(verbatim_pairs(skills), [])


class TestBuildClusters(unittest.TestCase):
    def test_pairs_form_one_cluster(self):
        self.assertEqual(build_clusters(3, [(0, 1), (1, 2)]), [[0, 1, 2]])

    def test_unpaired_skills_are_singletons(self):
        self.assertEqual(build_clusters(3, [(0, 1)]), [[0, 1], [2]])

    def test_no_pairs_all_singletons(self):
        self.assertEqual(build_clusters(2, []), [[0], [1]])


if __name__ == "__main__":
    unittest.main()
