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
