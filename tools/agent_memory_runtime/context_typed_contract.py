# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Exact declaration requests are not callable-local queries."""
from __future__ import annotations
from typing import Any
from .query_typed_contract import classify_contract
from .query_definition_identity import TYPE_DEFINITION_KINDS


def declaration_projection(anchors: list[dict[str, Any]], query: str,
                           path_context: dict[str, Any]) -> list[dict[str, Any]] | None:
    if path_context.get('activated') or path_context.get('wrapped_log_evidence'):
        return None
    contract = classify_contract(query)
    if not contract or contract.get('kind') != 'declaration':
        return None
    selected = [item for item in anchors
                if item.get('symbol') == contract.get('identifier')
                and item.get('symbol_type') in TYPE_DEFINITION_KINDS]
    return selected or None
