# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from pathlib import Path

from .models import Project
from .normative_documents import observe_document_source
from .storage import connect, now_iso
from .vault_common import (
    clear_markdown_files, frontmatter, slugify, truncation_notice, write_vault_file,
)


def write_normative_vault(project: Project) -> None:
    with connect(project) as conn:
        total = int(conn.execute(
            "SELECT COUNT(*) FROM normative_documents WHERE project_id = ?",
            (project.project_id,),
        ).fetchone()[0])
        rows = [dict(row) for row in conn.execute(
            """SELECT * FROM normative_documents WHERE project_id = ?
               ORDER BY kind, document_id, source_root, file_path LIMIT 500""",
            (project.project_id,),
        ).fetchall()]
    folder = project.vault_dir / "Normative Context"
    clear_markdown_files(folder)
    notice = (
        "> Generated SQLite snapshot. Approval and normative text belong to the original Git "
        "document. Read its current source before treating it as a project constraint; "
        "editing this mirror does not approve or update a specification.\n\n"
    )
    index = frontmatter("normative-context-index", project, now_iso())
    index += "# ADR and Feature Spec References\n\n" + notice
    index += truncation_notice(total, len(rows))
    for row in rows:
        stem = f"{row['id']:04d}-{slugify(row['document_id'], 'document')}"
        approval = json.loads(row["approval"])
        content = frontmatter("normative-context-mirror", project, row["updated_at"])
        content += f"# {row['title']}\n\n" + notice
        source_path = Path(row["source_root"]) / row["file_path"]
        if source_path.is_absolute():
            content += f"[Open original Git document](<{source_path.as_uri()}>)\n\n"
        freshness, observed_digest = observe_document_source(row)
        if freshness != "current":
            content += (
                f"> Source freshness: {freshness}. The indexed snapshot below is not "
                "current-source evidence. Read or restore the original and refresh its "
                "existing learned scope before using its content.\n\n"
            )
        fields = {
            "Document ID": row["document_id"], "Kind": row["kind"], "Declared status": row["status"],
            "Source": f"{row['source_root']}/{row['file_path']}",
            "Indexed revision": row["source_revision"] or "unknown",
            "Indexed source digest": row["source_digest"],
            "Observed source digest": observed_digest or "unavailable",
            "Source freshness": freshness,
            "Scope": ", ".join(json.loads(row["scopes"])),
            "Owner": approval.get("owner"), "Declared approver": approval.get("approved_by"),
            "Declared approval date": approval.get("approved_at"),
            "Approval reference": approval.get("approval_ref"),
            "Supersedes": row["supersedes"], "Superseded by": row["superseded_by"],
        }
        content += "\n".join(f"- {key}: {value}" for key, value in fields.items() if value)
        content += "\n\n## Indexed Source Snapshot\n\n" + row["body"] + "\n"
        write_vault_file(folder / f"{stem}.md", content)
        index += (
            f"- [[Normative Context/{stem}|{row['document_id']}]] "
            f"({row['kind']}, {row['status']}, source: {freshness})\n"
        )
    write_vault_file(folder / "index.md", index)
