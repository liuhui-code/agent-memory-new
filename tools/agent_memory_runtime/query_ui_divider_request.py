# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Complete static-property request, with an opaque textual owner qualifier."""
import re
from .text import identifier_parts

FORM = re.compile(r'(?:Find|Locate) the (?:ArkTS )?([a-z]+) divider stroke width implementation\.?')
RESERVED = set('and or not only both except exclude instead without return find locate source code context generate generated instruction call caller wrapper literal log api import boundary'.split())


def divider_request(query):
    if not isinstance(query, str) or len(query) > 240:
        return None
    match = FORM.fullmatch(query)
    if match is None or match[1] in RESERVED:
        return None
    return match[1]


def qualifier_matches(qualifier, owner):
    if (not isinstance(qualifier, str) or not isinstance(owner, str)
            or re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', owner) is None):
        return False
    return qualifier in (identifier_parts(owner) or [owner.lower()])
