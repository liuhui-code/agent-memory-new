# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from pathlib import Path

from .models import Project

VAULT_EPISODE_EXPORT_LIMIT = 500
VAULT_REFLECTION_EXPORT_LIMIT = 500
VAULT_FACT_SUMMARY_LIMIT = 1000
VAULT_FILE_SUMMARY_LIMIT = 1000
VAULT_SYMBOL_SUMMARY_LIMIT = 1500
VAULT_LOG_SUMMARY_LIMIT = 1500
VAULT_EDGE_SUMMARY_LIMIT = 1500



def slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text.strip().lower()).strip("-")
    return slug[:80] or fallback



def frontmatter(record_type: str, project: Project, created_at: str) -> str:
    return (
        "---\n"
        f"type: {record_type}\n"
        f"project_id: {project.project_id}\n"
        f"created_at: {created_at}\n"
        "tags:\n"
        "  - agent-memory\n"
        f"  - {record_type}\n"
        "---\n\n"
    )



def write_vault_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")



def clear_markdown_files(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for markdown_file in path.glob("*.md"):
        markdown_file.unlink()



def truncation_notice(total_count: int, exported_count: int) -> str:
    if exported_count >= total_count:
        return ""
    return (
        f"> Truncated vault export: showing {exported_count} of {total_count} records. "
        "Use the SQLite runtime for full machine-readable history.\n\n"
    )
