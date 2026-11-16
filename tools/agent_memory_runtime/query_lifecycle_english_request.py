# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite joint-role request; observation words grant no source identity or facts."""
import re

HEAD = r'(?:find|locate|return) the (?:owner|coordinator) (?:combining|owning|that combines|that owns) (?:lifecycle restore|restore lifecycle), (?:current state|current text state|state update), and (?:storage commit|persistence)'
OBSERVATION = r'Restart loses the saved (?P<label>[a-z]{1,24}(?: [a-z]{1,24}){0,3}); '
NEW_OBSERVATION = r'(?:A|The) saved (?P<label>[a-z]{1,24}(?: [a-z]{1,24}){0,3}) (?:resets|is cleared) after (?:relaunch|restart)\. '
NEW_REQUEST = re.compile(rf'{NEW_OBSERVATION}{HEAD}\.?', re.I | re.ASCII)
REQUEST = re.compile(rf'(?:{OBSERVATION})?{HEAD}\.?', re.I | re.ASCII)
RESERVED = set('and or not no only except exclude excluding without return find locate show source code generated literal quoted both owner coordinator state restore commit lifecycle save storage'.split())


def english_lifecycle_request(query):
    if not isinstance(query,str) or len(query)>240:
        return False
    match=REQUEST.fullmatch(query) or NEW_REQUEST.fullmatch(query)
    if match is None:
        return False
    label=match['label']
    if label is not None:
        # Fixed terminals are case-insensitive; descriptive NP is lowercase on
        # original bytes, so a camel-case source identifier cannot acquire scope.
        if re.fullmatch(r'[a-z]{1,24}(?: [a-z]{1,24}){0,3}',label) is None or set(label.split()) & RESERVED:
            return False
    return True
