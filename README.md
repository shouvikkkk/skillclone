# skillclone

Find cloned and stale agent skills with **zero metadata** — purely from
content similarity. No lockfile, no declared lineage, no network, no LLM.

## The problem

Agent skills spread by copy-paste, and copies drift apart silently. The
evidence:

- **Skill Constellations** (Seddik, UBC Okanagan, 8 October 2026,
  arXiv:2610.11169), a study of 2,193,119 skill adoptions on GitHub,
  found that half of all `SKILL.md` files are verbatim copies of another
  file, and that only 11.1% of changes to a clone group reach every copy.
  In other words: most skills are copies, and fixes almost never
  propagate to all of them.
- A 24 October 2026 dev.to post by sangaraju1988, "Your agent's skills
  have no lockfile", proposes declared `derived-from` keys so a copy can
  point at its origin — but almost no copied skill carries those keys
  today, and a reference implementation that only walks declared lineage
  cannot see the copies that never declared anything.

**The gap skillclone fills:** find clones and stale copies with zero
metadata, from content alone. If a skill *does* carry `derived-from`
keys, they are excluded during normalization, so a copy that gained
provenance metadata still matches its parent.

## Setup

Python 3.10+ and nothing else. There are no dependencies — the tool uses
only the standard library, so there is no `requirements.txt` to install.

```sh
git clone <this repo>
cd skillclone
python3 -m skillclone --version
```

## Usage

```sh
python3 -m skillclone scan <root...> [--threshold 0.8] [--format text|json] [--min-words 20]
```

- `<root...>` — one or more directories (or individual `SKILL.md` files)
  to walk recursively. Only files named exactly `SKILL.md` are collected.
- `--threshold` — minimum exact Jaccard similarity to link two skills
  (default `0.8`).
- `--format` — `text` (default) or `json`.
- `--min-words` — skills with fewer words are skipped with a note
  (default `20`); tiny files produce meaningless shingle sets.

Exit codes: `0` = no STALE skill found, `2` = at least one STALE skill,
`1` = usage or I/O error. This makes the tool usable as a check: a
non-zero exit from a scheduled scan means a human should look.

### Worked example

```sh
mkdir -p demo/new demo/old
cat > demo/new/SKILL.md <<'EOF'
# Code Review Skill
Always read the entire change before commenting on any individual line.
Check for injection flaws, leaked secrets, and unsafe deserialization first.
Verify tests cover the new behavior and the edge cases fully.
Suggest concrete improvements instead of vague praise or generic criticism.
Keep feedback focused short actionable and respectful toward the author.
Ask a clarifying question when a pattern is unclear before making claims.
Never repeat the same feedback across files in one review session.
Summarize findings at the end with severity labels and next steps.
Never approve a change that leaks credentials or breaks compatibility.
Follow the repository style guide unless there is a good reason not to.
Record decisions that affect future reviews in the review notes file.
Close the loop by confirming the author understood each requested change.
EOF
# An older copy, missing the last two lines:
head -n 11 demo/new/SKILL.md > demo/old/SKILL.md
touch -d "2025-01-01" demo/old/SKILL.md
touch -d "2026-01-01" demo/new/SKILL.md

python3 -m skillclone scan demo
```

Output (abridged):

```
skillclone report: 2 skill(s) in 1 cluster(s)
stale skills: 1

Cluster 1 (2 skill(s), newest: demo/new/SKILL.md)
  [CURRENT] demo/new/SKILL.md (missing 0 line(s), own 0 line(s))
  [STALE] demo/old/SKILL.md (missing 2 line(s), own 0 line(s))
      missing: Record decisions that affect future reviews in the review notes file.
      missing: Close the loop by confirming the author understood each requested change.
```

## How it works

1. **Discover** — walk the roots recursively, collect files named
   exactly `SKILL.md`, record path, size, and mtime. Unreadable files
   and missing roots are reported as warnings, never silent skips.
2. **Normalize** — CRLF becomes LF, trailing whitespace per line is
   stripped, trailing blank lines are dropped, and `derived-from` /
   `derived-from-hash` lines are removed (see
   `skillclone/normalize.py`).
3. **Shingle** — the normalized text becomes a set of 5-word shingles
   over raw, case-preserved words. Case is kept deliberately: skills
   contain code and commands where case changes meaning.
4. **MinHash + LSH** — each shingle set gets a 128-permutation MinHash
   signature (deterministic hashlib seeds); 32 bands × 4 rows of LSH
   propose candidate pairs cheaply.
5. **Exact verify** — every candidate pair is re-scored with the exact
   Jaccard similarity over the full shingle sets. MinHash is only a
   pre-filter: it can miss a pair, but it can never invent one.
6. **Cluster** — union-find over pairs at or above the threshold, plus
   verbatim edges from identical SHA-256 hashes of normalized text.
7. **Verdict** — within each cluster, the member with the largest mtime
   is the "newest". Every other member is line-diffed against it with
   difflib: lines only in the newest are "missing", lines only in the
   member are "own". Verdicts: `CURRENT` (identical to newest), `STALE`
   (missing lines, no own lines), `DIVERGED` (differs in both
   directions, or has own lines only), `UNIQUE` (singleton cluster).
   Missing-line samples in reports are capped at 10.

## Differentiation

- **vs the declared-provenance spec** (the dev.to `derived-from` idea):
  that spec only works where lineage was declared. skillclone works
  with zero metadata and complements the spec — when keys *are*
  present, normalization excludes them so matching still works.
- **vs AAIF-style skill versioning**: versioning answers "which version
  of this skill am I running?" skillclone answers a different question:
  "which copies of this skill exist, and which ones missed an update?"
  The two are complementary, not competing.

## Honest limitations

- **mtime is a proxy.** "Newest" means largest modification time on this
  disk, not latest upstream change. A freshly re-copied old skill looks
  new, and a cluster where every member is identical is reported
  CURRENT with an explicit note: the corpus-local newest copy may itself
  be stale versus the upstream original, which this tool cannot see.
- **The pre-filter is probabilistic.** LSH banding can miss a pair whose
  true similarity is near the threshold; anything it proposes is verified
  exactly, so misses are false negatives, never false positives.
- **Threshold tuning is yours.** 0.80 is a default, not a truth. Heavily
  templated skills (same boilerplate, different substance) can score
  high; genuinely related skills with different wording can score low.
- **No semantic judgement.** A `DIVERGED` skill may already contain an
  equivalent of the newest copy's fix, reworded. Verdicts are a prompt
  to review, not a verdict to auto-block: a human decides whether a
  missing line matters.
- **Local files only.** The tool reads the corpus you point it at; it
  cannot discover copies on other machines or judge an upstream repo it
  was never shown.

## Tests

```sh
python -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
