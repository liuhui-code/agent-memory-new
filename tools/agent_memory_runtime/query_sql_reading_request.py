"""Positive SQL source-reading permission, never SQL/UI slot or owner authority."""
import re

FLAGS = re.ASCII | re.IGNORECASE
ARTICLE = r'(?:(?:the|a|an) )?'
MODIFIER = r'(?:partial|exact|prefix|suffix|substring|case-sensitive|case-insensitive)'
DOMAIN = r'(?:[a-z]{1,24}-(?:name|title|code|id) )?'
NOMINAL = ARTICLE + MODIFIER + r' ' + DOMAIN + r'(?:search|query|lookup|matching)'
OBSERVATION = NOMINAL + r' behaves like ' + NOMINAL + r'\. '
SQL_ITEM = r'(?:(?:the|a) )?SQL (?:parameter|argument) (?:binding(?: (?:owner|source|implementation))?|owner|source|implementation)'
UI_ITEM = r'(?:(?:the|a) )?(?:page|component|view) that submits and (?:renders|displays) (?:the )?results?'
REQUEST = re.compile(r'(?P<observation>' + OBSERVATION + r')?(?:Find|Locate|Show|Return) (?P<targets>' + SQL_ITEM + r'|both ' + SQL_ITEM + r' and ' + UI_ITEM + r')\.', FLAGS)


def sql_reading_request(query):
    if type(query) is not str or not 0 < len(query) <= 240:
        return None
    match = REQUEST.fullmatch(query)
    if match is None:
        return None
    return dict(kind='positive_sql_reading', observation_unverified=match['observation'] is not None)
