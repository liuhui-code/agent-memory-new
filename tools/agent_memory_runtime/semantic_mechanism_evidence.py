# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json

from .semantic_models import SemanticMechanism
from .text import unique_list


MAX_MECHANISM_EVIDENCE_BYTES = 4096


def mechanism_evidence_payload(
    mechanisms: list[SemanticMechanism],
) -> tuple[str, str]:
    records: list[dict[str, object]] = []
    for item in mechanisms:
        candidate = [*records, item.to_dict()]
        encoded = json.dumps(
            candidate, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
        if len(encoded.encode("utf-8")) > MAX_MECHANISM_EVIDENCE_BYTES:
            break
        records = candidate
    retained = mechanisms[:len(records)]
    terms = unique_list(
        term
        for item in retained
        for term in (item.kind, item.kind.replace("_", ""), *item.terms)
    )
    return (
        json.dumps(records, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        " ".join(terms),
    )


def mechanism_search_terms(payload: object) -> str:
    try:
        records = json.loads(str(payload or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return ""
    if not isinstance(records, list):
        return ""
    terms: list[str] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        values = item.get("terms") if isinstance(item.get("terms"), list) else []
        terms.extend([kind, kind.replace("_", ""), *(str(term) for term in values)])
    return " ".join(unique_list(term for term in terms if term))
