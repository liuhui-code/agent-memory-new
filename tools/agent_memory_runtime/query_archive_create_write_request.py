# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Full original English operation head; contextual observations grant no facts."""
import re

HEAD = r'(?:find|locate|return) (?:the )?(?:temporary )?archive creation and write (?:source|implementation|owner|owners|ownership)'
ARTICLE = r'(?:a|an|the) (?:existing )?temporary archive'
CONTEXT = rf'(?:{ARTICLE} (?:is reused|remains available) during (?:asset|resource|bundle) extraction|(?:asset|resource|bundle) extraction reuses {ARTICLE})'
REQUEST = re.compile(rf'(?:{CONTEXT}\. )?{HEAD}\.?', re.I | re.ASCII)


def archive_create_write_request(query):
    return True if isinstance(query, str) and REQUEST.fullmatch(query) is not None else None
