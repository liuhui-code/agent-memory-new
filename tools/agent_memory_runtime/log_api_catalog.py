# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations


ECMA_LOG_CALL_PATTERN = (
    r"\b(?:console|logger|Logger|hilog|HiLog)\."
    r"(?:log|debug|info|warn|warning|error|exception|fatal)\s*\("
)


def direct_log_pattern(language: str) -> str:
    if language in {"TypeScript", "JavaScript", "ArkTS"}:
        return ECMA_LOG_CALL_PATTERN
    if language == "Python":
        return r"\b(?:print|logging\.(?:debug|info|warning|warn|error|exception)|logger\.(?:debug|info|warning|warn|error|exception))\s*\("
    if language == "Dart":
        return r"\b(?:print|debugPrint|log)\s*\("
    if language == "Swift":
        return r"\b(?:print|NSLog|os_log|logger\.(?:debug|info|warning|error))\s*\("
    return ""
