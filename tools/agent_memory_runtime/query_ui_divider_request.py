# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Complete static-property request, with an opaque textual owner qualifier."""
import re
from .text import identifier_parts

FORM = re.compile(r'(?:Find|Locate) the (?:ArkTS )?([a-z]+) divider stroke width implementation\.?')
CONTEXT_FORM = re.compile(r'The ([a-z]+) list separator has (?:the wrong|an incorrect) thickness\. (?:Return|Locate) the (?:ArkTS )?behavior owner and (?P<adjective>current) source window\.?')
RESERVED = set('and or not only both except exclude instead without return find locate source code context generate generated instruction call caller wrapper literal log api import boundary'.split())


def divider_request(query):
    if not isinstance(query, str) or len(query) > 240:
        return None
    from .query_ui_divider_multilingual_request import parse_multilingual_divider_request
    multilingual = parse_multilingual_divider_request(query)
    if multilingual is not None:
        return multilingual
    match = FORM.fullmatch(query) or CONTEXT_FORM.fullmatch(query)
    if match is None or match[1] in RESERVED:
        return None
    return match[1]


def qualifier_matches(qualifier, owner):
    if (not isinstance(qualifier, str) or not isinstance(owner, str)
            or re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', owner) is None):
        return False
    return qualifier in (identifier_parts(owner) or [owner.lower()])


def divider_identity_query(query):
    """Name-check projection only; never use this text for retrieval or logs."""
    from .query_ui_divider_multilingual_request import parse_multilingual_divider_request, project_negative_names
    multilingual = parse_multilingual_divider_request(query)
    if multilingual is not None:
        return project_negative_names(query, multilingual)
    if divider_request(query) is None:
        return query
    match = CONTEXT_FORM.fullmatch(query)
    if match is None:
        return query
    start, end = match.span('adjective')
    return query[:start] + ' ' * (end - start) + query[end:]
