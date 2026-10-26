"""Judge each cluster member against the cluster's newest member.

The "newest" member is the one with the largest file modification time.
That is a proxy, stated honestly: mtime says when a copy was last
written on this disk, not when its upstream source last changed. A
freshly re-copied old skill looks "new", and the newest corpus copy may
itself be stale relative to the original author. The verdicts below are
therefore corpus-relative, and the report says so wherever a cluster is
fully identical.

Line comparison uses difflib on the normalized texts. For each member:

* lines only in the newest member are "missing" from the member;
* lines only in the member are the member's "own" lines.

Verdicts:

* CURRENT  -- no missing lines and no own lines (identical to newest).
* STALE    -- missing lines, but no own lines: a strict subset that has
  not kept up with the newest copy.
* DIVERGED -- the member differs in both directions (missing and own),
  or has own lines only: it has gone its own way, so a reviewer cannot
  assume the newest copy's changes apply cleanly.
* UNIQUE   -- the skill is alone in its cluster; nothing to compare to.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

MISSING_SAMPLE_CAP = 10

ALL_IDENTICAL_NOTE = (
    "All members are identical, so all are CURRENT relative to the "
    "corpus-local newest member -- but that newest copy may itself be "
    "stale compared with the upstream original, which this tool cannot see."
)


@dataclass
class SkillVerdict:
    path: str
    verdict: str
    missing_count: int
    own_count: int
    missing_lines: list = field(default_factory=list)
    own_lines: list = field(default_factory=list)
    newest_path: str = ""


@dataclass
class ClusterVerdict:
    members: list
    newest_path: str
    all_identical: bool
    note: str = ""


def _line_diff(newest_lines: list, member_lines: list):
    """Return ``(missing, own)`` line lists via difflib opcodes."""
    matcher = difflib.SequenceMatcher(
        None, newest_lines, member_lines, autojunk=False
    )
    missing, own = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            missing.extend(newest_lines[i1:i2])
        if tag in ("insert", "replace"):
            own.extend(member_lines[j1:j2])
    return missing, own


def _split_lines(normalized: str) -> list:
    return normalized.split("\n") if normalized else []


def verdict_for_cluster(members) -> ClusterVerdict:
    """Compute verdicts for one cluster of skills."""
    if len(members) == 1:
        only = members[0]
        return ClusterVerdict(
            members=[SkillVerdict(
                path=only.path, verdict="UNIQUE",
                missing_count=0, own_count=0, newest_path=only.path,
            )],
            newest_path=only.path,
            all_identical=False,
        )
    newest = max(members, key=lambda skill: (skill.mtime, skill.path))
    newest_lines = _split_lines(newest.normalized)
    all_identical = len({skill.sha256 for skill in members}) == 1
    verdicts = []
    for member in members:
        if member is newest:
            verdicts.append(SkillVerdict(
                path=member.path, verdict="CURRENT",
                missing_count=0, own_count=0, newest_path=newest.path,
            ))
            continue
        missing, own = _line_diff(newest_lines, _split_lines(member.normalized))
        if not missing and not own:
            verdict = "CURRENT"
        elif missing and not own:
            verdict = "STALE"
        else:
            verdict = "DIVERGED"
        verdicts.append(SkillVerdict(
            path=member.path, verdict=verdict,
            missing_count=len(missing), own_count=len(own),
            missing_lines=missing[:MISSING_SAMPLE_CAP],
            own_lines=own[:MISSING_SAMPLE_CAP],
            newest_path=newest.path,
        ))
    verdicts.sort(key=lambda verdict: verdict.path)
    return ClusterVerdict(
        members=verdicts,
        newest_path=newest.path,
        all_identical=all_identical,
        note=ALL_IDENTICAL_NOTE if all_identical else "",
    )
