"""Render scan results as a text report or a JSON report."""

from __future__ import annotations

import json


def _verdict_as_dict(verdict) -> dict:
    return {
        "path": verdict.path,
        "verdict": verdict.verdict,
        "missing_count": verdict.missing_count,
        "own_count": verdict.own_count,
        "missing_lines_sample": verdict.missing_lines,
        "own_lines_sample": verdict.own_lines,
        "newest_path": verdict.newest_path,
    }


def _stale_count(clusters) -> int:
    return sum(
        1 for cluster in clusters for member in cluster.members
        if member.verdict == "STALE"
    )


def text_report(clusters, skipped, warnings) -> str:
    """Human-readable report: one section per cluster."""
    lines = []
    total = sum(len(cluster.members) for cluster in clusters)
    lines.append(f"skillclone report: {total} skill(s) in {len(clusters)} cluster(s)")
    lines.append(f"stale skills: {_stale_count(clusters)}")
    lines.append("")
    for number, cluster in enumerate(clusters, start=1):
        lines.append(
            f"Cluster {number} ({len(cluster.members)} skill(s), "
            f"newest: {cluster.newest_path})"
        )
        if cluster.note:
            lines.append(f"  note: {cluster.note}")
        for member in cluster.members:
            lines.append(
                f"  [{member.verdict}] {member.path} "
                f"(missing {member.missing_count} line(s), "
                f"own {member.own_count} line(s))"
            )
            for missing in member.missing_lines:
                lines.append(f"      missing: {missing}")
        lines.append("")
    if skipped:
        lines.append("Skipped (too few words to compare reliably):")
        for entry in skipped:
            lines.append(f"  {entry['path']}: {entry['reason']}")
        lines.append("")
    if warnings:
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"  {warning}")
        lines.append("")
    return "\n".join(lines)


def json_report(clusters, skipped, warnings) -> str:
    """Machine-readable report with the same information as the text form."""
    total = sum(len(cluster.members) for cluster in clusters)
    payload = {
        "total_skills": total,
        "cluster_count": len(clusters),
        "stale_count": _stale_count(clusters),
        "clusters": [
            {
                "newest_path": cluster.newest_path,
                "all_identical": cluster.all_identical,
                "note": cluster.note,
                "members": [_verdict_as_dict(member) for member in cluster.members],
            }
            for cluster in clusters
        ],
        "skipped": skipped,
        "warnings": warnings,
    }
    return json.dumps(payload, indent=2)
