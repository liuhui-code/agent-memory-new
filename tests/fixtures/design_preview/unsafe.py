# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Deliberately wrong control: mutable input and unscoped completion."""

from dataclasses import dataclass


@dataclass
class UnsafeJob:
    sequence: int
    rows: list[dict]


class UnsafePreview:
    def __init__(self) -> None:
        self.sequence = 0
        self.result: tuple[int, str] | None = None

    def request(self, rows: list[dict]) -> UnsafeJob:
        self.sequence += 1
        return UnsafeJob(self.sequence, rows)

    def complete(self, job: UnsafeJob, text: str) -> None:
        self.result = (job.sequence, text)
