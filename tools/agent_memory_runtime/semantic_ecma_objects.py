# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
import re

from .ecma_braces import block_end


OBJECT_CONTAINER_RE = re.compile(
    r"^\s*(export\s+)?(?:default\s+)?const\s+([A-Za-z_$][\w$]*)"
    r"(?:\s*:[^=]+)?\s*=\s*\{"
)


@dataclass(frozen=True)
class ObjectContainerSpec:
    name: str
    start: int
    end: int
    exported: bool


def object_container_specs(lines: list[str]) -> list[ObjectContainerSpec]:
    """Locate named ECMA object literals that own callable properties."""
    result: list[ObjectContainerSpec] = []
    for index, line in enumerate(lines):
        match = OBJECT_CONTAINER_RE.match(line)
        if match is None:
            continue
        result.append(ObjectContainerSpec(
            name=match.group(2),
            start=index,
            end=block_end(lines, index),
            exported=bool(match.group(1)),
        ))
    return result
