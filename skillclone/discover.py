"""Discover SKILL.md files under given roots.

Nothing is skipped silently: roots that do not exist and directories
that cannot be listed are reported as warnings alongside the results,
so a caller can always tell the difference between "no skills found"
and "a root could not be read".
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SkillFile:
    """One discovered SKILL.md file plus its derived content fields.

    ``normalized``, ``sha256`` and ``word_count`` are filled in by the
    scan pipeline after the file is read; discovery itself only records
    the filesystem facts.
    """

    path: str
    size: int
    mtime: float
    normalized: str = ""
    sha256: str = ""
    word_count: int = 0


def _add_file(files: list, warnings: list, path: str) -> None:
    try:
        stat = os.stat(path)
    except OSError as exc:
        warnings.append(f"cannot stat {path}: {exc}")
        return
    files.append(SkillFile(path=path, size=stat.st_size, mtime=stat.st_mtime))


def find_skill_files(roots):
    """Walk each root recursively and collect files named exactly SKILL.md.

    A root may also be a single SKILL.md file. Returns ``(files, warnings)``
    where ``files`` is sorted by path for deterministic output.
    """
    files: list = []
    warnings: list = []
    for root in roots:
        if os.path.isfile(root):
            if os.path.basename(root) == "SKILL.md":
                _add_file(files, warnings, root)
            else:
                warnings.append(f"not a SKILL.md file: {root}")
        elif os.path.isdir(root):
            def _onerror(exc, _warnings=warnings):
                warnings.append(f"cannot list directory: {getattr(exc, 'filename', None) or exc}")

            for dirpath, dirnames, filenames in os.walk(root, onerror=_onerror):
                dirnames.sort()
                for name in sorted(filenames):
                    if name == "SKILL.md":
                        _add_file(files, warnings, os.path.join(dirpath, name))
        else:
            warnings.append(f"root does not exist: {root}")
    files.sort(key=lambda item: item.path)
    return files, warnings
