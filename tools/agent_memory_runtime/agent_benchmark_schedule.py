# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "agent-benchmark-execution-order/v1"
SCHEDULE = "alternating_case_trial_parity/v1"
VARIANTS = ("baseline", "memory")


def pair_schedule(case_position: int, trial_index: int) -> list[tuple[str, dict[str, Any]]]:
    if case_position < 1 or trial_index < 1:
        raise ValueError("benchmark schedule positions must be positive")
    first = "baseline" if (case_position + trial_index) % 2 == 0 else "memory"
    ordered = VARIANTS if first == "baseline" else tuple(reversed(VARIANTS))
    pair_index = case_position * 1_000_000 + trial_index
    return [
        (variant, {
            "schema_version": SCHEMA_VERSION,
            "schedule": SCHEDULE,
            "case_position": case_position,
            "trial_index": trial_index,
            "pair_index": pair_index,
            "variant_position": position,
            "first_variant": first,
        })
        for position, variant in enumerate(ordered, start=1)
    ]


def normalize_execution_order(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"benchmark execution order must use {SCHEMA_VERSION}")
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "schedule": str(value.get("schedule") or ""),
        "case_position": positive_int(value, "case_position"),
        "trial_index": positive_int(value, "trial_index"),
        "pair_index": positive_int(value, "pair_index"),
        "variant_position": positive_int(value, "variant_position"),
        "first_variant": str(value.get("first_variant") or ""),
    }
    if normalized["schedule"] != SCHEDULE:
        raise SystemExit("benchmark execution order has unsupported schedule")
    if normalized["variant_position"] not in {1, 2}:
        raise SystemExit("benchmark variant position must be 1 or 2")
    if normalized["first_variant"] not in VARIANTS:
        raise SystemExit("benchmark execution order has unsupported first variant")
    return normalized


def execution_order_audit(observations: list[dict[str, Any]]) -> dict[str, Any]:
    reported = [item for item in observations if item.get("execution_order") is not None]
    if not reported:
        return {"status": "legacy_unreported", "enforced": False}
    orders = [normalize_execution_order(item.get("execution_order")) or {} for item in reported]
    pairs: dict[tuple[str, int], list[tuple[str, dict[str, Any]]]] = {}
    for item, order in zip(reported, orders):
        pair_key = (str(item.get("case_id") or "<unreported>"), int(order["pair_index"]))
        pairs.setdefault(pair_key, []).append((str(item.get("variant")), order))
    complete = all(pair_is_complete(values) for values in pairs.values())
    first_counts = {
        variant: sum(values[0][1]["first_variant"] == variant for values in pairs.values())
        for variant in VARIANTS
    }
    balanced = abs(first_counts["baseline"] - first_counts["memory"]) <= 1
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if complete and balanced and len(reported) == len(observations) else "fail",
        "enforced": True,
        "schedule": SCHEDULE,
        "observation_count": len(observations),
        "reported_count": len(reported),
        "pair_count": len(pairs),
        "complete_pairs": complete,
        "balanced_first_variant": balanced,
        "first_variant_counts": first_counts,
    }


def pair_is_complete(values: list[tuple[str, dict[str, Any]]]) -> bool:
    return (
        len(values) == 2
        and {variant for variant, _order in values} == set(VARIANTS)
        and {int(order["variant_position"]) for _variant, order in values} == {1, 2}
        and all(order["first_variant"] == values[0][1]["first_variant"] for _variant, order in values)
    )


def positive_int(value: dict[str, Any], key: str) -> int:
    item = int(value.get(key) or 0)
    if item < 1:
        raise SystemExit(f"benchmark execution order requires positive {key}")
    return item
