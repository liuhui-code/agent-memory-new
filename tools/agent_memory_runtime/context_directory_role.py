# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Weak exact directory-role evidence, used only by guarded post-cap projection."""
from __future__ import annotations
import re
from typing import Any
from .query_language import NEGATIVE_RESULT_CLAUSE_RE, EXCLUDED_ROLE_TERMS

# Only this independently controlled countable role is currently supported.
_DIRECTORY_FORMS = {'view': frozenset({'view', 'views'})}


def excluded_directory_role(query: str, item: dict[str, Any]) -> bool:
    clauses = NEGATIVE_RESULT_CLAUSE_RE.findall(query)
    roles = {word for clause in clauses for word in re.findall(r'[a-z]+', clause.casefold())
             if word in EXCLUDED_ROLE_TERMS and word in _DIRECTORY_FORMS}
    if not roles:
        return False
    path = item.get('file_path')
    if not isinstance(path, str) or not path.strip():
        return False
    segments = path.replace('\\', '/').casefold().split('/')
    matching = {role for role in roles if set(segments[:-1]) & _DIRECTORY_FORMS[role]}
    if not matching:
        return False
    positive = NEGATIVE_RESULT_CLAUSE_RE.sub(' ', query).casefold().replace('\\', '/')
    words = set(re.findall(r'[a-z]+', positive))
    if any(words & _DIRECTORY_FORMS[role] for role in matching):
        return False
    basename = segments[-1]
    stem = basename.rsplit('.', 1)[0]
    owner = str(item.get('owner_name') or '').casefold()
    names = {path.replace('\\', '/').casefold(), basename, stem, owner} - {''}
    if any(re.search(r'(?<![\w$])' + re.escape(name) + r'(?![\w$])', positive) for name in names):
        return False
    return True
