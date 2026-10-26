"""Normalize SKILL.md text before hashing and comparison.

Normalization removes differences that do not change what a skill says:

* CRLF (and lone CR) line endings become LF.
* Trailing whitespace is stripped from every line.
* Trailing blank lines are dropped.

It also strips the two optional provenance lines, ``derived-from:`` and
``derived-from-hash:``. The idea of declaring lineage with those keys
comes from the dev.to post "Your agent's skills have no lockfile"
(sangaraju1988, 24 October 2026); the code below is an original
implementation of that convention. Stripping the keys means a copy that
gained provenance metadata still matches the parent it was copied from,
so content-similarity matching keeps working whether or not a skill
carries declared lineage.
"""

from __future__ import annotations

import re

# A line that declares provenance: "derived-from: <...>" or
# "derived-from-hash: <...>", with optional leading whitespace and any
# casing. Only whole lines are removed, never words inside prose.
_PROVENANCE_LINE = re.compile(r"^\s*derived-from(-hash)?\s*:.*$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """Return the canonical form of ``text`` for hashing and diffing."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    lines = [line for line in lines if not _PROVENANCE_LINE.match(line)]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)
