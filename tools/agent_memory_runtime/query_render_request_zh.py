# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed affirmative Chinese adapter to the existing cleanup source contract."""
import re

_PATTERN = re.compile(
    r'(?:(?P<observation>(?:文章|消息|收据|通知|评论)详情)仍显示 HTML 标签，)?'
    r'(?:请)?(?:定位|查找|返回)(?:负责)?清洗并渲染(?:正文|文本)的'
    r'(?:[ \t]*(?:view|UI[ \t]*源码)|视图源码)[。.]?')


def chinese_cleanup_request(query):
    if not isinstance(query, str) or len(query) > 400:
        return None
    match = _PATTERN.fullmatch(query)
    if match is None:
        return None
    # Observation labels never select source identity or fields. Negative result
    # clauses are deliberately unsupported: the legacy exclusion matcher also
    # matches path substrings, and a filtered trial cannot certify their scope.
    return match['observation'] or '', ''
