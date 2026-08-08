# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import shlex
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
QUERY_SKILL = REPO_ROOT / "skills" / "agent-memory-query"
BINDING_SCHEMA = "selective-query-skill-binding/v1"
SELECTIVE_QUERY_LIMIT = 3
SOURCE_STATE_EXCLUDES = {".git", ".agent-memory-benchmark"}


def prepare_selective_query_skill(
    home: Path,
    memory_access: dict[str, Any],
    query_limit: int,
) -> str:
    source = QUERY_SKILL
    target = home / ".agents" / "skills" / "agent-memory-query"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    command = bound_query_command(memory_access)
    binding = (
        "\n## Benchmark Binding\n\n"
        "This isolated benchmark exposes the existing Query Skill without preloading "
        "Context. For a focused diagnosis query, run the exact bound command below, "
        f"replacing `<focused-query>`. Invoke it at most {max(0, int(query_limit))} times. "
        "Do not inspect the Memory database, vault, or runtime snapshots directly.\n\n"
        f"```bash\n{command}\n```\n"
    )
    skill = target / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + binding, encoding="utf-8")
    return skill_contract_digest(source, max(0, int(query_limit)))


def bound_query_command(memory_access: dict[str, Any]) -> str:
    value = memory_access.get("query_command")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit("selective query treatment requires memory_access.query_command")
    parts = [
        "<focused-query>"
        if item in {"<task-description>", "<task-description-or-agent-extracted-term>"}
        else item
        for item in value
    ]
    return shlex.join(parts)


def skill_contract_digest(source: Path, query_limit: int) -> str:
    digest = hashlib.sha256()
    digest.update(BINDING_SCHEMA.encode("utf-8"))
    digest.update(str(query_limit).encode("ascii"))
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(source)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def workspace_source_digest(workspace: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in workspace.rglob("*") if item.is_file()):
        relative = path.relative_to(workspace)
        if relative.parts and relative.parts[0] in SOURCE_STATE_EXCLUDES:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def telemetry_context(metrics: dict[str, Any]) -> dict[str, Any]:
    primary = set(metrics.get("memory_query_primary_anchor_paths") or [])
    anchors = [
        {
            "file_path": path,
            "role": "primary" if path in primary else "expansion",
        }
        for path in metrics.get("memory_query_anchor_paths") or []
    ]
    return {"query_handoff": {"code_anchors": anchors}}
