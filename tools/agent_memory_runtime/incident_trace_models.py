# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations


INCIDENT_TRACE_STATUSES = {"open", "diagnosed", "resolved", "stale", "ignored"}
INCIDENT_TRACE_QUERY_LIMIT = 5
INCIDENT_TRACE_SEARCH_LIMIT = 10
INCIDENT_TRACE_LINK_LIMIT = 12
INCIDENT_CAPTURE_AGENT = "agent_structured"
INCIDENT_CAPTURE_LEGACY = "legacy_runtime_derived"
INCIDENT_EVIDENCE_STATES = {"legacy_unverified", "reported", "supported", "verified"}
INCIDENT_STATE_CONFIDENCE_CAPS = {
    "legacy_unverified": 0.25,
    "reported": 0.45,
    "supported": 0.7,
    "verified": 0.95,
}

ARKTS_SCENES = {
    "route",
    "resource",
    "network",
    "permission",
    "ability",
    "state",
    "unknown",
}
