"""Whole-request subject qualification, not causal or runtime identity evidence."""
import re
from .query_ui_divider_request import qualifier_matches

WORD = r'([a-z]{2,32})'
DIRECT = re.compile(r'Locate the ' + WORD + r' gesture interaction source\.?')
OBSERVED = re.compile(r'Dragging the ' + WORD + r' moves ' + WORD + r' but ' + WORD
                      + r' and ' + WORD + r' remain unchanged\. Locate the gesture interaction owner\.?')
RESERVED = set('and or not only both except exclude instead without return find locate source code '
               'context generate generated instruction call caller wrapper literal log api import '
               'boundary cause failure error'.split())


def gesture_request(query):
    if not isinstance(query, str) or len(query) > 300:
        return None
    match = DIRECT.fullmatch(query) or OBSERVED.fullmatch(query)
    if match is None or any(word in RESERVED for word in match.groups()):
        return None
    if len(match.groups()) == 4 and match[3] == match[4]:
        return None
    return match[1]
