# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from .path_context_models import EntryPoint, GraphNode


GENERIC_ENTRY_NAMES = {
    "main": "public_api",
    "run": "public_api",
    "start": "public_api",
    "execute": "public_api",
    "handle": "event_handler",
}
ARKTS_LIFECYCLE_NAMES = {
    "onCreate",
    "onDestroy",
    "onForeground",
    "onBackground",
    "aboutToAppear",
    "aboutToDisappear",
    "onPageShow",
    "onPageHide",
    "onBackPress",
    "build",
}


class CompositeEntryPointPolicy:
    def __init__(self, *policies: object) -> None:
        self.policies = policies

    def classify(self, node: GraphNode) -> EntryPoint | None:
        for policy in self.policies:
            result = policy.classify(node)  # type: ignore[attr-defined]
            if result:
                return result
        return None


class ArkTSEntryPointPolicy:
    def classify(self, node: GraphNode) -> EntryPoint | None:
        if node.language != "ArkTS" and not node.file_path.endswith(".ets"):
            return None
        if node.name in ARKTS_LIFECYCLE_NAMES:
            return EntryPoint("lifecycle", 1.0, f"ArkTS lifecycle function {node.name}")
        lowered = node.name.casefold()
        if lowered.startswith(("onclick", "onchange", "onsubmit", "ontouch", "handle")):
            return EntryPoint("event_handler", 0.95, f"ArkTS UI event handler {node.name}")
        file_name = node.file_path.rsplit("/", 1)[-1]
        if node.kind == "file" and "ability" in file_name.casefold():
            return EntryPoint("lifecycle", 0.9, "ArkTS Ability file boundary")
        if node.kind == "file" and ("/pages/" in f"/{node.file_path}" or file_name.endswith("Page.ets")):
            return EntryPoint("route", 0.85, "ArkTS page file boundary")
        return None


class GenericEntryPointPolicy:
    def classify(self, node: GraphNode) -> EntryPoint | None:
        if node.kind == "file":
            return EntryPoint("unknown_entry", 0.5, "file boundary reached")
        lowered = node.name.casefold()
        if lowered in GENERIC_ENTRY_NAMES:
            return EntryPoint(GENERIC_ENTRY_NAMES[lowered], 0.8, f"conventional entry name {node.name}")
        if lowered.startswith(("on_", "handle_", "consume", "subscribe")):
            return EntryPoint("event_handler", 0.75, f"conventional handler name {node.name}")
        return None
