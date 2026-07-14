#!/usr/bin/env python3
# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path


def key(language: str, path: str, qualified: str, signature: str) -> str:
    value = f"{language}:{path}::{qualified}|{signature}"
    return "symbol:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def entity(language: str, path: str, name: str, kind: str, qualified: str, signature: str, line: int) -> dict:
    return {
        "key": key(language, path, qualified, signature),
        "file_path": path,
        "name": name,
        "kind": kind,
        "qualified_name": qualified,
        "signature": signature,
        "start_line": line,
        "end_line": line,
        "exported": True,
        "evidence_class": "exact",
    }


def parse_file(language: str, path: str) -> tuple[list[dict], list[dict]]:
    text = Path(path).read_text(encoding="utf-8")
    entities: list[dict] = []
    relations: list[dict] = []
    owner = None
    methods: dict[str, dict] = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        container = re.match(r"\s*(?:export\s+)?(class|struct)\s+(\w+)", line)
        if container:
            raw_kind, owner = container.groups()
            kind = "component" if raw_kind == "struct" else raw_kind
            entities.append(entity(language, path, owner, kind, owner, f"{raw_kind} {owner}", line_number))
            continue
        method = re.match(r"\s*(\w+)\s*\(([^)]*)\)\s*(?::\s*([^\s{]+))?\s*\{", line)
        if method and owner:
            name, params, return_type = method.groups()
            signature = f"{name}({params.strip()}):{return_type or 'unknown'}"
            item = entity(language, path, name, "function", f"{owner}.{name}", signature, line_number)
            entities.append(item)
            methods[name] = item
    for source_name, source in methods.items():
        source_line = next(
            (line for line in text.splitlines() if re.match(rf"\s*{re.escape(source_name)}\s*\(", line)), ""
        )
        for target_name in re.findall(r"this\.(\w+)\s*\(", source_line):
            target = methods.get(target_name)
            if target:
                relations.append({
                    "source_key": source["key"],
                    "relation": "calls",
                    "target_key": target["key"],
                    "line": source["start_line"],
                    "confidence": 1.0,
                    "evidence_class": "exact",
                    "detail": "test provider resolved local call",
                })
    return entities, relations


def main() -> None:
    request = json.load(sys.stdin)
    mode = os.environ.get("PROVIDER_TEST_MODE", "success")
    if mode == "timeout":
        time.sleep(2)
    if mode == "exit":
        print("provider failed", file=sys.stderr)
        raise SystemExit(7)
    if mode == "malformed":
        print("not-json")
        return
    language = request["language"]
    entities: list[dict] = []
    relations: list[dict] = []
    digests = {item["path"]: item["digest"] for item in request["files"]}
    for item in request["files"]:
        parsed_entities, parsed_relations = parse_file(language, item["path"])
        entities.extend(parsed_entities)
        relations.extend(parsed_relations)
    if mode == "stale":
        digests[next(iter(digests))] = "stale"
    if mode == "unsafe" and entities:
        entities[0]["file_path"] = "../outside.ets"
    if mode == "unstable-key" and entities:
        entities[0]["key"] = "symbol:not-deterministic"
    if mode == "nonexact" and relations:
        relations[0]["evidence_class"] = "static"
    if mode == "external-target" and relations:
        relations[0]["target_key"] = key(language, "external/Other.ets", "Other.work", "work():void")
        relations[0]["target_file_path"] = "external/Other.ets"
    result = {
        "schema_version": "semantic-provider-result/v1",
        "request_id": request["request_id"],
        "provider": {"id": "test-arkts-exact", "version": "1.0", "toolchain": "fixture"},
        "batch": {
            "schema_version": "semantic-index/v1",
            "adapter": {"id": "test-arkts-exact", "version": "1.0", "language": language},
            "capabilities": ["calls", "definitions"],
            "source_digests": digests,
            "entities": entities,
            "relations": relations,
            "gaps": [],
        },
    }
    if mode == "request-mismatch":
        result["request_id"] = "different-request"
    if mode == "bad-schema":
        result["schema_version"] = "semantic-provider-result/v2"
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
