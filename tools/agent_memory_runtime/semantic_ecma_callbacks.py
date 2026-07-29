# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .ecma_callable_ranges import callback_ranges_for_language


def callback_callable_specs(
    lines: list[str], language: str, containers: list[Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in callback_ranges_for_language(lines, language):
        start = int(item["start_line"]) - 1
        end = int(item["end_line"]) - 1
        container = containing_container(containers, start, end)
        name = str(item["symbol"])
        owner = str(container.name) if container is not None else ""
        qualified = f"{owner}.{name}@{start + 1}" if owner else f"{name}@{start + 1}"
        result.append({
            "name": name,
            "owner": owner,
            "owner_kind": container.entity.owner_kind if container is not None else "module",
            "qualified_name": qualified,
            "signature": f"callback {name}@{start + 1}",
            "start": start,
            "end": end,
        })
    return result


def containing_container(
    containers: list[Any], start: int, end: int,
) -> Any | None:
    matches = [
        item for item in containers
        if int(item.start) <= start and end <= int(item.end)
    ]
    return min(matches, key=lambda item: int(item.end) - int(item.start)) if matches else None
