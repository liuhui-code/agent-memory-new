# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re

from .code_wiki_component_flow import mask_comments


UI_CALLBACK_RE = re.compile(
    r"\.(?:onClick|onChange|onSubmit|onTouch)\s*\(\s*"
    r"(?:async\s*)?\([^)]*\)\s*=>",
)
PERSISTENCE_READ_RE = re.compile(
    r"\b[A-Za-z_$][A-Za-z0-9_$]*(?:Preferences|Preference|Storage|Store|"
    r"Repository|Dao|DAO|Database)\.(?:get|read|load|restore|find)"
    r"[A-Za-z0-9_$]*\s*\(\s*['\"]",
)
PLATFORM_API_RE = re.compile(
    r"\b(?:ConfigurationConstant\.ColorMode|deviceInfo\.|canIUse\s*\(|"
    r"hasSystemCapability\s*\()|\.setColorMode\s*\(",
)
PLATFORM_UI_RE = re.compile(
    r"\b(?:Tab)?SegmentButtonV?\d*\s*\(|\b(?:Button|Select|Toggle)\s*\(",
)


def extract_arkts_context_contracts(text: str) -> list[str]:
    source = mask_comments(text)
    markers: list[str] = []
    if UI_CALLBACK_RE.search(source):
        markers.append("uicallbackbinding")
    if PERSISTENCE_READ_RE.search(source):
        markers.append("persistenceread")
    if PLATFORM_API_RE.search(source) and PLATFORM_UI_RE.search(source):
        markers.append("platformsensitiveui")
    return markers
