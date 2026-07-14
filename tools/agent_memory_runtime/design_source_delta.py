# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .models import Project
from .semantic_ecma import ParsedFile, parse_source
from .storage import connect


MAX_DIFF_BYTES = 2_000_000
MAX_DIFF_FILES = 100
MAX_HUNKS = 1000
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
LANGUAGES = {".ets": ("ArkTS", True), ".ts": ("TypeScript", False), ".tsx": ("TypeScript", False)}
REVISION_RE = re.compile(r"^[A-Za-z0-9._/@^~:+-]{1,200}$")


def collect_source_delta(project: Project, base: str, diff_file: str | None) -> dict[str, Any]:
    diff, source = read_diff(project, base, diff_file)
    if not diff.strip():
        return empty_delta("no_diff", source, base)
    entries = parse_diff_hunks(diff)
    changed_symbols: list[str] = []
    api_changes: list[dict[str, Any]] = []
    added_relations: list[dict[str, str]] = []
    removed_relations: list[dict[str, str]] = []
    files: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    for entry in entries[:MAX_DIFF_FILES]:
        old_path, new_path = entry["old_path"], entry["new_path"]
        old = parse_version(project, old_path, git_show(project, base, old_path)) if old_path else None
        current_text = read_current(project, new_path) if new_path else None
        current = parse_version(project, new_path, current_text) if new_path else None
        if old is None and current is None:
            gaps.append({"kind": "unsupported_or_unreadable_source", "path": new_path or old_path or ""})
            continue
        fresh_symbols = [
            *symbols_for_ranges(current, entry["new_ranges"]),
            *symbols_for_ranges(old, entry["old_ranges"]),
        ]
        changed_symbols.extend(
            fresh_symbols or learned_symbols(
                project,
                new_path or old_path,
                entry["new_ranges"] or entry["old_ranges"],
            )
        )
        api_changes.extend(compare_api(old, current, old_path, new_path))
        relation_delta = compare_relations(old, current)
        added_relations.extend(relation_delta["added"])
        removed_relations.extend(relation_delta["removed"])
        files.append({
            "old_path": old_path,
            "new_path": new_path,
            "old_digest": old.digest if old else None,
            "new_digest": current.digest if current else None,
            "changed_old_lines": range_size(entry["old_ranges"]),
            "changed_new_lines": range_size(entry["new_ranges"]),
        })
    return {
        "schema_version": "design-source-delta/v1",
        "status": "available",
        "base": base,
        "source": source,
        "changed_symbols": sorted(set(changed_symbols)),
        "api_changes": sorted(api_changes, key=lambda item: (item["path"], item["symbol"], item["change"])),
        "graph_delta": {
            "added_relations": unique_relations(added_relations),
            "removed_relations": unique_relations(removed_relations),
        },
        "files": files,
        "evidence_gaps": gaps,
        "audit": {
            "diff_bytes": len(diff.encode("utf-8")),
            "file_count": len(files),
            "hunk_count": sum(len(item["new_ranges"]) for item in entries),
            "source_persisted": False,
            "diff_persisted": False,
        },
    }


def read_diff(project: Project, base: str, diff_file: str | None) -> tuple[str, str]:
    validate_revision(base)
    if diff_file:
        raw = Path(diff_file).read_bytes()
        if len(raw) > MAX_DIFF_BYTES:
            raise SystemExit(f"design diff exceeds {MAX_DIFF_BYTES} bytes")
        return raw.decode("utf-8", errors="ignore"), "diff_file"
    process = subprocess.run(
        ["git", "-c", "core.quotePath=false", "diff", "--unified=0", "--no-ext-diff", base, "--"],
        cwd=project.root,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode:
        return "", "git_unavailable"
    if len(process.stdout.encode("utf-8")) > MAX_DIFF_BYTES:
        raise SystemExit(f"design diff exceeds {MAX_DIFF_BYTES} bytes")
    return process.stdout, "git"


def parse_diff_hunks(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    hunk_count = 0
    for line in text.splitlines():
        if line.startswith("diff --git "):
            if current:
                entries.append(current)
            current = {"old_path": None, "new_path": None, "old_ranges": [], "new_ranges": []}
        elif current is not None and line.startswith("--- "):
            current["old_path"] = diff_path(line[4:])
        elif current is not None and line.startswith("+++ "):
            current["new_path"] = diff_path(line[4:])
        elif current is not None and line.startswith("@@ "):
            match = HUNK_RE.match(line)
            if not match:
                continue
            old_start, old_count, new_start, new_count = match.groups()
            current["old_ranges"].append((int(old_start), int(old_count or 1)))
            current["new_ranges"].append((int(new_start), int(new_count or 1)))
            hunk_count += 1
            if hunk_count > MAX_HUNKS:
                raise SystemExit(f"design diff exceeds {MAX_HUNKS} hunks")
    if current:
        entries.append(current)
    return [item for item in entries if item["old_path"] or item["new_path"]][:MAX_DIFF_FILES]


def diff_path(value: str) -> str | None:
    try:
        tokens = shlex.split(value)
    except ValueError as exc:
        raise SystemExit(f"invalid diff path: {exc}") from exc
    path = tokens[0] if tokens else ""
    if path == "/dev/null":
        return None
    path = path[2:] if path.startswith(("a/", "b/")) else path
    validate_relative_path(path)
    return path


def git_show(project: Project, base: str, path: str | None) -> str | None:
    if not path:
        return None
    process = subprocess.run(
        ["git", "show", f"{base}:{path}"],
        cwd=project.root,
        text=True,
        capture_output=True,
        check=False,
    )
    return process.stdout if process.returncode == 0 else None


def read_current(project: Project, path: str | None) -> str | None:
    if not path:
        return None
    source = (project.root / path).resolve()
    try:
        source.relative_to(project.root.resolve())
    except ValueError as exc:
        raise SystemExit("design diff resolves outside the project") from exc
    return source.read_text(encoding="utf-8", errors="ignore") if source.is_file() else None


def validate_revision(value: str) -> None:
    if value.startswith("-") or not REVISION_RE.fullmatch(value):
        raise SystemExit("design base revision contains unsupported characters")


def validate_relative_path(value: str) -> None:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise SystemExit("design diff contains a path outside the project")


def parse_version(project: Project, path: str | None, text: str | None) -> ParsedFile | None:
    if not path or text is None:
        return None
    language = LANGUAGES.get(Path(path).suffix.lower())
    if not language:
        return None
    return parse_source(project, project.root / path, text, language[0], language[1])


def symbols_for_ranges(parsed: ParsedFile | None, ranges: list[tuple[int, int]]) -> list[str]:
    if not parsed:
        return []
    result = []
    for start, count in ranges:
        candidates = [
            entity for entity in parsed.entities
            if overlaps(entity.start_line, entity.end_line, start, count)
        ]
        specific = [entity for entity in candidates if entity.kind not in {"class", "component", "interface"}]
        for entity in specific or candidates:
            result.append(f"symbol:{parsed.path}::{entity.qualified_name}")
    return result


def overlaps(entity_start: int, entity_end: int, changed_start: int, changed_count: int) -> bool:
    changed_end = changed_start + max(1, changed_count) - 1
    return entity_start <= changed_end and changed_start <= entity_end


def learned_symbols(project: Project, path: str | None, ranges: list[tuple[int, int]]) -> list[str]:
    if not path or not ranges:
        return []
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT qualified_name, symbol, start_line, end_line
            FROM code_symbols
            WHERE project_id = ? AND file_path = ?
              AND start_line IS NOT NULL AND end_line IS NOT NULL
            ORDER BY start_line, end_line
            """,
            (project.project_id, path),
        ).fetchall()
    result = []
    for row in rows:
        if any(overlaps(int(row["start_line"]), int(row["end_line"]), start, count) for start, count in ranges):
            name = str(row["qualified_name"] or row["symbol"])
            result.append(f"symbol:{path}::{name}")
    return result


def compare_api(old: ParsedFile | None, current: ParsedFile | None, old_path: str | None, new_path: str | None) -> list[dict[str, Any]]:
    before = {item.qualified_name: item for item in old.entities if item.exported} if old else {}
    after = {item.qualified_name: item for item in current.entities if item.exported} if current else {}
    changes = []
    for name in sorted(set(before) | set(after)):
        left, right = before.get(name), after.get(name)
        if left and right and left.signature == right.signature:
            continue
        changes.append({
            "change": "signature_changed" if left and right else "removed" if left else "added",
            "symbol": name,
            "path": new_path or old_path or "",
            "old_signature": left.signature if left else None,
            "new_signature": right.signature if right else None,
            "evidence_class": "static",
        })
    return changes


def compare_relations(old: ParsedFile | None, current: ParsedFile | None) -> dict[str, list[dict[str, str]]]:
    before = relation_shapes(old)
    after = relation_shapes(current)
    return {
        "added": [shape_dict(item) for item in sorted(after - before)],
        "removed": [shape_dict(item) for item in sorted(before - after)],
    }


def relation_shapes(parsed: ParsedFile | None) -> set[tuple[str, str, str]]:
    if not parsed:
        return set()
    names = {item.key: item.qualified_name for item in parsed.entities}
    result = set()
    for item in parsed.relations:
        source = names.get(item.source_key, item.source_key)
        target = names.get(item.target_key or "") or item.target_qualified_name or item.target_name or item.target_file_path or "unknown"
        result.add((source, item.relation, target))
    return result


def shape_dict(value: tuple[str, str, str]) -> dict[str, str]:
    return {"source": value[0], "relation": value[1], "target": value[2]}


def unique_relations(values: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    result = []
    for value in values:
        key = (value["source"], value["relation"], value["target"])
        if key not in seen:
            seen.add(key)
            result.append(value)
    return sorted(result, key=lambda item: (item["source"], item["relation"], item["target"]))[:200]


def range_size(ranges: list[tuple[int, int]]) -> int:
    return sum(count for _start, count in ranges)


def empty_delta(status: str, source: str, base: str) -> dict[str, Any]:
    return {
        "schema_version": "design-source-delta/v1",
        "status": status,
        "base": base,
        "source": source,
        "changed_symbols": [],
        "api_changes": [],
        "graph_delta": {"added_relations": [], "removed_relations": []},
        "files": [],
        "evidence_gaps": [{"kind": status, "path": ""}],
        "audit": {"source_persisted": False, "diff_persisted": False},
    }
