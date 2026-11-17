"""Finite explicit-axis request permission; subjects are opaque owner parts."""
import re
from .query_ui_divider_request import qualifier_matches

# Frozen union of protocol subjects and the existing gesture protection words.
RESERVED = frozenset('all any current code source owner layout vertical horizontal viewport screen '
    'scroll list column row component page panel records record content build method class struct '
    'interface function axis state log event graph path file root and or not only both except exclude '
    'instead without return find locate context generate generated instruction call caller wrapper '
    'literal api import boundary cause failure error'.split())
FORMS = (
    re.compile(r'Locate the ([a-z]{2,24}) vertical layout source\.'),
    re.compile(r'([A-Z][a-z]{1,23}) records cannot scroll when their content fills the viewport\. Locate the vertical layout owner\.'),
    re.compile(r'The viewport clips ([a-z]{2,24}) records and the vertical layout does not move\. Return the current code owner\.'),
)


def vertical_request(query):
    if not isinstance(query, str) or len(query) > 240:
        return None
    for form in FORMS:
        match = form.fullmatch(query)
        if match is not None:
            subject = match[1].lower()
            return None if subject in RESERVED else subject
    return None
