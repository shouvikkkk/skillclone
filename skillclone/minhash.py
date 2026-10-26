"""Word shingles, MinHash signatures, and LSH candidate generation.

Design choices, stated plainly:

* Shingles are built from RAW words (case preserved). Agent skills are
  full of code, commands, and identifiers where case changes meaning
  (``README`` is not ``readme``, ``--Flag`` is not ``--flag``), so
  lowercasing would merge genuinely different content.
* MinHash is only a pre-filter. LSH banding proposes candidate pairs
  cheaply, but every candidate is then verified with the EXACT Jaccard
  similarity over the full shingle sets. A pair is reported only if its
  exact similarity clears the threshold, so the probabilistic step can
  miss a pair (false negative) but can never invent one (no false
  positive from MinHash itself).
* All hashes use hashlib with fixed seeds, so signatures are
  deterministic across runs and machines.
"""

from __future__ import annotations

import hashlib
import itertools

SHINGLE_SIZE = 5
NUM_PERMUTATIONS = 128
NUM_BANDS = 32
ROWS_PER_BAND = NUM_PERMUTATIONS // NUM_BANDS  # 4


def word_shingles(text: str, size: int = SHINGLE_SIZE) -> set:
    """Return the set of ``size``-word shingles of ``text``.

    Words are maximal runs of non-whitespace characters. Texts shorter
    than one shingle yield an empty set; the scan pipeline skips such
    tiny skills before this point, so this only matters for direct
    library use.
    """
    words = text.split()
    if len(words) < size:
        return set()
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def _perm_hash(permutation: int, shingle: tuple) -> int:
    data = f"{permutation}:{'|'.join(shingle)}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "big")


def minhash_signature(shingles: set, num_perm: int = NUM_PERMUTATIONS) -> tuple:
    """Return a deterministic MinHash signature for a shingle set.

    For each of ``num_perm`` pseudo-random permutations (realised as a
    seeded hash), the signature keeps the minimum hash value over the
    set. Similar sets agree on many signature positions, which is what
    LSH banding exploits.
    """
    if not shingles:
        return tuple([2 ** 64 - 1] * num_perm)
    return tuple(
        min(_perm_hash(p, shingle) for shingle in shingles)
        for p in range(num_perm)
    )


def lsh_candidates(signatures: dict, num_bands: int = NUM_BANDS) -> set:
    """Return candidate pairs that share at least one LSH band.

    ``signatures`` maps an arbitrary key to its signature tuple. Each
    signature is split into ``num_bands`` bands of equal rows; two keys
    sharing any band's exact values become a candidate pair.
    """
    if not signatures:
        return set()
    sig_len = len(next(iter(signatures.values())))
    rows = sig_len // num_bands
    buckets: dict = {}
    for key, sig in signatures.items():
        for band in range(num_bands):
            band_values = sig[band * rows:(band + 1) * rows]
            buckets.setdefault((band, band_values), []).append(key)
    pairs = set()
    for members in buckets.values():
        for first, second in itertools.combinations(sorted(members), 2):
            pairs.add((first, second))
    return pairs


def exact_jaccard(first: set, second: set) -> float:
    """Exact Jaccard similarity of two shingle sets."""
    if not first and not second:
        return 1.0
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def candidate_pairs(shingle_sets: dict, threshold: float) -> list:
    """Return ``(key_a, key_b, similarity)`` for pairs at/above threshold.

    LSH proposes candidates; each is verified with exact Jaccard, and
    only verified pairs are returned, sorted for deterministic output.
    """
    signatures = {
        key: minhash_signature(shingles)
        for key, shingles in shingle_sets.items()
    }
    verified = []
    for first, second in sorted(lsh_candidates(signatures)):
        similarity = exact_jaccard(shingle_sets[first], shingle_sets[second])
        if similarity >= threshold:
            verified.append((first, second, similarity))
    return verified
