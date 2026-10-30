# System Meta-Review v1

Use this protocol to review Agent Memory itself and propose improvements to its rules,
Query, Learn, Reflect, data structures, evaluators or delivery. It is an Agent-side
workflow with optional explicit Runtime persistence. The model review and trigger remain
client responsibilities; there is no new model connection, background worker or task hook.
The supporting Runtime has passed isolated regressions. One real Codex ordinary-task
fixture also executed the installed handoff; this does not establish universal host adherence.

## Trigger At A Real Task Boundary

Apply the current user's instructions first. Do not recursively start an automatic
meta-review while already reviewing or implementing a meta-review.

1. An explicit user request can trigger a review during or after a task. State the
   observed scope; do not describe an unfinished task as completed.
2. Otherwise consider review when a real task completes, fails or becomes blocked,
   and that task used or explicitly requested an Agent Memory capability.
3. Review automatically only for a concrete system-relevant signal: a failed Memory
   operation, a user correction of Memory/tool behavior, an inspected contradiction
   with returned evidence, or at least two observed query rounds that leave the same
   named gap with no new inspectable evidence. A signal warrants review, not a defect verdict.
4. A normal empty result, pagination, truncation, or an expected stale-source warning
   alone does not trigger review. In v1, automatic review of successful tasks without
   a signal is disabled; do not invent a sampling decision.
5. On user cancellation, stop as requested. Do not prolong the cancelled task with
   an automatic review. A later explicit review is a separate user instruction.

Use a host task ID when available. A session-local key for the actual current task
is acceptable if marked `client_local`; it is not a cohort enrollment or proof of
independent tasks. Reuse that key for retries and revisions. If the association cannot
be retained, skip automatic review and offer only an explicitly requested bounded review.

Within the current task context, retain the review reference and revision so the automatic
path emits at most one review per logical task. An explicit update revises that review;
it does not create another independent evidence case. Across sessions, exactly-once
execution is not guaranteed by this Skill. The new explicit writer can retain a thread
across sessions when installed and authorized, but it cannot discover task boundaries or
authenticate task identities. Without a successful save, context-only state is not durable.

For the installed deterministic decision helper or an authorized durable slot, read
[system-trigger.md](system-trigger.md) before generating the review. `reflect-system-trigger`
is read-only by default; explicit --claim reserves one slot without invoking a model.
Automatic generation after requesting a slot requires claim_created=true. Reserved slots
are not live-process evidence, and command availability does not guarantee host invocation.

## Bounds And Evidence

Initial v1 limits are design defaults, not measured optima. Explicit report saving now
checks input shape and size; task triggering and emitted-response budgets still depend
on the client following this protocol:

- At most one automatic review, eight distinct evidence references, five check assertions and
  one system-change proposal per logical task; no automatic retry.
- Keep the complete emitted review within 4,000 Unicode characters. Prioritize the
  concrete issue and record omitted counts or gaps rather than presenting a partial list
  as exhaustive. A smaller user or host budget takes precedence.
- Reuse the current Agent and already inspected task evidence. Do not create another
  model/API connection or run extra checks merely to fill the review.
- Further investigation, patching and validation are separate maintenance/development
  work governed by existing authorization. Respect a user instruction to skip verification.

Use actual project/archive, source, query and version identities when available. Read
only needed existing metadata; do not initialize, learn, refresh or replay a query just
to prepare a review. Missing identities or inaccessible tool events remain explicit gaps.
Do not assume the installed Runtime source repository or a task-end hook is available.

Separate observed facts, source/tool checks, model assessments and causal claims. A check
can be `pass` or `fail` only for a named assertion with an expected basis and actual
observed evidence; otherwise use `unknown` or `not_run`. Task success alone does not prove
Memory benefit. A model opinion or another model vote is not an independently verified result.

Keep brief evidence summaries and references, not raw task/query text, commands, logs,
source bodies, tool-output dumps, secrets or private reasoning. Give a concise justification,
not a reasoning transcript. A digest identifies material but cannot replace missing replay input.

## Emit A Review, Not Project Memory

Return the following logical groups in the conversation. Use nulls, empty lists and
explicit gaps where information is unavailable. The new `reflect-system` writer accepts
the dedicated format below; ordinary `reflect --payload` and MCP do not gain these fields.

| Group | Required meaning |
|---|---|
| `report_format` | `system-meta-review/v1`, the dedicated writer's report format |
| `task_ref` | Task key and origin (`host` or `client_local`), or null when not established |
| `review_revision` | Starts at 1 for an actual review; explicit revisions retain the task/review association |
| `trigger`, `task_state` | Why review started; actual task state, including unfinished/manual scope |
| `task_outcome`, `memory_use` | Task success/failure/partial/unknown and observed Memory used/not_used/unknown, separately from task closure and model usefulness opinions |
| `version_refs`, `query_refs` | Available Runtime/Skill/protocol/source/archive/generation and call identities; never invent them |
| `observations`, `checks` | Brief facts and cited assertions; check result is pass/fail/unknown/not_run |
| `model_opinions` | Advisory relevance/usefulness/clarity opinions, brief basis and counter-evidence |
| `target_components` | memory, rules, query, learn, reflect, data_model, evaluator or delivery |
| `change_proposals` | Zero or one bounded proposal using the fields below |
| `missing_evidence`, `omitted_counts` | Missing identities/materials/coverage and known omissions |
| `additional_cost` | Available extra Token and elapsed-time measurements; unavailable values are null |
| `review_status`, `advisory_only` | completed/partial/skipped/failed; `advisory_only` is true |

`completed` means the review was completed, not that functionality passed or a proposal
was applied. No actual review means no fabricated success record; a blank documentation
template can use `not_run`, which is not an executed-review outcome.

A system-change proposal identifies:

- A real proposal/task association, target component and change kind: defect,
  requirement or structural change. Missing durable IDs must not be presented as stored records.
- A concrete observed problem or explicitly requested new behavior, evidence references,
  suspected/proven layer and missing evidence. Distinguish observations from hypotheses.
- The base versions, affected scope, alternatives and smallest proposed mechanism change.
- The intended artifact: rule/Skill/config diff, Runtime patch, or structural/migration
  design. Do not replace a system change with an unrelated new business-memory entry.
- Acceptance assertions, counterexamples, public-contract compatibility, cost constraints
  and the migration/rollback requirements where relevant.
- `proposal_state`: `proposed` or `needs_evidence` at review emission. Later preparation,
  checks, application and rollback belong to maintenance/development work.

If no issue is supported, emit no proposal. If evidence is insufficient, identify the
gap instead of inventing a defect or a repair. One proposal may include necessary code,
rule and data changes for one mechanism, but not unrelated optimizations.

Do not send this review to `reflect`, `update`, `experience-usage` or `retrieval-feedback`.
Do not automatically mark anything verified/confirmed, mutate ranking signals, patch
installed Runtime code or migrate a database. Ordinary project lessons remain a separate
Reflect workflow; they must not inherit an unverified system-review verdict.

## Optional Explicit Persistence

When the user has authorized local system-review recording and the installed Runtime
supports the new writer, save only an actual review with:

```bash
python3 tools/agent_memory.py reflect-system --project . --review-key <namespaced-review-key> --payload-file <review.json> --json
```

Use the actual archive/memory-home binding. This command requires an initialized archive;
do not silently initialize or migrate one merely to save a review. If the installed
writer is unavailable, return the conversation review and the limitation instead.

The report must include every group in the table. `task_ref` has only `key` and `origin`;
client-local keys and review-key must be namespaced within the archive. observations have
summary/refs; checks have assertion/expected_ref/observed_refs/result/scope; model opinions
have dimension/assessment/evidence_refs/counter_evidence_refs. Version keys are
runtime_revision/runtime_digest/skill_revision/skill_digest/protocol_version/source_revision/
source_digest/archive_project_id/index_generation, with missing values null.

A proposal requires target_component/change_kind/problem/proposed_change/evidence_refs/
acceptance_criteria/compatibility/rollback/proposal_state; optional keys are proven_layer,
alternatives, migration and artifact_refs. additional_cost contains tokens/elapsed_ms;
omitted_counts permits observations/checks/model_opinions/change_proposals/evidence_refs.
Use compact UTF-8 JSON within 4,000 characters; unsupported fields are rejected, not silently ignored.
References and version strings are at most 240 characters, observation summaries 500,
assertions/scope/criteria/gaps/alternatives 300, opinion dimensions 80 and assessments 400.
The four proposal prose fields are at most 600 characters each; proven_layer/migration
are at most 400. Limit observations/gaps to eight, opinions/checks/criteria to five and
alternatives to three. Every list of references has at most eight items, with at most
eight distinct references across the report. Use explicit gaps rather than oversized dumps.

Saving is idempotent for the same review-key/revision/content; changed content needs the
next consecutive revision. A task cannot be silently rebound or placed in a second thread.
Each revision preserves old reports and creates a separate proposal snapshot when present;
it does not overwrite an older prepared proposal. Review thread counts do not prove
independent real tasks. Shape checks and saved check labels do not authenticate evidence.

## Handoff And Completion

Return the bounded review and, when supported, one proposal. Hand system-change follow-up
to the installed `agent-memory-maintain` Skill when available; that Skill loads its own
`references/system-evolution.md`. If the Skill or its reference is absent, present the
proposal and the missing workflow rather than inventing a command.

The source package includes explicit governance persistence with isolated synthetic regression coverage.
Saving a review does not update installed copies, guarantee host invocation or run checks.
Any authorized explicit checking belongs to Maintain's separate plan workflow; MCP is
not implemented. State what actually ran, what was saved, and what remains unverified.
