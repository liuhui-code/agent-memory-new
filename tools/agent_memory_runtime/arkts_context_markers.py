# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from .arkts_behavior_markers import extract_arkts_behavior_markers
from .arkts_context_contracts import extract_arkts_context_contracts


def extract_arkts_context_markers(text: str) -> list[str]:
    return list(dict.fromkeys([
        *extract_arkts_behavior_markers(text),
        *extract_arkts_context_contracts(text),
    ]))
