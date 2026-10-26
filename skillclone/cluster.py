"""Group skills into clone clusters with union-find.

Two kinds of edge join a cluster:

* a similarity edge: a pair whose exact Jaccard similarity cleared the
  threshold (computed by :mod:`skillclone.minhash`);
* a verbatim edge: two skills whose SHA-256 of normalized text is
  identical. This is a belt-and-braces check -- verbatim copies already
  score similarity 1.0 -- but it makes the verbatim relationship
  explicit even if the similarity step is ever bypassed.
"""

from __future__ import annotations


class UnionFind:
    """Classic union-find with path compression and union by rank."""

    def __init__(self, count: int):
        self.parent = list(range(count))
        self.rank = [0] * count

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        root_first, root_second = self.find(first), self.find(second)
        if root_first == root_second:
            return
        if self.rank[root_first] < self.rank[root_second]:
            root_first, root_second = root_second, root_first
        self.parent[root_second] = root_first
        if self.rank[root_first] == self.rank[root_second]:
            self.rank[root_first] += 1


def verbatim_pairs(skills) -> list:
    """Return index pairs whose normalized SHA-256 hashes are identical."""
    by_hash: dict = {}
    for index, skill in enumerate(skills):
        if skill.sha256:
            by_hash.setdefault(skill.sha256, []).append(index)
    pairs = []
    for indices in by_hash.values():
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                pairs.append((indices[i], indices[j]))
    return sorted(pairs)


def build_clusters(count: int, pairs) -> list:
    """Return groups of indices, one group per cluster.

    Every group has at least one member; singletons are groups of one,
    so callers never need a separate "unclustered" path. Groups are
    sorted by their members' indices for deterministic output.
    """
    union_find = UnionFind(count)
    for first, second in pairs:
        union_find.union(first, second)
    groups: dict = {}
    for index in range(count):
        groups.setdefault(union_find.find(index), []).append(index)
    return sorted(groups.values(), key=lambda group: group[0])
