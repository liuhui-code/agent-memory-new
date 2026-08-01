# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
from typing import Any

from .incident_trace_models import INCIDENT_STATE_CONFIDENCE_CAPS


MAX_OBSERVED_EVENTS = 8
MAX_CAUSAL_STEPS = 12
MAX_TEXT = 1000


def build_agent_incident(
    symptom: str,
    scene: str,
    diagnosis_summary: str,
    observed_events: list[str],
    causal_steps: list[str],
    links: list[dict[str, Any]],
    status: str,
    resolution: str | None,
    intervention: str | None,
    verification_evidence: str | None,
    confidence: float,
) -> dict[str, Any]:
    symptom = required_text(symptom, "symptom")
    diagnosis = required_text(diagnosis_summary, "diagnosis-summary")
    resolution = optional_text(resolution)
    intervention = optional_text(intervention)
    verification = optional_text(verification_evidence)
    if status == "resolved" and not resolution:
        raise SystemExit("--resolution is required when --status resolved")
    events = clean_values(observed_events, MAX_OBSERVED_EVENTS)
    steps = clean_values(causal_steps, MAX_CAUSAL_STEPS)
    state = evidence_state(links, resolution, intervention, verification)
    anchor_keys = [str(link.get("target_key") or "") for link in links]
    return {
        "trace_key": trace_key(symptom, diagnosis, anchor_keys),
        "status": status,
        "symptom": symptom,
        "arkts_scene": scene,
        "diagnosis_summary": diagnosis,
        "observed_events": events,
        "agent_causal_steps": steps,
        "resolution": resolution,
        "intervention": intervention,
        "verification_evidence": verification,
        "capture_mode": "agent_structured",
        "evidence_state": state,
        "confidence": capped_confidence(confidence, state),
        "source": "agent-cli",
    }


def evidence_state(
    links: list[dict[str, Any]],
    resolution: str | None,
    intervention: str | None,
    verification_evidence: str | None,
) -> str:
    anchored = any(link.get("relation") == "agent_confirmed_anchor" for link in links)
    if anchored and resolution and intervention and verification_evidence:
        return "verified"
    if anchored:
        return "supported"
    return "reported"


def capped_confidence(value: float, state: str) -> float:
    try:
        confidence = max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        confidence = 0.0
    return round(min(confidence, INCIDENT_STATE_CONFIDENCE_CAPS[state]), 3)


def trace_key(symptom: str, diagnosis: str, anchors: list[str]) -> str:
    material = "\n".join([symptom.casefold(), diagnosis.casefold(), *sorted(anchors)])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def required_text(value: str, field: str) -> str:
    text = " ".join(str(value or "").split())[:MAX_TEXT]
    if not text:
        raise SystemExit(f"--{field} is required")
    return text


def optional_text(value: str | None) -> str | None:
    text = " ".join(str(value or "").split())[:MAX_TEXT]
    return text or None


def clean_values(values: list[str], limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split())[:MAX_TEXT]
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) == limit:
            break
    return result
