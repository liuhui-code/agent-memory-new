# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3

from .models import Project
from .records import row_dict
from .storage import now_iso
from .vault_common import frontmatter, write_vault_file

def write_incident_trace_vault_pages(project: Project, incident_traces: list[sqlite3.Row]) -> None:
    header = frontmatter("codebase-wiki", project, now_iso())
    notice = "This file is generated. Edit memory through agent-memory-maintain or runtime commands.\n\n"
    rows = [row_dict(row) for row in incident_traces]
    wiki_doc = header + "# Incident Traces\n\n" + notice
    wiki_doc += "These are compact ArkTS incident summaries. Raw runtime logs are not persisted here.\n\n"
    for row in rows[:50]:
        wiki_doc += f"- trace #{row['id']} ({row['status']}, {row['arkts_scene']}): {row['symptom']}\n"
        if row.get("normalized_error"):
            wiki_doc += f"  - event: {row['normalized_error']}\n"
        if row.get("resolution"):
            wiki_doc += f"  - resolution: {row['resolution']}\n"
    write_vault_file(project.vault_dir / "Codebase Wiki" / "incident-traces.md", wiki_doc)

    review_doc = frontmatter("governance", project, now_iso()) + "# Incident Trace Review\n\n" + notice
    for row in rows[:50]:
        if row.get("status") in {"stale", "ignored"}:
            continue
        review_doc += f"- trace #{row['id']} ({row['status']}, {row['arkts_scene']}): {row['symptom']}\n"
        review_doc += "  - review: resolve, ignore, mark stale, or promote to reflection after source verification\n"
    write_vault_file(project.vault_dir / "Governance" / "Incident Trace Review.md", review_doc)
