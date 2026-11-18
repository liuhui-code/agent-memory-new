"""Executable scope of the existing diagnosis A/B measurement contract."""
from typing import Any


def require_diagnosis_cases(cases: list[dict[str, Any]]) -> None:
    # Missing task_type remains compatible with historical direct diagnosis APIs.
    # Explicit null/unknown types must not acquire that compatibility.
    unsupported = [str(c.get("id") or c.get("case_id") or "<unnamed>")
                   for c in cases if c.get("task_type", "diagnosis") != "diagnosis"]
    if unsupported:
        raise SystemExit(
            "Agent benchmark supports diagnosis execution/scoring only; "
            "design quality has no supported response and measurement contract. "
            "Unsupported selected cases: " + ", ".join(unsupported)
            + ". Design case loading and design-context remain available; "
            "do not interpret historical diagnosis scores as design quality."
        )
