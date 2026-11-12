# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Bounded, complete dependency discovery for destructive index refreshes.

Legacy list helpers remain available for read-only callers. A writer must either
reach EOF on every page or fail before mutating the archive; a partial list is
never a successful result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterator

from .incremental_graph_scope import DEPENDENT_CALL_DEPTH, chunks
from .incremental_dispatch_scope import CLASS_HIERARCHY_RE


class IncompleteDependencyDiscovery(RuntimeError):
    pass


@dataclass
class DiscoveryBudget:
    max_rows: int = 1_000_000
    max_paths: int = 50_000
    max_queries: int = 20_000
    max_source_bytes: int = 16 * 1024 * 1024
    max_seconds: float = 30.0
    page_size: int = 400
    rows: int = 0
    queries: int = 0
    source_bytes: int = 0
    paths: set[str] = field(default_factory=set)
    started: float = field(default_factory=time.monotonic)

    def check(self) -> None:
        if (self.rows > self.max_rows or self.queries > self.max_queries
                or self.source_bytes > self.max_source_bytes
                or len(self.paths) > self.max_paths
                or time.monotonic() - self.started > self.max_seconds):
            raise IncompleteDependencyDiscovery(
                "Dependency discovery incomplete: resource budget exceeded; index unchanged"
            )
        if not 1 <= self.page_size <= 400:
            raise IncompleteDependencyDiscovery("Invalid dependency page size")

    def add_paths(self, paths: set[str]) -> None:
        self.paths.update(paths)
        self.check()


def pages(conn: sqlite3.Connection, table: str, columns: str, where: str,
          args: tuple[Any, ...], budget: DiscoveryBudget) -> Iterator[sqlite3.Row]:
    cursor = -1
    while True:
        budget.queries += 1
        budget.check()
        rows = conn.execute(
            f"SELECT id, {columns} FROM {table} WHERE ({where}) AND id > ? "
            "ORDER BY id LIMIT ?", (*args, cursor, budget.page_size),
        ).fetchall()
        budget.rows += len(rows)
        budget.check()
        if not rows:
            return
        for row in rows:
            new_cursor = int(row["id"])
            if new_cursor <= cursor:
                raise IncompleteDependencyDiscovery("Non-monotonic dependency cursor")
            cursor = new_cursor
            yield row
        # Query once more even for a short page: completion is explicit EOF.


def entity_paths(conn: sqlite3.Connection, project_id: str,
                 entities: dict[str, set[int]], budget: DiscoveryBudget) -> set[str]:
    result: set[str] = set()
    tables = {"code_file": "code_files", "code_symbol": "code_symbols",
              "code_log_statement": "code_log_statements"}
    for kind, ids in entities.items():
        for group in chunks(sorted(ids)):
            seen: set[int] = set()
            for row in pages(conn, tables[kind], "file_path",
                             f"project_id=? AND id IN ({','.join('?' for _ in group)})",
                             (project_id, *group), budget):
                seen.add(int(row["id"]))
                result.add(str(row["file_path"]))
            if seen != set(group):
                raise IncompleteDependencyDiscovery("Dependency endpoint missing; index unchanged")
            budget.add_paths(result)
    return result


def incoming(conn: sqlite3.Connection, project_id: str, ids: set[int],
             target_type: str, condition: str, budget: DiscoveryBudget
             ) -> Iterator[sqlite3.Row]:
    for group in chunks(sorted(ids)):
        yield from pages(
            conn, "memory_edges", "source_type, source_id, target_id",
            "project_id=? AND valid_to IS NULL AND target_type=? "
            f"AND target_id IN ({','.join('?' for _ in group)}) AND ({condition})",
            (project_id, target_type, *group), budget,
        )


def complete_reverse_paths(conn: sqlite3.Connection, project_id: str,
                           scoped_ids: dict[str, set[int]],
                           budget: DiscoveryBudget) -> list[str]:
    sources: dict[str, set[int]] = {
        "code_file": set(), "code_symbol": set(), "code_log_statement": set()}
    for kind, ids in scoped_ids.items():
        for row in incoming(conn, project_id, ids, kind,
                            "source_type IN ('code_file','code_symbol','code_log_statement')",
                            budget):
            sources[str(row["source_type"])].add(int(row["source_id"]))
    frontier = set(scoped_ids.get("code_symbol", set()))
    visited = set(frontier)
    for _ in range(DEPENDENT_CALL_DEPTH):
        next_frontier = {
            int(row["source_id"]) for row in incoming(
                conn, project_id, frontier, "code_symbol",
                "source_type='code_symbol' AND relation='calls'", budget)
        } - visited
        if not next_frontier:
            break
        sources["code_symbol"].update(next_frontier)
        visited.update(next_frontier)
        frontier = next_frontier
    return sorted(entity_paths(conn, project_id, sources, budget))


def parent_names(root: Path, changed_paths: list[str], budget: DiscoveryBudget) -> set[str]:
    names: set[str] = set()
    for relative in changed_paths:
        if Path(relative).suffix.lower() not in {".ets", ".ts", ".tsx"}:
            continue
        budget.check()
        try:
            with (root / relative).open("rb") as source:
                data = source.read(max(0, budget.max_source_bytes - budget.source_bytes) + 1)
        except OSError as exc:
            raise IncompleteDependencyDiscovery("Cannot inspect changed dependency source") from exc
        budget.source_bytes += len(data)
        budget.check()
        for extends, implements in CLASS_HIERARCHY_RE.findall(data.decode("utf-8", errors="ignore")):
            if extends:
                names.add(extends)
            for item in implements.split(",") if implements else []:
                match = re.match(r"[A-Za-z_$][\w$]*", item.strip())
                if match:
                    names.add(match.group(0))
    return names


def complete_dispatch_paths(conn: sqlite3.Connection, project: Any,
                            changed_paths: list[str], previous_ids: set[int],
                            budget: DiscoveryBudget) -> list[str]:
    contracts: set[int] = set()
    for group in chunks(sorted(previous_ids)):
        for row in pages(conn, "memory_edges", "target_id",
                         "project_id=? AND valid_to IS NULL AND source_type='code_symbol' "
                         "AND target_type='code_symbol' AND relation IN ('implements','extends') "
                         f"AND source_id IN ({','.join('?' for _ in group)})",
                         (project.project_id, *group), budget):
            contracts.add(int(row["target_id"]))
    names = parent_names(project.root, changed_paths, budget)
    for group in chunks(sorted(names)):
        for row in pages(conn, "code_symbols", "symbol",
                         f"project_id=? AND symbol IN ({','.join('?' for _ in group)})",
                         (project.project_id, *group), budget):
            contracts.add(int(row["id"]))
    ids = set(contracts)
    for row in incoming(conn, project.project_id, contracts, "code_symbol",
                        "source_type='code_symbol' AND relation IN "
                        "('dispatches_via','implements','extends')", budget):
        ids.add(int(row["source_id"]))
    return sorted(entity_paths(conn, project.project_id, {"code_symbol": ids}, budget))
