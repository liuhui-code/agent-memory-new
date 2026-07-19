# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re

from .code_wiki_component_flow import mask_comments


MAX_BEHAVIOR_MARKERS = 56
MARKER_ORDER = (
    "fallbackbranch",
    "repositoryboundary",
    "callbackboundary",
    "deserialization",
    "actiondispatch",
    "archiveioboundary",
    "collectionfold",
    "keyboardvisibility",
    "focusstate",
    "colorparser",
    "clipboardread",
    "permissionrequest",
    "permissionguard",
    "outputreadloop",
    "runtimecapability",
    "serializedwrite",
    "writebarrier",
    "timeoutboundary",
    "cancellationguard",
    "webaccesspolicy",
    "urlschemeguard",
    "cacheeviction",
    "toolbarrole",
    "gestureboundary",
    "touchboundary",
    "keyboundary",
    "backkeyguard",
    "eventboundary",
    "indexedread",
    "collectionwrite",
    "statehandoff",
    "validationguard",
    "persistencewrite",
    "countertimestampwrite",
    "lifecyclesync",
    "lifecycleboundary",
    "callbackcleanup",
    "conditionalbranch",
    "datasourceboundary",
    "resourceacquire",
    "resourcerelease",
    "horizontalaxis",
    "verticalaxis",
    "orderingguard",
    "statewrite",
    "asyncboundary",
)
REPOSITORY_RE = re.compile(r"\b[A-Za-z_$][A-Za-z0-9_$]*Repository\b")
CONSTRUCTOR_RE = re.compile(r"\bnew\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(")
CALLBACK_CALL_RE = re.compile(
    r"\.(?:on[A-Z_$][A-Za-z0-9_$]*|register[A-Z_$][A-Za-z0-9_$]*|"
    r"subscribe|set[A-Z_$][A-Za-z0-9_$]*(?:Callback|Listener))\s*\("
)
DESERIALIZATION_RE = re.compile(
    r"\bJSON\.parse\s*\(|\.(?:fromJson|deserialize|decode)\s*\("
)
ACTION_RE = re.compile(
    r"\b(?:run|execute|dispatch|perform|submit|send)?(?:Action|Command)\b|"
    r"\.(?:action|execute|dispatch)\s*\(|"
    r"\.(?:execute|dispatch|perform|submit|send)[A-Z_$][A-Za-z0-9_$]*\s*\("
)
ARCHIVE_CONTEXT_RE = re.compile(
    r"\b(?:archive|compressed|gzip|tar|unzip|zip)\b|\.(?:tar|zip)\b",
    re.I,
)
ARCHIVE_IO_RE = re.compile(
    r"\bfs\.(?:closeSync|openSync|readSync|writeSync)\s*\(|"
    r"\bgetRawFileContentSync\s*\(|\b(?:unzip|untar)\s*\(",
)
FOR_OF_RE = re.compile(r"\bfor\s*\([^)]*\bof\b[^)]*\)\s*\{")
LOCAL_DECLARATION_RE = re.compile(
    r"\b(?:let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*="
)
KEYBOARD_VISIBILITY_RE = re.compile(
    r"\b(?:keyboardHeightChange|keyboardDidHide|keyboardDidShow|"
    r"onKeyboardHide|onKeyboardShow)\b"
)
FOCUS_STATE_RE = re.compile(
    r"\bthis\.[A-Za-z_$][A-Za-z0-9_$]*(?:focus|focusable)"
    r"[A-Za-z0-9_$]*\s*=|\.(?:requestFocus|setFocusable)\s*\(",
    re.I,
)
COLOR_PARSER_NAME_RE = re.compile(
    r"\b(?:convert|normalize|parse)[A-Za-z0-9_$]*Color\s*\(",
    re.I,
)
COLOR_CONVERSION_RE = re.compile(
    r"\bparseInt\s*\(|\.(?:charAt|split|substring|toString|trim)\s*\("
)
CLIPBOARD_SOURCE_RE = re.compile(
    r"\b(?:pasteboard\.)?getSystemPasteboard\s*\(|\.getData\s*\("
)
CLIPBOARD_RECORD_RE = re.compile(
    r"\.getRecordAt\s*\(|\.(?:plainText|htmlText)\b|\.hasType\s*\("
)
PERMISSION_REQUEST_RE = re.compile(
    r"\.(?:requestPermissionsFromUser|requestPermission)\s*\("
)
PERMISSION_RESULT_RE = re.compile(
    r"\b(?:authResults|grantResults|permissionResults)\b"
)
OUTPUT_LOOP_RE = re.compile(r"\b(?:while|for)\s*\(")
OUTPUT_READ_RE = re.compile(
    r"\.(?:readLine|readString|readSync)\s*\("
)
OUTPUT_ACCUMULATION_RE = re.compile(r"\.push\s*\(|\+=")
RUNTIME_CAPABILITY_RE = re.compile(
    r"\bbundleManager\.(?:getBundleInfoForSelf|getBundleInfo|"
    r"getApplicationInfo|queryExtensionAbilityInfos)\s*\(|"
    r"\b(?:canIUse|hasSystemCapability)\s*\("
)
SERIALIZED_WRITE_RE = re.compile(
    r"\bthis\.([A-Za-z_$][A-Za-z0-9_$]*(?:tail|queue|pending|write)"
    r"[A-Za-z0-9_$]*)\s*=\s*this\.\1\.then\s*\(",
    re.I,
)
WRITE_BARRIER_RE = re.compile(
    r"\bawait\s+this\.[A-Za-z_$][A-Za-z0-9_$]*"
    r"(?:tail|queue|pending|write)[A-Za-z0-9_$]*(?!\s*\()",
    re.I,
)
TIMEOUT_RACE_RE = re.compile(r"\bPromise\.race\s*\(")
TIMEOUT_SCHEDULE_RE = re.compile(r"\bsetTimeout\s*\(")
CANCELLATION_GUARD_RE = re.compile(
    r"\bif\s*\(\s*(?:this\.)?([A-Za-z_$][A-Za-z0-9_$]*)\s*\)",
    re.I,
)
WEB_ACCESS_POLICY_RE = re.compile(r"\.fileAccess\s*\(\s*false\s*\)")
WEB_INTERCEPT_RE = re.compile(r"\.onLoadIntercept\s*\(")
DANGEROUS_SCHEME_RE = re.compile(
    r"['\"](?:javascript|data|file|vbscript):['\"]",
    re.I,
)
URL_SCHEME_CHECK_RE = re.compile(
    r"\.(?:startsWith|match|test)\s*\(|\bURL\s*\(",
)
CACHE_SIZE_RE = re.compile(
    r"\.[A-Za-z_$][A-Za-z0-9_$]*\.size\b|\.size\s*(?:>=|>)"
)
CACHE_DELETE_RE = re.compile(r"\.delete\s*\(")
CACHE_AGE_RE = re.compile(
    r"\b(?:oldest|createdAt|updatedAt|timestamp|lastUsedAt)\b",
    re.I,
)
TOOLBAR_COMPONENT_RE = re.compile(
    r"@Component\b[\s\S]{0,180}?\b(?:export\s+)?struct\s+"
    r"[A-Za-z_$][A-Za-z0-9_$]*(?:Toolbar|ToolBar|AppBar|NavigationBar)\b"
)
EVENT_HANDLER_RE = re.compile(
    r"\b(?:on|handle)[A-Z_$][A-Za-z0-9_$]*\s*\([^)]*\)\s*(?::[^\{]+)?\{"
)
GESTURE_BOUNDARY_RE = re.compile(
    r"\b(?:Pan|Swipe|Tap|LongPress|Pinch|Rotation)?Gesture\s*\(|"
    r"\.(?:onActionStart|onActionUpdate|onActionEnd|onActionCancel)\s*\("
)
TOUCH_BOUNDARY_RE = re.compile(r"\.onTouch\s*\(|\bTouchEvent\b")
KEY_BOUNDARY_RE = re.compile(r"\.onKeyEvent\s*\(|\bKeyEvent\b")
BACK_KEY_GUARD_RE = re.compile(
    r"\b(?:KeyCode\.)?KEYCODE_BACK\b|\bBackPressed\b|\bonBackPress\s*\("
)
INDEXED_READ_RE = re.compile(
    r"\b[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+"
    r"\s*\[[^\]\n]+\]"
)
PRESENTATION_CALL_RE = re.compile(
    r"\b(?:this\.)?(?:open|show|present|push|replace|navigate)"
    r"[A-Z_$][A-Za-z0-9_$]*\s*\("
)
VALIDATION_SIGNAL_RE = re.compile(
    r"\b(?:invalid|valid|required|empty|missing|error)\b|"
    r"\.trim\s*\(|\.length\b|showToast\s*\(",
    re.I,
)
PERSISTENCE_WRITE_RE = re.compile(
    r"\b(?:this\.)?[A-Za-z_$][A-Za-z0-9_$]*"
    r"(?:Store|Storage|Repository|Dao|DAO|Database|Preferences)"
    r"\.(?:save|persist|commit|update|insert|put|set|write|upsert)"
    r"[A-Za-z0-9_$]*\s*\("
)
COUNTER_WRITE_RE = re.compile(
    r"\.[A-Za-z_$]*(?:count|counter|usage)[A-Za-z0-9_$]*"
    r"\s*(?:\+=|-=|\+\+|--)",
    re.I,
)
TIMESTAMP_WRITE_RE = re.compile(
    r"\.[A-Za-z_$]*(?:time|timestamp|usedAt|updatedAt)[A-Za-z0-9_$]*"
    r"\s*=\s*(?:Date\.now\s*\(|new\s+Date\s*\()",
    re.I,
)
LIFECYCLE_SYNC_RE = re.compile(
    r"\b(?:sync|refresh|reload|restore|retry|reconnect|upgrade|resume)"
    r"[A-Za-z0-9_$]*\s*\("
)
LIFECYCLE_BOUNDARY_RE = re.compile(
    r"\b(?:onCreate|onDestroy|onWindowStageCreate|onWindowStageDestroy|"
    r"aboutToAppear|aboutToDisappear)\s*\("
)
CALLBACK_CLEANUP_RE = re.compile(
    r"\.(?:unregister[A-Z_$][A-Za-z0-9_$]*|unsubscribe|off|"
    r"remove[A-Z_$][A-Za-z0-9_$]*Listener)\s*\("
)
CONDITIONAL_BRANCH_RE = re.compile(r"\b(?:if|switch)\s*\(")
DATA_SOURCE_RE = re.compile(
    r"\b(?:this\.)?[A-Za-z_$][A-Za-z0-9_$]*"
    r"\.(?:get[A-Za-z0-9_$]*Assets|query[A-Za-z0-9_$]*|"
    r"fetch[A-Za-z0-9_$]*|load[A-Za-z0-9_$]*|find[A-Za-z0-9_$]*|"
    r"list[A-Za-z0-9_$]*|search[A-Za-z0-9_$]*)\s*\("
)
RESOURCE_CONTEXT_RE = re.compile(
    r"\b[A-Za-z_$][A-Za-z0-9_$]*(?:Audio|Voice|Media|Video|Camera|"
    r"Capturer|Recorder|Player|Stream)[A-Za-z0-9_$]*\b|"
    r"\b(?:Audio|Voice|Media|Video|Camera|Capturer|Recorder|Player|Stream)"
    r"[A-Za-z0-9_$]*\b"
)
RESOURCE_ACQUIRE_RE = re.compile(
    r"\.(?:start|open|prepare|resume|initialize|init)\s*\("
)
RESOURCE_RELEASE_RE = re.compile(r"\.(?:stop|pause|release|close|reset)\s*\(")
HORIZONTAL_AXIS_RE = re.compile(r"\bAxis\.Horizontal\b")
VERTICAL_AXIS_RE = re.compile(r"\bAxis\.Vertical\b")
ASYNC_ORDER_GUARD_RE = re.compile(
    r"\bif\s*\(\s*(?:"
    r"[A-Za-z_$][A-Za-z0-9_$]*\s*(?:!==|!=|===|==)\s*this\.[A-Za-z_$][A-Za-z0-9_$]*|"
    r"this\.[A-Za-z_$][A-Za-z0-9_$]*\s*(?:!==|!=|===|==)\s*[A-Za-z_$][A-Za-z0-9_$]*"
    r")"
)
STATE_WRITE_RE = re.compile(
    r"\bthis\.[A-Za-z_$][A-Za-z0-9_$]*\s*(?:=|\+=|-=|\+\+|--)"
)
COLLECTION_WRITE_RE = re.compile(
    r"\bthis\.[A-Za-z_$][A-Za-z0-9_$]*(?:\[[^\]\n]+\])+"
    r"(?:\.[A-Za-z_$][A-Za-z0-9_$]*)?\s*(?:=|\+=|-=|\+\+|--)"
)


def extract_arkts_behavior_markers(text: str) -> list[str]:
    """Normalize existing ArkTS mechanisms without inferring missing repairs."""
    source = mask_comments(text)
    markers: set[str] = set()
    constructors = set(CONSTRUCTOR_RE.findall(source))
    if fallback_branch_present(source, constructors):
        markers.add("fallbackbranch")
    if REPOSITORY_RE.search(source):
        markers.add("repositoryboundary")
    if CALLBACK_CALL_RE.search(source) and "=>" in source:
        markers.add("callbackboundary")
    if DESERIALIZATION_RE.search(source):
        markers.add("deserialization")
    if ACTION_RE.search(source):
        markers.add("actiondispatch")
    if ARCHIVE_CONTEXT_RE.search(source) and ARCHIVE_IO_RE.search(source):
        markers.add("archiveioboundary")
    if collection_fold_present(source):
        markers.add("collectionfold")
    if KEYBOARD_VISIBILITY_RE.search(source):
        markers.add("keyboardvisibility")
    if FOCUS_STATE_RE.search(source):
        markers.add("focusstate")
    if COLOR_PARSER_NAME_RE.search(source) and COLOR_CONVERSION_RE.search(source):
        markers.add("colorparser")
    if CLIPBOARD_SOURCE_RE.search(source) and CLIPBOARD_RECORD_RE.search(source):
        markers.add("clipboardread")
    permission_request = bool(PERMISSION_REQUEST_RE.search(source))
    if permission_request:
        markers.add("permissionrequest")
    if permission_request and permission_result_guard_present(source):
        markers.add("permissionguard")
    if (
        OUTPUT_LOOP_RE.search(source)
        and OUTPUT_READ_RE.search(source)
        and OUTPUT_ACCUMULATION_RE.search(source)
    ):
        markers.add("outputreadloop")
    if RUNTIME_CAPABILITY_RE.search(source):
        markers.add("runtimecapability")
    if SERIALIZED_WRITE_RE.search(source):
        markers.add("serializedwrite")
    if WRITE_BARRIER_RE.search(source):
        markers.add("writebarrier")
    if TIMEOUT_RACE_RE.search(source) and TIMEOUT_SCHEDULE_RE.search(source):
        markers.add("timeoutboundary")
    if cancellation_guard_present(source):
        markers.add("cancellationguard")
    if WEB_ACCESS_POLICY_RE.search(source):
        markers.add("webaccesspolicy")
    if (
        WEB_INTERCEPT_RE.search(source)
        and DANGEROUS_SCHEME_RE.search(source)
        and URL_SCHEME_CHECK_RE.search(source)
    ):
        markers.add("urlschemeguard")
    if (
        CACHE_SIZE_RE.search(source)
        and FOR_OF_RE.search(source)
        and CACHE_DELETE_RE.search(source)
        and CACHE_AGE_RE.search(source)
    ):
        markers.add("cacheeviction")
    if TOOLBAR_COMPONENT_RE.search(source):
        markers.add("toolbarrole")
    if GESTURE_BOUNDARY_RE.search(source):
        markers.add("gestureboundary")
    if TOUCH_BOUNDARY_RE.search(source):
        markers.add("touchboundary")
    if KEY_BOUNDARY_RE.search(source):
        markers.add("keyboundary")
    if KEY_BOUNDARY_RE.search(source) and BACK_KEY_GUARD_RE.search(source):
        markers.add("backkeyguard")
    if INDEXED_READ_RE.search(source):
        markers.add("indexedread")
    event_boundary = bool(EVENT_HANDLER_RE.search(source))
    if event_boundary:
        markers.add("eventboundary")
    if COLLECTION_WRITE_RE.search(source):
        markers.add("collectionwrite")
    if event_boundary and STATE_WRITE_RE.search(source) and PRESENTATION_CALL_RE.search(source):
        markers.add("statehandoff")
    if validation_guard_present(source):
        markers.add("validationguard")
    if PERSISTENCE_WRITE_RE.search(source):
        markers.add("persistencewrite")
    if COUNTER_WRITE_RE.search(source) and TIMESTAMP_WRITE_RE.search(source):
        markers.add("countertimestampwrite")
    if LIFECYCLE_SYNC_RE.search(source):
        markers.add("lifecyclesync")
    if LIFECYCLE_BOUNDARY_RE.search(source):
        markers.add("lifecycleboundary")
    if CALLBACK_CLEANUP_RE.search(source):
        markers.add("callbackcleanup")
    if CONDITIONAL_BRANCH_RE.search(source):
        markers.add("conditionalbranch")
    if DATA_SOURCE_RE.search(source):
        markers.add("datasourceboundary")
    if RESOURCE_CONTEXT_RE.search(source):
        if RESOURCE_ACQUIRE_RE.search(source):
            markers.add("resourceacquire")
        if RESOURCE_RELEASE_RE.search(source):
            markers.add("resourcerelease")
    if HORIZONTAL_AXIS_RE.search(source):
        markers.add("horizontalaxis")
    if VERTICAL_AXIS_RE.search(source):
        markers.add("verticalaxis")
    if ASYNC_ORDER_GUARD_RE.search(source) and re.search(r"\basync\b|\bawait\b", source):
        markers.add("orderingguard")
    if STATE_WRITE_RE.search(source):
        markers.add("statewrite")
    if re.search(r"\basync\b|\bawait\b", source):
        markers.add("asyncboundary")
    return [marker for marker in MARKER_ORDER if marker in markers][
        :MAX_BEHAVIOR_MARKERS
    ]


def validation_guard_present(source: str) -> bool:
    for match in re.finditer(r"\bif\s*\(", source):
        window = source[match.start():match.start() + 700]
        exit_match = re.search(r"\b(?:return|throw)\b", window)
        if exit_match is None or "{" not in window[:exit_match.start()]:
            continue
        if VALIDATION_SIGNAL_RE.search(window[:exit_match.end()]):
            return True
    return False


def permission_result_guard_present(source: str) -> bool:
    request = PERMISSION_REQUEST_RE.search(source)
    if request is None:
        return False
    guarded = source[request.end():request.end() + 1200]
    result = PERMISSION_RESULT_RE.search(guarded)
    if result is None:
        return False
    branch = guarded.rfind("if", 0, result.start() + 1)
    if branch < 0:
        return False
    return bool(re.search(r"\b(?:return|throw)\b", guarded[result.end():]))


def cancellation_guard_present(source: str) -> bool:
    for guard in CANCELLATION_GUARD_RE.finditer(source):
        identifier = guard.group(1).casefold()
        if not any(
            marker in identifier
            for marker in ("cancel", "abandon", "timedout", "expired", "disposed")
        ):
            continue
        if re.search(r"\b(?:return|throw)\b", source[guard.end():guard.end() + 240]):
            return True
    return False


def fallback_branch_present(source: str, constructors: set[str]) -> bool:
    if re.search(r"\bif\s*\(", source) and re.search(r"\belse\b", source):
        return len(constructors) >= 2
    return bool(
        re.search(r"\b(?:fallback|mock|demo|default)[A-Za-z0-9_$]*\b", source, re.I)
        and len(constructors) >= 2
    )


def collection_fold_present(source: str) -> bool:
    loop = FOR_OF_RE.search(source)
    if loop is None:
        return False
    for declaration in LOCAL_DECLARATION_RE.finditer(source[:loop.start()]):
        name = re.escape(declaration.group(1))
        if re.search(rf"\b{name}\s*=(?!=)", source[loop.start():]):
            return True
    return False
