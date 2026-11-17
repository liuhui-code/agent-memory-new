# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Mechanical orchestration of existing opt-in context trial hooks.

No request recognition, qualification, focus or authority rules live here.
Keep the existing lifecycle-before-output qualification and background-before-
source-trial wrapping order; each producer retains its own authority contract.
"""


def qualify_context_trials(project, query, gated, *, allow_lifecycle=False, allow_output_loop=False):
    authority = None
    if allow_lifecycle:
        from .query_lifecycle_selection import qualify_lifecycle
        authority = qualify_lifecycle(project, query, gated["matches"].get("wiki_matches") or [])
    output_authority = None
    if allow_output_loop:
        from .query_output_loop_selection import qualify_output_loop, output_loop_focus
        items = gated['matches'].get('wiki_matches') or []
        output_authority = qualify_output_loop(project, query, items)
        focused = output_loop_focus(output_authority, query, items)
        if focused is not None:
            gated = {**gated, 'matches': {**gated['matches'], 'wiki_matches': focused}}
    return gated, authority, output_authority


def bind_context_trials(query, context, items, *, allow_render_recall=False,
                        authority=None, output_authority=None):
    if allow_render_recall:
        from .query_render_selection import retain_background_candidates
        context = retain_background_candidates(query, context, items)
    if authority is not None:
        from .query_lifecycle_selection import LifecycleTrial
        context = LifecycleTrial(context)
        context._lifecycle_authority = authority
        from copy import deepcopy
        context._lifecycle_pool = deepcopy(items)
        from .query_lifecycle_selection import snapshot
        context._lifecycle_pool_binding = snapshot(items)
    if output_authority is not None:
        from .query_output_loop_selection import OutputLoopTrial
        context = OutputLoopTrial(context)
        context._output_loop_authority = output_authority
    return context


def bind_source_views(project, query, context, items):
    """Existing terminal view order, then the opt-in static UI property view."""
    from .query_record_loop_selection import bind_record_loop_context
    from .query_archive_create_write_selection import bind_archive_create_write_context
    from .query_command_table_selection import bind_command_table_context
    from .query_ui_divider_selection import bind_divider_context
    context = bind_record_loop_context(project, query, context, items)
    context = bind_archive_create_write_context(project, query, context, items)
    context = bind_command_table_context(project, query, context, items)
    from .query_ui_gesture_selection import bind_gesture_context
    context = bind_divider_context(project, query, context, items)
    context = bind_gesture_context(project, query, context, items)
    from .query_ui_vertical_selection import bind_vertical_context
    context = bind_vertical_context(project, query, context, items)
    from .query_sql_slot_selection import bind_sql_slot_context
    return bind_sql_slot_context(project, query, context, items)
