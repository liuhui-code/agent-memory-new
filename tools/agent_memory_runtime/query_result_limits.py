# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Unchanged log diversity truncation helper, re-exported by query_results."""
from typing import Any


def diverse_log_matches(
    values: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    selected = list(values[:limit])
    selected_ids = {id(item) for item in selected}
    wrapped = [item for item in values if item.get("kind") == "log_effect"][:2]
    for item in wrapped:
        if id(item) in selected_ids:
            continue
        replace_at = next(
            (index for index in range(len(selected) - 1, -1, -1)
             if selected[index].get("kind") != "log_effect"),
            None,
        )
        if replace_at is None:
            break
        selected_ids.discard(id(selected[replace_at]))
        selected[replace_at] = item
        selected_ids.add(id(item))
    positions = {id(item): index for index, item in enumerate(values)}
    return sorted(selected, key=lambda item: positions.get(id(item), len(values)))
