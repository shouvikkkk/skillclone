"""Command-line interface for skillclone.

Usage:
    python -m skillclone scan <root...> [--threshold 0.8]
                                [--format text|json] [--min-words 20]
    python -m skillclone --version

Exit codes: 0 = no STALE skill found, 2 = at least one STALE skill,
1 = usage or I/O error.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

from . import __version__
from .cluster import build_clusters, verbatim_pairs
from .discover import find_skill_files
from .minhash import candidate_pairs, word_shingles
from .normalize import normalize_text
from .report import json_report, text_report
from .verdict import verdict_for_cluster


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that exits 1 (not argparse's default 2) on errors,
    so exit code 2 stays reserved for "stale skills found"."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(1)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="skillclone")
    parser.add_argument("--version", action="store_true",
                        help="print the skillclone version and exit")
    subparsers = parser.add_subparsers(dest="command")
    scan = subparsers.add_parser("scan", help="scan roots for SKILL.md files")
    scan.add_argument("roots", nargs="+", help="root directories (or SKILL.md files) to scan")
    scan.add_argument("--threshold", type=float, default=0.80,
                      help="minimum exact Jaccard similarity to link two skills (default 0.80)")
    scan.add_argument("--format", choices=["text", "json"], default="text",
                      help="report format (default text)")
    scan.add_argument("--min-words", type=int, default=20,
                      help="skills with fewer words are skipped (default 20)")
    scan.add_argument("--version", action="store_true",
                      help="print the skillclone version and exit")
    return parser


def scan_roots(roots, threshold=0.80, min_words=20):
    """Run the full pipeline and return a report-ready result dict."""
    files, warnings = find_skill_files(roots)
    skills = []
    skipped = []
    for skill in files:
        try:
            with open(skill.path, "r", encoding="utf-8", errors="replace") as handle:
                raw = handle.read()
        except OSError as exc:
            warnings.append(f"cannot read {skill.path}: {exc}")
            continue
        skill.normalized = normalize_text(raw)
        skill.sha256 = hashlib.sha256(skill.normalized.encode("utf-8")).hexdigest()
        skill.word_count = len(skill.normalized.split())
        if skill.word_count < min_words:
            skipped.append({
                "path": skill.path,
                "reason": f"only {skill.word_count} word(s) (minimum {min_words})",
            })
        else:
            skills.append(skill)
    shingle_sets = {i: word_shingles(skill.normalized) for i, skill in enumerate(skills)}
    pair_map = {
        (first, second): similarity
        for first, second, similarity in candidate_pairs(shingle_sets, threshold)
    }
    for first, second in verbatim_pairs(skills):
        pair_map.setdefault((first, second), 1.0)
    groups = build_clusters(len(skills), sorted(pair_map))
    clusters = [verdict_for_cluster([skills[i] for i in group]) for group in groups]
    stale = any(
        member.verdict == "STALE"
        for cluster in clusters for member in cluster.members
    )
    return {
        "clusters": clusters,
        "skipped": skipped,
        "warnings": warnings,
        "stale_found": stale,
    }


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        print(f"skillclone {__version__}")
        return 0
    if args.command != "scan":
        parser.print_usage(sys.stderr)
        print("skillclone: error: a command is required (try 'scan')", file=sys.stderr)
        return 1
    if not 0.0 < args.threshold <= 1.0:
        print("skillclone: error: --threshold must be in (0, 1]", file=sys.stderr)
        return 1
    if args.min_words < 0:
        print("skillclone: error: --min-words must be >= 0", file=sys.stderr)
        return 1
    if not any(os.path.exists(root) for root in args.roots):
        print("skillclone: error: none of the given roots exist", file=sys.stderr)
        return 1
    try:
        result = scan_roots(args.roots, threshold=args.threshold, min_words=args.min_words)
    except OSError as exc:
        print(f"skillclone: error: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json_report(result["clusters"], result["skipped"], result["warnings"]))
    else:
        print(text_report(result["clusters"], result["skipped"], result["warnings"]))
    return 2 if result["stale_found"] else 0
