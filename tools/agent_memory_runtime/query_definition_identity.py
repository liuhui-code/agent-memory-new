# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any


TYPE_DEFINITION_KINDS = {
    "class", "component", "enum", "interface", "object", "struct",
}
DIRECT_IDENTITY_REASONS = {"exact_identifier", "exact_symbol"}


def explicit_definition_identity(item: dict[str, Any]) -> bool:
    """True only for a directly matched type declaration, not a reference."""
    if str(item.get("kind") or "") != "symbol":
        return False
    if str(item.get("symbol_type") or "").casefold() not in TYPE_DEFINITION_KINDS:
        return False
    return bool(DIRECT_IDENTITY_REASONS & set(item.get("match_reasons") or []))


def explicit_owner_identity_match(query: str, owner_name: object) -> bool:
    owner = str(owner_name or "").strip()
    if len(owner) < 3:
        return False
    normalized_query = re.sub(r"[^a-z0-9_$]", " ", query.casefold())
    normalized_owner = re.sub(r"[^a-z0-9_$]", "", owner.casefold())
    return bool(normalized_owner) and normalized_owner in normalized_query.split()
