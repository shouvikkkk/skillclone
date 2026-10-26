"""skillclone: find cloned and stale agent skills with zero metadata.

The tool works purely from file contents: it normalizes SKILL.md files,
fingerprints them with MinHash/LSH, verifies candidate pairs with exact
Jaccard similarity, groups matches into clusters, and compares every
cluster member against the newest member to judge freshness.
"""

__version__ = "0.1.0"
