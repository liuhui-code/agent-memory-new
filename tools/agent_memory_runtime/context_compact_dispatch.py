"""Mechanical private-view dispatch; each view retains its own authority."""
from typing import Any

def dispatch_compact_context(data: dict[str, Any], _compact_context) -> dict[str, Any]:
    from .query_sql_slot_selection import SqlSlotContext, compact_sql_slot
    if isinstance(data, SqlSlotContext):
        return compact_sql_slot(data, _compact_context(dict(data)))
    from .query_touch_index_selection import TouchIndexContext, compact_touch_index
    if isinstance(data, TouchIndexContext):
        return compact_touch_index(data, _compact_context(dict(data)))
    from .query_ui_vertical_selection import VerticalContext, compact_vertical
    if isinstance(data, VerticalContext):
        return compact_vertical(data, _compact_context(dict(data)))
    from .query_ui_gesture_selection import GestureContext, compact_gesture
    if isinstance(data, GestureContext):
        return compact_gesture(data, _compact_context(dict(data)))
    from .query_ui_divider_selection import DividerContext, compact_divider
    if isinstance(data, DividerContext):
        return compact_divider(data, _compact_context(dict(data)))
    from .query_command_table_selection import CommandTableContext, compact_command_table
    if isinstance(data, CommandTableContext):
        return compact_command_table(data, _compact_context(dict(data)))
    from .query_lifecycle_log_context import LifecycleLogContext, compact_lifecycle_log_context
    if isinstance(data, LifecycleLogContext):
        return compact_lifecycle_log_context(data, _compact_context(dict(data)))
    from .query_archive_create_write_selection import ArchiveCreateWriteContext, compact_archive_create_write
    if isinstance(data, ArchiveCreateWriteContext):
        return compact_archive_create_write(data, _compact_context(dict(data)))
    from .query_record_loop_selection import RecordLoopContext, compact_record_loop
    if isinstance(data, RecordLoopContext):
        return compact_record_loop(data, _compact_context(dict(data)))
    from .query_cache_scan_selection import cache_scan_context_view
    data, cache_scan_receipts = cache_scan_context_view(data)
    if cache_scan_receipts:
        return _compact_context(data, cache_scan_receipts=cache_scan_receipts)
    from .query_command_selection import command_context_view
    data, command_receipts = command_context_view(data)
    if command_receipts:
        return _compact_context(data, command_receipts=command_receipts)
    from .query_render_selection import render_context_view, attach_render_excerpts
    data, render_receipts = render_context_view(data)
    from .query_lifecycle_selection import lifecycle_context_view
    data, lifecycle_receipts = lifecycle_context_view(data)
    if lifecycle_receipts:
        return _compact_context(data, lifecycle_receipts=lifecycle_receipts)
    from .query_output_loop_selection import output_loop_context_view
    data, output_loop_receipts = output_loop_context_view(data)
    if output_loop_receipts:
        return _compact_context(data, output_loop_receipts=output_loop_receipts)
    from .query_recovery_pair import valid, accepted_output, complete_added_snapshots
    handoff = data.get("query_handoff") or {}
    if not render_receipts and valid(handoff, handoff.get("code_anchors") or [], data.get("query")):
        baseline = _compact_context({**data, "query_handoff": dict(handoff)})
        candidate = complete_added_snapshots(handoff, baseline, _compact_context(data))
        return candidate if accepted_output(handoff, baseline, candidate) else baseline
    return _compact_context(data, render_receipts)
