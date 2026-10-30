# Task-End Trigger And One Review Slot

Use this reference after identifying a real Memory-related task boundary or an explicit
user request to review Agent Memory itself. It is not a per-query step. The new Runtime
decision/claim code has passed isolated synthetic regressions; it does not supply a host hook.

## Describe Actual Observations

Follow the current user's stop, disable and budget instructions before invoking anything.
Reuse the real logical task identity across tools, retries and explicit revisions. Prefer
host IDs; a namespaced client_local key may associate the actual task but cannot prove
external task identity or statistical independence. Do not invent tasks or tool events.

The strict request shape is shown below as an unexecuted template. Replace every example
identity and observation with actual values. Unknown task identity is null; unavailable
version/call metadata stays empty/null. Do not submit raw tasks, queries, logs or reasoning.

```json
{
  "schema_version": "system-meta-trigger/v1",
  "task_ref": {"key": "<namespaced-task-key>", "origin": "client_local"},
  "task_state": "failed",
  "task_outcome": "unknown",
  "memory_use": "used",
  "memory_requested": false,
  "manual_request": false,
  "review_enabled": true,
  "user_cancelled": false,
  "budget_available": true,
  "activity": "task",
  "signals": [{"kind": "memory_error", "refs": ["<actual-observation-reference>"]}],
  "version_refs": {},
  "query_refs": []
}
```

All top-level fields are required. task_state is in_progress/completed/failed/blocked/
cancelled; task_outcome is success/failure/partial/unknown; memory_use is used/not_used/
unknown. activity is task/system_review/system_evolution. manual_request means a current
explicit review request, not historical feedback authorization or a generic task to build
this feature. The five switches are booleans, not measurements or authenticated evidence.

signals has at most four distinct kinds: memory_error, user_correction, evidence_conflict
and repeated_gap. Each has kind and a nonempty refs list. repeated_gap additionally requires
gap_key and at least two different round_refs for actual query rounds on the same gap
without new inspectable evidence. Other signal kinds cannot contain these extra fields.
Ordinary empty results, pagination, truncation, expected freshness guards and final task
failure alone are not qualifying signals; use no signal rather than manufacturing one.

Requests are at most 4,000 Unicode characters, file reads at most 32 KiB. References are
single-line, at most 240 characters, each list at most eight entries, with at most eight
distinct query/signal/round references in total. Task/gap keys are 1-160 ASCII letters,
digits or `_.:-`, beginning with a letter/digit. Version fields match system-meta-review:
runtime_revision/runtime_digest/skill_revision/skill_digest/protocol_version/source_revision/
source_digest/archive_project_id/index_generation, with missing values null or omitted.

## Decide Before Generating

When supported by the installed Runtime, use the actual archive binding:

```bash
python3 tools/agent_memory.py reflect-system-trigger --project . --payload-file <trigger.json> --json
```

The default is read-only. Skip decisions are final for this automatic opportunity; do not
change task IDs, signals or flags to force a review. A review decision supplies a review_key,
next_review_revision and partial report_binding, not an actual review or an accepted full
payload. Complete the report through system-meta-review.md using the user's current model.

Decision order is current stop/disable/budget, explicit manual request, recursion guard,
closed task, observed/requested Memory, task identity and a concrete signal. Successful
tasks without signals have no automatic sampling in v1. Explicit manual review can cover
an unfinished or historically cancelled task while respecting current stop instructions.

## Claim Only Within Existing Local Recording Authorization

If local governance recording is already authorized and a real initialized archive/task
identity is available, add --claim before generating an automatic review. The short write
transaction creates one reserved slot per project/task. Only claim_created=true permits
that automatic generator to start. Repeated or concurrent automatic claims return skip;
the Runtime never calls the model itself.
The boundary is the real Memory Home/project archive and declared task identity. Do not
switch archives or rotate keys to reopen the same task's automatic budget. Older writers
and clients that bypass this protocol do not gain its allocation guarantee.

If --claim cannot reserve or returns an unavailable archive/identity, skip the automatic
path. Do not initialize the archive, change keys or bypass the requested durable check.
A current explicit manual request can still produce a conversation-only report, with the
limitation stated. Without persistence authorization or a supported installed command,
retain only the existing context-level once-per-task protocol and make no durable guarantee.

Use the returned review_key and report_binding when saving with reflect-system. A reserved
slot binds the task/key/automatic trigger; saving cannot switch these identities. One
automatic report consumes the slot. Later explicit revisions use trigger=manual and the
same thread. Immutable historical retries remain idempotent. A failed/skipped review
record does not authorize an automatic retry or any verified feedback.

Manual continuation may reuse a reserved/recorded thread and the next revision even when
claim_created=false. This requires a real current manual request; do not set the flag to
evade automatic limits. reserved means allocated, not an observed live model process.
Do not infer completion or free a slot based on elapsed time. A saved report makes it
recorded, which still does not prove the model ran, functionality passed or a change applied.

Inspect bounded slots through maintain-system, or use --trigger-id <id> for the original
typed request and linked report. Counts and local IDs are not cohort enrollment, independent
tasks, causality or release evidence. Continue system proposals through Maintain separately.
