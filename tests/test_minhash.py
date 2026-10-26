"""Tests for skillclone.minhash."""

import unittest

from skillclone.minhash import (
    candidate_pairs,
    exact_jaccard,
    lsh_candidates,
    minhash_signature,
    word_shingles,
)

BASE = (
    "alpha bravo charlie delta echo foxtrot golf hotel india juliet "
    "kilo lima mike november oscar papa quebec romeo sierra tango"
)


class TestShingles(unittest.TestCase):
    def test_shingle_count(self):
        words = BASE.split()
        self.assertEqual(len(word_shingles(BASE)), len(words) - 5 + 1)

    def test_case_sensitive_shingles(self):
        lower = word_shingles("alpha bravo charlie delta echo foxtrot")
        upper = word_shingles("ALPHA bravo charlie delta echo foxtrot")
        self.assertNotEqual(lower, upper)

    def test_too_short_text_has_no_shingles(self):
        self.assertEqual(word_shingles("one two three"), set())


class TestJaccard(unittest.TestCase):
    def test_known_value(self):
        self.assertAlmostEqual(exact_jaccard({"a", "b", "c"}, {"b", "c", "d"}), 0.5)

    def test_identical_sets(self):
        self.assertEqual(exact_jaccard({"a", "b"}, {"a", "b"}), 1.0)

    def test_disjoint_sets(self):
        self.assertEqual(exact_jaccard({"a"}, {"b"}), 0.0)

    def test_both_empty(self):
        self.assertEqual(exact_jaccard(set(), set()), 1.0)


class TestMinHash(unittest.TestCase):
    def test_signature_is_deterministic(self):
        shingles = word_shingles(BASE)
        self.assertEqual(minhash_signature(shingles), minhash_signature(shingles))

    def test_signature_length(self):
        self.assertEqual(len(minhash_signature(word_shingles(BASE))), 128)

    def test_lsh_finds_near_duplicate(self):
        near = BASE + " uniform victor whisky"
        sigs = {
            "a": minhash_signature(word_shingles(BASE)),
            "b": minhash_signature(word_shingles(near)),
        }
        self.assertIn(("a", "b"), lsh_candidates(sigs))

    def test_candidate_pairs_verifies_exactly(self):
        near = BASE + " uniform victor whisky"
        unrelated = (
            "zebra yak xray wolf vulture uranium tornado syrup rocket "
            "quilt panda otter nutmeg mango lemon kiwi jelly igloo"
        )
        sets = {
            "base": word_shingles(BASE),
            "near": word_shingles(near),
            "other": word_shingles(unrelated),
        }
        pairs = candidate_pairs(sets, 0.80)
        keys = {(a, b) for a, b, _ in pairs}
        self.assertIn(("base", "near"), keys)
        self.assertNotIn(("base", "other"), keys)
        self.assertNotIn(("near", "other"), keys)

    def test_reported_similarity_is_exact(self):
        near = BASE + " uniform victor whisky"
        sets = {"base": word_shingles(BASE), "near": word_shingles(near)}
        pairs = candidate_pairs(sets, 0.80)
        self.assertEqual(len(pairs), 1)
        self.assertAlmostEqual(
            pairs[0][2], exact_jaccard(sets["base"], sets["near"])
        )


if __name__ == "__main__":
    unittest.main()
