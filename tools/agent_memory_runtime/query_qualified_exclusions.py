# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite complete negative clauses; never infer a member owner from paths."""
import re

# Separate from the historical prose grammar. Only a complete, unquoted,
# delimiter-separated negative clause naming exactly one owner.member qualifies.
CLAUSE = re.compile(
    r'(?P<boundary>^|[;；]\s*)(?i:exclude|excluding|omit|ignore|排除|忽略)\s+'
    r'(?P<owner>[A-Z][A-Za-z0-9_$]*)\.(?P<member>[a-z_$][A-Za-z0-9_$]*)'
    r'(?P<end>\.(?=\s*(?:$|[;；\n]))|(?=\s*(?:$|[;；\n])))'
)


def qualified_exclusions(query):
    """Return exact case-sensitive pairs and prose safe for legacy consumers."""
    if any(c in query for c in '`\"\'“”‘’'):
        return set(), query
    pairs = set()
    def remove(match):
        pairs.add((match['owner'], match['member']))
        return match['boundary']
    return pairs, CLAUSE.sub(remove, query)


def matches_qualified_exclusion(pairs, item):
    qualified = item.get('qualified_name')
    owner, symbol = item.get('owner_name'), item.get('symbol')
    for expected_owner, member in pairs:
        target = expected_owner + '.' + member
        if qualified:
            if qualified != target:
                continue
            if owner and owner != expected_owner:
                continue
            if symbol and symbol not in (member, target):
                continue
            return True
        if owner == expected_owner and symbol in (member, target):
            return True
    return False
