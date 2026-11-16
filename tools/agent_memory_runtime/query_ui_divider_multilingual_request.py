# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite request-local naming conventions, never retrieval or source authority."""
from dataclasses import dataclass
import re

DOMAINS = {'字形': ('glyph',), '账户': ('account',), '库存': ('inventory', 'stock')}
IDENTIFIER = r'[A-Za-z_$][A-Za-z0-9_$]*'
FORM = re.compile(
    r'(?P<domain>字形|账户|库存)列表分隔线粗细(?:错误|不正确)，请定位 divider 的源码'
    r'(?:，不要返回 (?P<names>' + IDENTIFIER + r'(?: 或 ' + IDENTIFIER + r'){0,2}))?。?'
)
NAME = re.compile(IDENTIFIER)
RESERVED = frozenset('''await break case catch class const continue debugger default delete do
else enum export extends false finally for function if implements import in instanceof
interface let new null package private protected public return static super switch this
throw true try typeof var void while with yield abstract as asserts any async boolean
constructor declare get infer is keyof module namespace never readonly require number
object set string symbol type undefined unique unknown from of struct build and or not
only both except exclude instead without find locate source code context generate generated
instruction call caller wrapper literal log api sdk boundary'''.split())


@dataclass(frozen=True)
class MultilingualDividerRequest:
    qualifiers: tuple[str, ...]
    excluded_names: tuple[str, ...]
    negative_spans: tuple[tuple[int, int], ...]


def parse_multilingual_divider_request(query):
    if not isinstance(query, str) or len(query) > 240:
        return None
    match = FORM.fullmatch(query)
    if match is None:
        return None
    names, spans = (), ()
    if match['names'] is not None:
        names = tuple(match['names'].split(' 或 '))
        if len(set(names)) != len(names) or any(name.lower() in RESERVED for name in names):
            return None
        offset = match.start('names')
        spans = tuple((offset + m.start(), offset + m.end()) for m in NAME.finditer(match['names']))
    return MultilingualDividerRequest(DOMAINS[match['domain']], names, spans)


def project_negative_names(query, descriptor):
    """Text-name checks only: retain original query for retrieval, logs and receipts.

    Unknown or altered descriptors do not authorize removal of any input text.
    """
    if type(descriptor) is not MultilingualDividerRequest:
        return query
    parsed = parse_multilingual_divider_request(query)
    if parsed is None or parsed != descriptor:
        return query
    result = query
    for lo, hi in descriptor.negative_spans:
        result = result[:lo] + ' ' * (hi - lo) + result[hi:]
    return result
