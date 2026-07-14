# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


EVIDENCE_RANK = {"exact": 4, "static": 3, "heuristic": 2, "inferred": 1}


@dataclass(frozen=True)
class DesignEdgeObservation:
    source: str
    relation: str
    target: str
    confidence: float
    evidence: str
    evidence_class: str


class LanguageEvidenceAdapter(Protocol):
    language: str

    def extract(self, file_path: str, source: str) -> list[DesignEdgeObservation]: ...


def evidence_class(evidence_kind: str, extractor_version: str) -> str:
    kind = evidence_kind.lower()
    if kind.startswith("compiler_") or kind.startswith("symbol_index_"):
        return "exact"
    if kind.startswith("exact_semantic_"):
        return "exact"
    if kind.startswith("static_semantic_"):
        return "static"
    if kind in {
        "static_containment", "static_import", "static_route", "static_resource",
        "static_state", "static_event_dispatch", "static_event_binding",
        "static_configuration", "static_call", "static_state_read", "static_state_write",
        "static_implementation", "static_override", "static_api_export", "static_api_use",
        "static_callback",
    }:
        return "static"
    if kind.startswith("static_") or "heuristic" in kind:
        return "heuristic"
    return "inferred" if extractor_version == "legacy" else "heuristic"
