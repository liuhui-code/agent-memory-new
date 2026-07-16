# Agent-Led Incident Query Protocol

Use this protocol for symptoms, errors, runtime logs, crashes, blank pages, failed routes, missing resources, or recurring incidents.

## Workflow

1. If the problem already names a precise file/line or literal mismatch, inspect at most three files and run at most two source searches first. Stop without Memory when current source plus verification settles it.
2. Otherwise run compact `context` with the user's problem to retrieve historical experience, code-log keywords, code locations, and stored graph edges.
3. Read the temporary runtime log directly with Agent CLI tools; never send the file to Agent Memory.
4. Summarize exact events, identifiers, ordering, missing expected events, and multiple candidate causes in the Agent session.
5. Run one compact `context` query for each exact log phrase, error code, event name, symbol, or candidate cause.
6. Inspect the returned current source and relation hints, then infer the likely call chain in the Agent session.
7. Combine the observed runtime order with inspected code behavior to build the causal chain in the Agent session.
8. Execute discriminating checks and treat prior incidents and experience as historical advice only.

```bash
python tools/agent_memory.py context --project . --query "<user symptom>" --compact --json
python tools/agent_memory.py context --project . --query "<exact runtime-log phrase or error code>" --compact --json
python tools/agent_memory.py context --project . --query "<one Agent candidate cause>" --compact --json
```

Remove `--compact` only when a focused candidate requires full retrieval explanations, complete records, or conflict audit.

When reading the user log, prefer stable fields such as severity, logger, event name, trace/request/session id, error code, reason, route, resource, and result. These fields become plain text inputs for the next `context` query.

Read `query_handoff.log_anchors` to map runtime phrases to code-log templates and source functions. When `query_handoff.path_context.activated` is true, treat each `path_candidate` as a current-graph possibility, not a diagnosis. Compare its `expected_log_anchors` with the actual temporary-log order, process/session identity, missing events, and contradictions. Keep multiple paths when the log does not distinguish them. Read `code_anchors` for current source locations and `experience_refs` for historical applicability. Do not let stored `likely_causes`, ranking, or repeated memories select the current root cause.

Path scores are structural only. Experience and semantic corrections cannot create graph seeds, edges, or path scores. Use them after path reconstruction to annotate applicability or challenge an interpretation. A missing path means incomplete graph evidence; it does not prove that execution did not occur.

Create the candidate-cause queue in the Agent session. For each candidate, query separately, inspect its source path, and record supporting and counter observations locally.

Start source inspection with the returned candidate entry, emitter, edge provenance, uncertainty, and missing segments. Extend or reject paths by following callers, async boundaries, callbacks, route/resource access, state reads/writes, and error branches in current source. Infer the causal chain only after aligning that source path with the order observed in the temporary runtime log.

Report missing identifiers or expected events as observability gaps. Persist only the Agent-authored, verified reflection or Incident summary, never the raw log stream.
