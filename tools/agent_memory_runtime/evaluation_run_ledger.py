# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .benchmark_case_seal import case_pack_seal_audit
from .models import Project
from .storage import connect, now_iso


RUN_KINDS = {"context_capability", "agent_benchmark"}


@contextmanager
def evaluation_run_guard(
    project: Project,
    pack: dict[str, Any],
    run_kind: str,
    case_file: str | Path,
) -> Iterator[dict[str, Any] | None]:
    reservation = reserve_evaluation_run(project, pack, run_kind, case_file)
    try:
        yield reservation
    except BaseException as exc:
        fail_evaluation_run(project, reservation, exc)
        raise
    else:
        complete_evaluation_run(project, reservation)


def reserve_evaluation_run(
    project: Project,
    pack: dict[str, Any],
    run_kind: str,
    case_file: str | Path,
) -> dict[str, Any] | None:
    if run_kind not in RUN_KINDS:
        raise ValueError(f"unsupported evaluation run kind: {run_kind}")
    identity = holdout_identity(pack)
    if identity is None:
        return None
    with connect(project) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if run_kind == "agent_benchmark":
            require_context_predecessor(conn, project.project_id, identity)
        try:
            cursor = conn.execute(
                """
                INSERT INTO evaluation_runs(
                  project_id, run_kind, seal_digest, case_file, status, started_at
                ) VALUES (?, ?, ?, ?, 'running', ?)
                """,
                (
                    project.project_id,
                    run_kind,
                    identity,
                    str(Path(case_file).expanduser()),
                    now_iso(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            row = conn.execute(
                """
                SELECT status, started_at FROM evaluation_runs
                WHERE project_id = ? AND run_kind = ? AND seal_digest = ?
                """,
                (project.project_id, run_kind, identity),
            ).fetchone()
            detail = f"{row['status']} since {row['started_at']}" if row else "already reserved"
            raise SystemExit(
                f"sealed holdout {run_kind} is already consumed or reserved: {detail}"
            ) from exc
        conn.commit()
    return {
        "id": int(cursor.lastrowid),
        "seal_digest": identity,
        "run_kind": run_kind,
        "gate_status": None,
        "result": None,
    }


def holdout_identity(pack: dict[str, Any]) -> str | None:
    governance = pack.get("evaluation_governance")
    if not isinstance(governance, dict) or not governance.get("enforced"):
        return None
    if governance.get("split") != "holdout":
        return None
    seal = case_pack_seal_audit(pack)
    if seal.get("status") != "verified" or not seal.get("required"):
        raise SystemExit("holdout run ledger requires a verified required seal")
    return str(seal["digest"])


def require_context_predecessor(
    conn: sqlite3.Connection,
    project_id: str,
    seal_digest: str,
) -> None:
    row = conn.execute(
        """
        SELECT status, gate_status FROM evaluation_runs
        WHERE project_id = ? AND run_kind = 'context_capability' AND seal_digest = ?
        """,
        (project_id, seal_digest),
    ).fetchone()
    if row is None:
        raise SystemExit("sealed holdout Agent A/B requires a recorded Context run")
    if row["status"] != "completed" or row["gate_status"] != "pass":
        raise SystemExit("sealed holdout Agent A/B requires a completed passing Context gate")


def complete_evaluation_run(project: Project, reservation: dict[str, Any] | None) -> None:
    if reservation is None:
        return
    result = reservation.get("result")
    digest = canonical_digest(result) if isinstance(result, dict) else None
    update_run(
        project,
        reservation,
        status="completed",
        gate_status=str(reservation.get("gate_status") or "unknown"),
        result_digest=digest,
    )


def fail_evaluation_run(
    project: Project,
    reservation: dict[str, Any] | None,
    error: BaseException,
) -> None:
    if reservation is None:
        return
    update_run(
        project,
        reservation,
        status="failed",
        error_class=type(error).__name__,
    )


def update_run(
    project: Project,
    reservation: dict[str, Any],
    *,
    status: str,
    gate_status: str | None = None,
    result_digest: str | None = None,
    error_class: str | None = None,
) -> None:
    with connect(project) as conn:
        cursor = conn.execute(
            """
            UPDATE evaluation_runs
            SET status = ?, gate_status = ?, result_digest = ?, error_class = ?,
                finished_at = ?
            WHERE id = ? AND status = 'running'
            """,
            (
                status,
                gate_status,
                result_digest,
                error_class,
                now_iso(),
                reservation["id"],
            ),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("evaluation run reservation is no longer active")
        conn.commit()


def canonical_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
