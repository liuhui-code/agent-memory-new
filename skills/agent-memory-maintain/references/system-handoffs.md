# Window Review Handoff

Use only when an already known active round has a pre-bound outcome plan/v2 with
host_review enabled and existing user authorization for window review. Do not scan
archives or add task-end work just to discover opportunities. The current host model
performs one bounded assessment; Runtime supplies context and durable coordination.

## Prepare And Install

Before candidate checks/application, bind outcome-plan/v2 as an existing prepared
artifact. It keeps every v1 plan field and adds exactly:

```json
"host_review": {
  "enabled": true,
  "authorization_ref": "<existing-user-authorization-reference>",
  "max_review_attempts": 1,
  "automatic_retries": 0,
  "max_report_chars": 4000
}
```

Use the actual authorization, not an invented reference or a model's own permission.
v1 plans have no automatic handoff permission; do not edit a bound plan after application.
The declared task-count window, R2 round and assessment budgets still apply. This policy
bounds one reserved generation attempt and the canonical assessment's characters. Actual
host Token/tool costs are not metered here; follow the user's host budget and retain unknowns.

With governance v2 and R2 already installed, explicitly preview/install the optional component:

```bash
python3 tools/agent_memory.py maintain-system-migrate --project . --target-version system-handoffs-v1 --backup-file <new-backup-outside-memory-home.db> --json
python3 tools/agent_memory.py maintain-system-migrate --project . --target-version system-handoffs-v1 --backup-file <new-backup-outside-memory-home.db> --execute --json
```

No read/init/handoff implicitly installs it. Preserve later Memory data during code recovery;
do not restore the old whole database over subsequent writes. Old Runtime ordinary reads/writes
preserve unknown tables, but old automatic trigger code lacks R3 coordination: do not run
old/new automatic review workflows concurrently against this archive.

## At The Actual Boundary

At the end of an ordinary task contributing to this known window, or an authorized batch
window-follow-up task, use the real host task reference. Mark origin client_local only when
the host supplies no durable ID; reuse that locally persisted ID on retries. Do not relabel
system_review/system_evolution work as a normal task or a new independent sample.

Write bounded UTF-8 JSON (32 KiB, unique keys, strict fields) to a file. Example claim shape:

```json
{
  "schema_version": "system-evolution-handoff-request/v1",
  "action": "claim",
  "round_key": "<actual-round>",
  "expected_revision": 1,
  "observations_file": "<relative-observations-file>",
  "task_ref": {"origin": "client_local", "key": "<actual-stable-task-id>"},
  "task_state": "completed",
  "activity": "round_follow_up",
  "review_enabled": true,
  "user_cancelled": false,
  "budget_available": true,
  "version_refs": {}
}
```

Use the observed revision/state/versions and existing Memory Home, not example values.
activity also permits task, system_review, system_evolution; the last two auto-skip.
Nonterminal/cancelled tasks, disabled review, missing budget, uninstalled storage, incomplete
declared windows or no known verified-result declarations do not generate a review.
Known outcomes still are caller declarations; Runtime does not authenticate task correctness.

```bash
python3 tools/agent_memory.py maintain-system-round-handoff --project . --payload-file <claim.json> --json
python3 tools/agent_memory.py maintain-system-round-handoff --project . --payload-file <claim.json> --execute --json
```

Preview ready is not permission to generate. Generate only after this invocation returns
should_review=true and a newly written claim. All other replies stop model generation.
Repeated or lost responses do not authorize retry; inspect the retained claim. Allocation
is once per round and once per task across current v1/R3 automatic paths. Never change keys
to evade it. A reserved slot does not prove a model ran or that any process ended.

## Assess Once And Save

Use only the returned claim.receipt.context to compare the original hypothesis with the
actual linked operations and later declared outcomes. Keep negative/unknown results and
missing costs explicit. Use the current host model; launch no reviewer, background loop or
new candidate. No extra investigation is required to finish an inconclusive assessment.

Copy claim.receipt.assessment_binding exactly and add the ordinary R2 assessment fields:
finding (supported/contradicted/inconclusive), summary (up to 600 characters), evidence_refs
(up to eight single-line 240-character references) and additional_cost (tokens/elapsed_ms,
null or bounded nonnegative integers). Supported/contradicted requires at least one reference.
Respect the pre-bound maximum canonical report characters. Do not turn declarations,
successful checks or allocation into verified evidence or proven long-term gains.

The complete request has schema_version, action="complete", round_key, claim_digest
(the actual claim.receipt_digest), and assessment (the bound R2 assessment object).
Preview and save it with the same command; only --execute writes. Runtime rechecks current
context and revision, then atomically appends the R2 assessment and finish event. It does
not change a decision/proposal, deploy, roll back, call a model or start the next round.

If interrupted, cancelled, over budget, or inputs changed, do not regenerate. Submit action
"fail" with schema_version, round_key, claim_digest, reason, note, evidence_refs and
additional_cost. reason is host_interrupted/budget_exhausted/input_drift/review_failed/
user_stopped/unknown. Notes have at most 600 characters, references/costs the same bounds.
Failure retains the consumed slot and does not clear actual unknown operations.

## Inspect Or Retry A Save

An inspect request contains only schema_version, action="inspect" and round_key. It reads
claim/finish history without the original files. The same completed/failure save can be
retried idempotently without rereading today's inputs; different content cannot replace it.
Reserved claims never expire or self-reset. Manual recovery needs existing authorization
and the separate R2/lifecycle workflow; preserve the failed/unknown history.

All authenticity, efficacy, promotion and host-execution flags remain false. A real host
test proves only that tested host and controlled workflow. Normal-task automatic sampling,
independent efficacy campaigns and automatic next-candidate deployment remain separate work.
