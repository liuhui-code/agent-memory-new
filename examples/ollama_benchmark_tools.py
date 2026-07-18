# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from tools.agent_memory_runtime.source_exploration import (
    SOURCE_FILE_LIMIT,
    SOURCE_READ_LINE_LIMIT,
    SOURCE_READS_PER_FILE_LIMIT,
    SOURCE_SEARCH_LIMIT,
)


MAX_SEARCH_MATCHES = 80
MAX_SEARCHED_FILES = 20_000
MAX_SOURCE_FILE_BYTES = 2_000_000
MAX_TOOL_OUTPUT_BYTES = 64_000
IGNORED_DIRECTORIES = {
    ".agent-memory",
    ".git",
    ".hg",
    ".svn",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "oh_modules",
    "vendor",
}


def source_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "read_source",
                "description": "Read a bounded line window from a source file in the workspace.",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "start_line", "end_line"],
                    "properties": {
                        "path": {"type": "string"},
                        "start_line": {"type": "integer", "minimum": 1},
                        "end_line": {"type": "integer", "minimum": 1},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_source",
                "description": "Search current workspace source text for a literal term.",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string"},
                        "path": {"type": "string"},
                    },
                },
            },
        },
    ]


class SourceToolExecutor:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.command_count = 0
        self.command_output_bytes = 0
        self.source_search_count = 0
        self.source_search_miss_count = 0
        self.source_search_error_count = 0
        self.source_read_count = 0
        self.source_read_output_bytes = 0
        self.source_read_error_count = 0
        self.other_tool_error_count = 0
        self.investigated_files: list[str] = []
        self._read_counts: dict[str, int] = {}

    def execute(self, name: str, arguments: Any) -> str:
        self.command_count += 1
        try:
            values = arguments if isinstance(arguments, dict) else {}
            if name == "read_source":
                output = self._read_source(values)
            elif name == "search_source":
                output = self._search_source(values)
            else:
                self.other_tool_error_count += 1
                output = self._error(f"unsupported tool: {name}")
        except (OSError, UnicodeError, ValueError) as exc:
            self.other_tool_error_count += 1
            output = self._error(str(exc))
        output = byte_limited(output, MAX_TOOL_OUTPUT_BYTES)
        self.command_output_bytes += len(output.encode("utf-8"))
        return output

    def telemetry(self) -> dict[str, Any]:
        errors = (
            self.source_search_error_count
            + self.source_read_error_count
            + self.other_tool_error_count
        )
        return {
            "command_count": self.command_count,
            "command_output_bytes": self.command_output_bytes,
            "source_read_count": self.source_read_count,
            "source_read_output_bytes": self.source_read_output_bytes,
            "tool_error_count": errors,
            "source_search_count": self.source_search_count,
            "source_search_count_source": "runner_telemetry",
            "source_search_miss_count": self.source_search_miss_count,
            "source_search_error_count": self.source_search_error_count,
            "source_read_error_count": self.source_read_error_count,
            "other_tool_error_count": self.other_tool_error_count,
        }

    def _read_source(self, values: dict[str, Any]) -> str:
        self.source_read_count += 1
        try:
            relative, path = self._resolve_file(values.get("path"))
            start = positive_int(values.get("start_line"), "start_line")
            end = positive_int(values.get("end_line"), "end_line")
            if end < start:
                raise ValueError("end_line must be greater than or equal to start_line")
            if end - start + 1 > SOURCE_READ_LINE_LIMIT:
                raise ValueError(f"read exceeds {SOURCE_READ_LINE_LIMIT} lines")
            count = self._read_counts.get(relative, 0)
            if count >= SOURCE_READS_PER_FILE_LIMIT:
                raise ValueError(
                    f"read limit reached for {relative}: {SOURCE_READS_PER_FILE_LIMIT}"
                )
            if path.stat().st_size > MAX_SOURCE_FILE_BYTES:
                raise ValueError(f"source file exceeds {MAX_SOURCE_FILE_BYTES} bytes")
            data = path.read_bytes()
            if b"\x00" in data:
                raise ValueError("source file is binary-like")
            if relative not in self.investigated_files:
                if len(self.investigated_files) >= SOURCE_FILE_LIMIT:
                    raise ValueError(f"source file limit reached: {SOURCE_FILE_LIMIT}")
                self.investigated_files.append(relative)
            lines = data.decode("utf-8").splitlines()
            selected = lines[start - 1:end]
            output = "\n".join(
                f"{number}: {line}"
                for number, line in enumerate(selected, start=start)
            )
            self._read_counts[relative] = count + 1
            output = byte_limited(json.dumps(
                {"path": relative, "start_line": start, "end_line": end, "content": output},
                ensure_ascii=False,
            ), MAX_TOOL_OUTPUT_BYTES)
            self.source_read_output_bytes += len(output.encode("utf-8"))
            return output
        except (OSError, UnicodeError, ValueError) as exc:
            self.source_read_error_count += 1
            return self._error(str(exc))

    def _search_source(self, values: dict[str, Any]) -> str:
        self.source_search_count += 1
        try:
            if self.source_search_count > SOURCE_SEARCH_LIMIT:
                raise ValueError(f"source search limit reached: {SOURCE_SEARCH_LIMIT}")
            query = str(values.get("query") or "").strip()
            if not query or len(query) > 200:
                raise ValueError("query must contain 1 to 200 characters")
            root = self._resolve_search_root(values.get("path"))
            matches = literal_matches(root, self.workspace, query)
            if not matches:
                self.source_search_miss_count += 1
            return json.dumps({"query": query, "matches": matches}, ensure_ascii=False)
        except (OSError, UnicodeError, ValueError) as exc:
            self.source_search_error_count += 1
            return self._error(str(exc))

    def _resolve_file(self, value: Any) -> tuple[str, Path]:
        path = safe_workspace_path(self.workspace, value)
        if not path.is_file():
            raise ValueError(f"source file not found: {value}")
        return path.relative_to(self.workspace).as_posix(), path

    def _resolve_search_root(self, value: Any) -> Path:
        if value is None or not str(value).strip():
            return self.workspace
        path = safe_workspace_path(self.workspace, value)
        if not path.exists():
            raise ValueError(f"search path not found: {value}")
        return path

    @staticmethod
    def _error(message: str) -> str:
        return json.dumps({"error": message}, ensure_ascii=False)


def safe_workspace_path(workspace: Path, value: Any) -> Path:
    text = str(value or "").strip()
    if not text or Path(text).is_absolute():
        raise ValueError("path must be a relative workspace path")
    path = (workspace / text).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("path escapes the workspace") from exc
    return path


def literal_matches(root: Path, workspace: Path, query: str) -> list[dict[str, Any]]:
    needle = query.casefold()
    matches: list[dict[str, Any]] = []
    for path in source_files(root):
        try:
            resolved = path.resolve()
            resolved.relative_to(workspace)
            if path.is_symlink() or path.stat().st_size > MAX_SOURCE_FILE_BYTES:
                continue
        except (OSError, ValueError):
            continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if "\x00" in text:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if needle not in line.casefold():
                continue
            matches.append({
                "path": path.relative_to(workspace).as_posix(),
                "line": number,
                "text": line[:500],
            })
            if len(matches) >= MAX_SEARCH_MATCHES:
                return matches
    return matches


def source_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    scanned = 0
    for directory, names, files in os.walk(root):
        names[:] = sorted(name for name in names if name not in IGNORED_DIRECTORIES)
        for name in sorted(files):
            scanned += 1
            if scanned > MAX_SEARCHED_FILES:
                raise ValueError(f"search exceeds {MAX_SEARCHED_FILES} files")
            path = Path(directory) / name
            if path.is_file() and not path.is_symlink():
                yield path


def positive_int(value: Any, name: str) -> int:
    if isinstance(value, str) and value.isascii() and value.isdigit():
        value = int(value)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def byte_limited(value: str, limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    return encoded[:limit].decode("utf-8", errors="ignore") + "\n[truncated]"
