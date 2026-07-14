# Incident Diagnosis Protocol

Use this protocol for symptoms, errors, runtime logs, crashes, blank pages, failed routes, missing resources, or recurring incidents.

## Workflow

1. Run `evidence-context` with `--goal diagnosis`.
2. Prefer current code-log anchors and observed runtime evidence.
3. If a temporary log is available, analyze it without persisting the raw file.
4. Build a bounded chain from symptom to event, code anchor, mechanism, and verification.
5. Treat prior incidents and experience as corroboration only.

```bash
python tools/agent_memory.py evidence-context --project . --goal diagnosis --query "<symptom>" --json
python tools/agent_memory.py analyze-runtime-log --project . --query "<symptom>" --log-file "<path>" --json
```

Prefer stable OTel-lite fields such as severity, logger, event name, trace/request/session id, error code, reason, route, resource, and result. Use raw excerpts only when structured fields are insufficient.

Read `causal_evidence.level`: `association` is a lead, `supported` has a mechanism or runtime correlation, `verified` has resolution/verification evidence, and `rejected` has counter-evidence. Never upgrade a chain because multiple weak memories repeat the same claim.

When `incident-trace` returns `causal_chain`, preserve its role boundary: the supplied runtime log is `observed`, enclosing code is `supports`, static semantic neighbors are `possible`, and lower-authority links are `inferred`. Inspect the linked symbol ids before turning a possible path into a diagnosis.

Report low-signal logs and `observability_gaps` as narrow engineering follow-ups. Persist only a compact reflection candidate after verification, never the raw log stream.
