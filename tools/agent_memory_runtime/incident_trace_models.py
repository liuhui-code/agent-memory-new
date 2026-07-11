# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations


INCIDENT_TRACE_STATUSES = {"open", "diagnosed", "resolved", "stale", "ignored"}
INCIDENT_TRACE_QUERY_LIMIT = 5
INCIDENT_TRACE_SEARCH_LIMIT = 10
INCIDENT_TRACE_LINK_LIMIT = 5
INCIDENT_LOG_TEXT_LIMIT = 2000
INCIDENT_LOG_FILE_BYTES_LIMIT = 64 * 1024

ARKTS_SCENES = {
    "route",
    "resource",
    "network",
    "permission",
    "ability",
    "state",
    "unknown",
}

