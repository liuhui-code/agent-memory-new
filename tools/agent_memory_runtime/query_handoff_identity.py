# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Display deduplication only; these keys are not source-reading authority."""
from typing import Any


def anchor_display_key(item: dict[str, Any], source: str) -> tuple[Any, ...]:
    base = (str(item.get('file_path') or ''), str(item.get('symbol') or item.get('function') or ''))
    identifier = item.get('id')
    start, end = item.get('start_line'), item.get('end_line')
    known_symbol = (bool(base[1].strip()) and source == 'wiki' and item.get('kind') == 'symbol'
                    and type(identifier) is int and identifier > 0
                    and type(start) is int and type(end) is int and 0 < start <= end)
    # Bounds validate the projection, not distinct identities for one record.
    return (*base, 'code_symbol', identifier) if known_symbol else base


def display_key_seen(key: tuple[Any, ...], seen: set[tuple[Any, ...]]) -> bool:
    # Legacy/file/log collisions retain their prior coarse suppression policy.
    # Only two known, shape-validated code-symbol records may be distinguished by this change.
    return any((len(prior) == len(key) == 4 and prior[2:] == key[2:])
               or (prior[:2] == key[:2] and (len(prior) == 2 or len(key) == 2))
               for prior in seen)
