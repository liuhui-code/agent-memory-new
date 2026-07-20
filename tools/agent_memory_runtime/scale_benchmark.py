# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .code_wiki_extractors import summarize_symbol
from .models import Project
from .query_candidate_recall import SQLiteCandidateRecall, recall_candidate_ids
from .records import output
from .scale_maintenance import benchmark_incremental_maintenance
from .storage import connect, ensure_dirs, ensure_initialized, now_iso, resolve_project


BATCH_SIZE = 10_000


@dataclass(frozen=True)
class ScaleProfile:
    name: str
    entity_count: int
    edge_count: int
    repetitions: int = 5

    @property
    def file_count(self) -> int:
        return max(1, self.entity_count // 20)

    @property
    def symbol_count(self) -> int:
        return max(1, self.entity_count * 4 // 5)

    @property
    def log_count(self) -> int:
        return self.entity_count - self.file_count - self.symbol_count


PROFILES = {
    "ci": ScaleProfile("ci", 100_000, 300_000, 5),
    "million": ScaleProfile("million", 1_000_000, 3_000_000, 7),
}

SLO_MS = {
    "candidate_recall_hit": 800.0,
    "candidate_recall_miss": 800.0,
    "generic_symbol_abstention": 100.0,
    "exact_log_fts": 1000.0,
    "qualified_symbol_lookup": 100.0,
    "file_symbols": 100.0,
    "outgoing_edges": 100.0,
    "incoming_edges": 100.0,
}


def eval_scale_command(args: argparse.Namespace) -> None:
    owner = resolve_project(args.project, args.memory_home)
    ensure_dirs(owner)
    report = run_scale_benchmark(PROFILES[args.profile])
    path = owner.runtime_dir / "last_scale_benchmark.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output(report, args.json)
    if args.fail_on_slo and report["status"] != "pass":
        raise SystemExit("scale benchmark failed")


def run_scale_benchmark(profile: ScaleProfile) -> dict[str, Any]:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="agent-memory-scale-") as directory:
        root = Path(directory) / "source"
        root.mkdir()
        project = resolve_project(str(root), str(Path(directory) / "memory"))
        ensure_initialized(project)
        load_times = seed_scale_data(project, profile)
        setup_seconds = time.perf_counter() - started
        with connect(project) as conn:
            conn.execute("ANALYZE")
            conn.execute("PRAGMA optimize")
            operations = benchmark_operations(conn, project, profile.repetitions)
            plans = benchmark_query_plans(conn, project.project_id)
            counts = observed_counts(conn)
        maintenance = benchmark_incremental_maintenance(project, profile.repetitions)
        database_size = database_bytes(project.db_path)
    latency_pass = all(value["pass"] for value in operations.values())
    plan_pass = all(value["pass"] for value in plans.values())
    maintenance_pass = maintenance["status"] == "pass"
    return {
        "schema_version": "scale-benchmark/v1",
        "profile": profile.name,
        "status": "pass" if latency_pass and plan_pass and maintenance_pass else "fail",
        "configured_counts": profile_counts(profile),
        "observed_counts": counts,
        "database_bytes": database_size,
        "setup_seconds": round(setup_seconds, 3),
        "total_seconds": round(time.perf_counter() - started, 3),
        "load_seconds": load_times,
        "operations": operations,
        "incremental_maintenance": maintenance,
        "query_plans": plans,
        "gates": {
            "latency": latency_pass,
            "query_plan": plan_pass,
            "incremental_maintenance": maintenance_pass,
        },
    }


def seed_scale_data(project: Project, profile: ScaleProfile) -> dict[str, float]:
    timings: dict[str, float] = {}
    with connect(project) as conn:
        timings["code_files"] = timed_load(
            conn,
            """INSERT INTO code_files(
                 id, project_id, file_path, summary, language, updated_at
               ) VALUES (?, ?, ?, ?, 'ArkTS', ?)""",
            file_rows(profile, project.project_id),
        )
        timings["code_symbols"] = timed_load(
            conn,
            """INSERT INTO code_symbols(
                 id, project_id, file_path, symbol, symbol_type, summary,
                 symbol_key, qualified_name, signature, updated_at
               ) VALUES (?, ?, ?, ?, 'function', ?, ?, ?, ?, ?)""",
            symbol_rows(profile, project.project_id),
        )
        timings["code_logs"] = timed_load(
            conn,
            """INSERT INTO code_log_statements(
                 id, project_id, file_path, line, function, level, logger,
                 message_template, raw_statement, updated_at
               ) VALUES (?, ?, ?, ?, ?, 'INFO', 'ScaleLogger', ?, ?, ?)""",
            log_rows(profile, project.project_id),
        )
        timings["memory_edges"] = timed_load(
            conn,
            """INSERT INTO memory_edges(
                 id, project_id, source_type, source_id, relation, target_type,
                 target_id, evidence, confidence, valid_from, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, 'scale', 0.9, ?, ?)""",
            edge_rows(profile, project.project_id),
        )
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return timings


def timed_load(conn: sqlite3.Connection, sql: str, rows: Iterable[tuple[Any, ...]]) -> float:
    started = time.perf_counter()
    batch: list[tuple[Any, ...]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            conn.executemany(sql, batch)
            conn.commit()
            batch.clear()
    if batch:
        conn.executemany(sql, batch)
        conn.commit()
    return round(time.perf_counter() - started, 3)


def file_rows(profile: ScaleProfile, project_id: str) -> Iterable[tuple[Any, ...]]:
    ts = now_iso()
    for file_id in range(1, profile.file_count + 1):
        yield (
            file_id,
            project_id,
            file_path(file_id),
            "ArkTS service component for bounded scale retrieval",
            ts,
        )


def symbol_rows(profile: ScaleProfile, project_id: str) -> Iterable[tuple[Any, ...]]:
    ts = now_iso()
    for symbol_id in range(1, profile.symbol_count + 1):
        file_id = ((symbol_id - 1) % profile.file_count) + 1
        name = "CriticalPaymentRetryHandler" if symbol_id == 1 else f"method{symbol_id % 10000:04d}"
        qualified = f"Service{file_id}.{name}.{symbol_id}"
        yield (
            symbol_id,
            project_id,
            file_path(file_id),
            name,
            summarize_symbol(file_path(file_id), name, "function", "ArkTS"),
            f"arkts:{file_id}:{symbol_id}",
            qualified,
            f"{name}(): void",
            ts,
        )


def log_rows(profile: ScaleProfile, project_id: str) -> Iterable[tuple[Any, ...]]:
    ts = now_iso()
    for log_id in range(1, profile.log_count + 1):
        file_id = ((log_id - 1) % profile.file_count) + 1
        message = (
            "payment retry exhausted order identifier"
            if log_id == 1 else f"worker event checkpoint {log_id % 1000}"
        )
        yield (
            log_id,
            project_id,
            file_path(file_id),
            (log_id % 400) + 1,
            "CriticalPaymentRetryHandler" if log_id == 1 else f"method{log_id % 10000:04d}",
            message,
            f"console.info('{message}')",
            ts,
        )


def edge_rows(profile: ScaleProfile, project_id: str) -> Iterable[tuple[Any, ...]]:
    ts = now_iso()
    for edge_id in range(1, profile.edge_count + 1):
        if edge_id <= profile.symbol_count:
            file_id = ((edge_id - 1) % profile.file_count) + 1
            yield (
                edge_id, project_id, "code_file", file_id, "contains",
                "code_symbol", edge_id, ts, ts,
            )
            continue
        source_id = ((edge_id - 1) % profile.symbol_count) + 1
        target_id = (source_id % profile.symbol_count) + 1
        yield (
            edge_id, project_id, "code_symbol", source_id, "calls",
            "code_symbol", target_id, ts, ts,
        )


def benchmark_operations(
    conn: sqlite3.Connection,
    project: Project,
    repetitions: int,
) -> dict[str, dict[str, Any]]:
    recall = SQLiteCandidateRecall()
    operations: dict[str, Callable[[], Any]] = {
        "candidate_recall_hit": lambda: recall.recall(conn, project, "payment retry exhausted"),
        "candidate_recall_miss": lambda: recall.recall(conn, project, "zephyrnomatchtoken"),
        "generic_symbol_abstention": lambda: recall_candidate_ids(
            conn, project, "code_symbols", "method", 220
        ),
        "exact_log_fts": lambda: conn.execute(
            "SELECT rowid FROM code_log_fts WHERE code_log_fts MATCH ? "
            "AND project_id = ? ORDER BY bm25(code_log_fts) LIMIT 180",
            ('"payment"* AND "retry"*', project.project_id),
        ).fetchall(),
        "qualified_symbol_lookup": lambda: conn.execute(
            "SELECT id FROM code_symbols WHERE project_id = ? AND qualified_name = ? LIMIT 20",
            (project.project_id, "Service1.CriticalPaymentRetryHandler.1"),
        ).fetchall(),
        "file_symbols": lambda: conn.execute(
            "SELECT id FROM code_symbols WHERE project_id = ? AND file_path = ? LIMIT 220",
            (project.project_id, file_path(1)),
        ).fetchall(),
        "outgoing_edges": lambda: conn.execute(
            "SELECT target_type, target_id FROM memory_edges WHERE project_id = ? "
            "AND valid_to IS NULL AND source_type = 'code_symbol' AND source_id = ? "
            "AND relation = 'calls' LIMIT 240",
            (project.project_id, 1),
        ).fetchall(),
        "incoming_edges": lambda: conn.execute(
            "SELECT source_type, source_id FROM memory_edges WHERE project_id = ? "
            "AND valid_to IS NULL AND target_type = 'code_symbol' AND target_id = ? "
            "AND relation = 'calls' LIMIT 240",
            (project.project_id, 2),
        ).fetchall(),
    }
    return {
        name: measure_operation(operation, repetitions, SLO_MS[name])
        for name, operation in operations.items()
    }


def measure_operation(
    operation: Callable[[], Any],
    repetitions: int,
    target_ms: float,
) -> dict[str, Any]:
    operation()
    samples: list[float] = []
    for _index in range(repetitions):
        started = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started) * 1000.0)
    ordered = sorted(samples)
    p95 = ordered[int(round((len(ordered) - 1) * 0.95))]
    return {
        "samples": len(samples),
        "p50_ms": round(ordered[len(ordered) // 2], 3),
        "p95_ms": round(p95, 3),
        "target_p95_ms": target_ms,
        "pass": p95 <= target_ms,
    }


def benchmark_query_plans(
    conn: sqlite3.Connection,
    project_id: str,
) -> dict[str, dict[str, Any]]:
    definitions = {
        "qualified_symbol_lookup": (
            "SELECT id FROM code_symbols WHERE project_id = ? AND qualified_name = ? LIMIT 20",
            (project_id, "Service1.CriticalPaymentRetryHandler.1"),
            "idx_code_symbols_project_qualified_lookup",
        ),
        "file_symbols": (
            "SELECT id FROM code_symbols WHERE project_id = ? AND file_path = ? LIMIT 220",
            (project_id, file_path(1)),
            ("idx_code_symbols_project_file", "idx_code_symbols_project_qualified"),
        ),
        "outgoing_edges": (
            "SELECT target_id FROM memory_edges WHERE project_id = ? AND valid_to IS NULL "
            "AND source_type = 'code_symbol' AND source_id = ? AND relation = 'calls' LIMIT 240",
            (project_id, 1),
            "idx_memory_edges_project_valid_source_relation",
        ),
        "incoming_edges": (
            "SELECT source_id FROM memory_edges WHERE project_id = ? AND valid_to IS NULL "
            "AND target_type = 'code_symbol' AND target_id = ? AND relation = 'calls' LIMIT 240",
            (project_id, 2),
            "idx_memory_edges_project_valid_target_relation",
        ),
    }
    result: dict[str, dict[str, Any]] = {}
    for name, (sql, params, required_index) in definitions.items():
        details = [
            str(row[3]) for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
        ]
        accepted = (
            list(required_index) if isinstance(required_index, tuple) else [required_index]
        )
        result[name] = {
            "details": details,
            "accepted_indexes": accepted,
            "pass": any(index in detail for index in accepted for detail in details),
        }
    return result


def observed_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in ("code_files", "code_symbols", "code_log_statements", "memory_edges")
    }
    counts["searchable_entities"] = (
        counts["code_files"] + counts["code_symbols"] + counts["code_log_statements"]
    )
    return counts


def profile_counts(profile: ScaleProfile) -> dict[str, int]:
    return {
        "searchable_entities": profile.entity_count,
        "code_files": profile.file_count,
        "code_symbols": profile.symbol_count,
        "code_log_statements": profile.log_count,
        "memory_edges": profile.edge_count,
    }


def database_bytes(path: Path) -> int:
    return sum(
        candidate.stat().st_size
        for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm"))
        if candidate.exists()
    )


def file_path(file_id: int) -> str:
    return f"src/domain{file_id % 100:02d}/Service{file_id}.ets"
