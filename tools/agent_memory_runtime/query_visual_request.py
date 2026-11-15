# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite affirmative OR request; observation never selects owner identity."""
import re
_NOUN = r'[A-Za-z]+(?: [A-Za-z]+){0,4}'
_REQUEST = re.compile(r'(?:(?P<left>'+_NOUN+r') covers (?P<right>'+_NOUN+r')\. )?'
    r'(?:Return|Locate|Find) the (?:stacking or background styling|background styling or stacking) source\.?', re.I | re.ASCII)
_RESERVED = set('and or not no never only except exclude excluding without neither nor rather return find locate source code render generate caller wrapper must should please'.split())


def visual_alternative_request(query):
    if not isinstance(query, str) or len(query) > 400:
        return False
    match = _REQUEST.fullmatch(query)
    return bool(match and not any(set((match[k] or '').lower().split()) & _RESERVED
                                 for k in ('left', 'right')))
