"""Frozen English direct-loop request, not general aggregation intent."""
import re
HEAD = r'(?:find|locate|return) (?:the )?(?:record|item|entry|collection|batch) iteration and (?P<relation>result|accumulator) (?:source|implementation|owner|owners|ownership)'
CONTEXT = r'(?:a|the) (?:batch|sequence|collection) of (?P<label>[a-z]+(?: [a-z]+){0,2}) (?:is reduced to its last value|retains only the final item); '
EXCLUSION = r'(?: rather than the (?:display panel|preview component|composer page))?'
BARE = re.compile(HEAD+r'\.?', re.I)
WITH_CONTEXT = re.compile(CONTEXT+HEAD+EXCLUSION+r'\.?', re.I)
RESERVED = set('find locate return both not except only source implementation owner owners'.split())


def record_loop_request(query):
    if not isinstance(query, str) or len(query)>360:
        return None
    query=query.strip(' ')
    found=WITH_CONTEXT.fullmatch(query)
    if found:
        if set(found['label'].lower().split()) & RESERVED:
            return None
        return 'result'
    found=BARE.fullmatch(query)
    return found['relation'].lower() if found else None
