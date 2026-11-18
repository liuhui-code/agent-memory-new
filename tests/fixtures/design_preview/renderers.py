# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Pure render functions; the preview state owner does not execute rendering."""

import json

from .preview import PreviewJob, RenderedPreview


def render_text(job: PreviewJob) -> RenderedPreview:
    return RenderedPreview("text/plain", "\n".join(
        f"[{row.kind}:{row.record_id}] {row.text}" for row in job.rows
    ))


def render_json(job: PreviewJob) -> RenderedPreview:
    rows = [{"kind": row.kind, "id": row.record_id, "text": row.text} for row in job.rows]
    return RenderedPreview("application/json", json.dumps(rows, ensure_ascii=False))
