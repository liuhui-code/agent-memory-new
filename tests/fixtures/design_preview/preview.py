# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Isolated preview case. No HTTP, database, worker service, or Runtime entry."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Iterable, Mapping


@dataclass(frozen=True)
class PreviewRow:
    kind: str
    record_id: int
    text: str


@dataclass(frozen=True, eq=False)
class PreviewJob:
    # sequence is diagnostic; the live in-process handle is the authority.
    sequence: int
    rows: tuple[PreviewRow, ...]


@dataclass(frozen=True)
class RenderedPreview:
    media_type: str
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.media_type, str) or not self.media_type or not isinstance(self.text, str):
            raise TypeError("preview payload requires strings")


@dataclass(frozen=True)
class PreviewState:
    status: str = "idle"
    sequence: int | None = None
    result: RenderedPreview | None = None
    error: str | None = None


class PreviewCoordinator:
    def __init__(self, max_rows: int = 100) -> None:
        if type(max_rows) is not int or max_rows < 1:
            raise ValueError("max_rows must be positive")
        self._max_rows = max_rows
        self._lock = Lock()
        self._sequence = 0
        self._active: PreviewJob | None = None
        self._state = PreviewState()

    @property
    def state(self) -> PreviewState:
        with self._lock:
            return self._state

    def request(self, rows: Iterable[Mapping[str, object]]) -> PreviewJob:
        # Callers own the input while this copies it. No database snapshot is implied.
        snapshot = []
        for row in rows:
            if len(snapshot) >= self._max_rows:
                raise ValueError("too many selected rows")
            kind, record_id, text = row["kind"], row["id"], row["text"]
            if not isinstance(kind, str) or not kind or type(record_id) is not int or record_id < 1 or not isinstance(text, str):
                raise ValueError("invalid selected row")
            snapshot.append(PreviewRow(kind, record_id, text))
        if not snapshot:
            raise ValueError("empty selection")
        with self._lock:
            self._sequence += 1
            job = PreviewJob(self._sequence, tuple(snapshot))
            self._active = job
            self._state = PreviewState("running", job.sequence)
            return job

    def complete(self, job: PreviewJob, result: RenderedPreview) -> bool:
        with self._lock:
            if self._active is None or self._active is not job:
                return False
            if not isinstance(result, RenderedPreview):
                raise TypeError("invalid preview payload")
            self._active = None
            self._state = PreviewState("ready", job.sequence, result)
            return True

    def cancel(self, job: PreviewJob) -> bool:
        with self._lock:
            if self._active is None or self._active is not job:
                return False
            self._active = None
            self._state = PreviewState("cancelled", job.sequence)
            return True

    def fail(self, job: PreviewJob, reason: str) -> bool:
        if not isinstance(reason, str):
            raise TypeError("failure reason must be text")
        with self._lock:
            if self._active is None or self._active is not job:
                return False
            self._active = None
            self._state = PreviewState("failed", job.sequence, error=reason)
            return True
