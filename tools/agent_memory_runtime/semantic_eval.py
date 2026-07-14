# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from time import monotonic
from typing import Any

from .design_evidence import EVIDENCE_RANK
from .records import output
from .semantic_models import SemanticBatch
from .semantic_provider_protocol import ProviderFailure
from .semantic_runtime import SemanticSelection, run_semantic_adapter
from .storage import resolve_project


EVAL_SCHEMA = "semantic-eval-cases/v1"
RESULT_SCHEMA = "semantic-eval-result/v1"


def eval_semantic_command(args: argparse.Namespace) -> None:
    pack = load_case_pack(Path(args.cases))
    payload = evaluate_semantic_pack(pack, args.mode)
    output(payload, args.json)


def load_case_pack(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"failed to read semantic evaluation cases: {path}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != EVAL_SCHEMA:
        raise SystemExit("unsupported semantic evaluation case schema")
    if not isinstance(value.get("cases"), list) or not value["cases"]:
        raise SystemExit("semantic evaluation cases require a non-empty cases list")
    return value


def evaluate_semantic_pack(pack: dict[str, Any], mode: str) -> dict[str, Any]:
    started = monotonic()
    results = [evaluate_semantic_case(item, index, mode) for index, item in enumerate(pack["cases"])]
    expected = sum(item["counts"]["expected"] for item in results)
    matched = sum(item["counts"]["matched"] for item in results)
    forbidden = sum(item["counts"]["forbidden"] for item in results)
    forbidden_hits = sum(item["counts"]["forbidden_hits"] for item in results)
    relations = sum(item["counts"]["relations"] for item in results)
    resolved = sum(item["counts"]["resolved_relations"] for item in results)
    passed = sum(item["status"] == "pass" for item in results)
    return {
        "schema_version": RESULT_SCHEMA,
        "status": "pass" if passed == len(results) else "fail",
        "mode": mode,
        "metrics": {
            "case_pass_rate": round(passed / len(results), 4),
            "expected_relation_recall": round(matched / expected, 4) if expected else 1.0,
            "forbidden_edge_rate": round(forbidden_hits / forbidden, 4) if forbidden else 0.0,
            "resolution_rate": round(resolved / relations, 4) if relations else 1.0,
            "entity_count": sum(item["counts"]["entities"] for item in results),
            "relation_count": relations,
            "gap_count": sum(item["counts"]["gaps"] for item in results),
            "common_relations": sum(item["comparison"]["common_count"] for item in results),
            "selected_only_relations": sum(item["comparison"]["selected_only_count"] for item in results),
            "static_only_relations": sum(item["comparison"]["static_only_count"] for item in results),
            "duration_ms": round((monotonic() - started) * 1000, 3),
            "case_count": len(results),
        },
        "cases": results,
        "audit": {"persisted": False, "llm_used": False, "target_project_read": False},
    }


def evaluate_semantic_case(value: Any, index: int, mode: str) -> dict[str, Any]:
    case = validate_case(value, index)
    with tempfile.TemporaryDirectory(prefix="agent-memory-semantic-eval-") as temp_dir:
        root = Path(temp_dir) / "source"
        root.mkdir()
        files = write_fixture_files(root, case["files"])
        project = resolve_project(str(root), str(Path(temp_dir) / "memory"))
        try:
            selected = run_semantic_adapter(project, case["language"], files, mode)
        except ProviderFailure as exc:
            raise SystemExit(f"semantic provider failed for case {case['id']}: {exc.code}: {exc.detail}") from exc
        baseline = selected if mode == "static" else run_semantic_adapter(project, case["language"], files, "static")
    actual = canonical_relations(selected.batch)
    baseline_relations = canonical_relations(baseline.batch)
    missing = [item for item in case["expected"] if not matching_relations(actual, item)]
    forbidden_hits = [item for item in case["forbidden"] if matching_relations(actual, item)]
    weak = [
        item for item in case["expected"]
        if matching_relations(actual, item)
        and max(EVIDENCE_RANK.get(row["evidence_class"], 0) for row in matching_relations(actual, item))
        < EVIDENCE_RANK[case["minimum_evidence_class"]]
    ]
    selected_keys = {relation_key(item) for item in actual}
    baseline_keys = {relation_key(item) for item in baseline_relations}
    resolved = sum(item["resolved"] for item in actual)
    return {
        "id": case["id"],
        "status": "pass" if not missing and not forbidden_hits and not weak else "fail",
        "provider": selected.telemetry,
        "counts": {
            "entities": len(selected.batch.entities),
            "relations": len(actual),
            "resolved_relations": resolved,
            "gaps": len(selected.batch.gaps),
            "expected": len(case["expected"]),
            "matched": len(case["expected"]) - len(missing),
            "forbidden": len(case["forbidden"]),
            "forbidden_hits": len(forbidden_hits),
        },
        "missing": missing,
        "forbidden_hits": forbidden_hits,
        "weak_evidence": weak,
        "comparison": {
            "common_count": len(selected_keys & baseline_keys),
            "selected_only_count": len(selected_keys - baseline_keys),
            "static_only_count": len(baseline_keys - selected_keys),
            "selected_only": sorted(selected_keys - baseline_keys)[:20],
            "static_only": sorted(baseline_keys - selected_keys)[:20],
        },
        "output_bytes": len(json.dumps(selected.batch.to_dict(), ensure_ascii=False).encode("utf-8")),
    }


def validate_case(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("id"), str):
        raise SystemExit(f"semantic case {index} requires an id")
    if value.get("language") not in {"ArkTS", "TypeScript"}:
        raise SystemExit(f"semantic case {value['id']} has unsupported language")
    files = value.get("files")
    if not isinstance(files, dict) or not files or not all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
        raise SystemExit(f"semantic case {value['id']} requires source files")
    expected = validate_specs(value.get("expected", []), value["id"], "expected")
    forbidden = validate_specs(value.get("forbidden", []), value["id"], "forbidden")
    minimum = str(value.get("minimum_evidence_class") or "static")
    if minimum not in EVIDENCE_RANK:
        raise SystemExit(f"semantic case {value['id']} has invalid minimum evidence class")
    return {**value, "expected": expected, "forbidden": forbidden, "minimum_evidence_class": minimum}


def validate_specs(value: Any, case_id: str, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise SystemExit(f"semantic case {case_id} {label} must be a list")
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str) for key in ("source", "relation", "target")):
            raise SystemExit(f"semantic case {case_id} has malformed {label} relation")
        result.append({key: str(item[key]) for key in ("source", "relation", "target")})
    return result


def write_fixture_files(root: Path, values: dict[str, str]) -> list[Path]:
    files: list[Path] = []
    for relative, content in sorted(values.items()):
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"unsafe semantic evaluation fixture path: {relative}")
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.rstrip() + "\n", encoding="utf-8")
        files.append(target.resolve())
    return files


def canonical_relations(batch: SemanticBatch) -> list[dict[str, Any]]:
    labels = {item.key: item.qualified_name for item in batch.entities}
    qualified = set(labels.values())
    result: list[dict[str, Any]] = []
    for item in batch.relations:
        source = labels.get(item.source_key, item.source_key)
        target = labels.get(item.target_key or "") or item.target_qualified_name or item.target_name or item.target_key
        result.append({
            "source": source,
            "relation": item.relation,
            "target": str(target or ""),
            "evidence_class": item.evidence_class,
            "resolved": bool(
                (item.target_key and item.target_key in labels)
                or (item.target_qualified_name and item.target_qualified_name in qualified)
            ),
        })
    return result


def matching_relations(actual: list[dict[str, Any]], expected: dict[str, str]) -> list[dict[str, Any]]:
    return [item for item in actual if all(item[key] == expected[key] for key in ("source", "relation", "target"))]


def relation_key(item: dict[str, Any]) -> str:
    return f"{item['source']}|{item['relation']}|{item['target']}"
