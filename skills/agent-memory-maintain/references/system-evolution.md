# System Evolution v1

Use this protocol for an explicit Agent Memory system-improvement request or a bounded
system-change proposal. It covers rules, Query, Learn, Reflect, data structures,
evaluators and delivery, alongside ordinary memory maintenance. It is a client workflow;
the supporting Runtime has passed isolated synthetic regressions. Explicit commands store and inspect
isolated governance records. Explicit scoped check execution is available in source;
advanced states, application and governance migration use the explicit
[lifecycle protocol](system-lifecycle.md), never model-filled state claims.

## Establish The Target And Authority

Identify the Agent Memory source/development copy, base Runtime/Skill/protocol/data
versions, affected archive/scope, evidence and currently authorized work. Distinguish
the user's business repository from the Memory software to be changed.

If only an installed copy is available, prepare a proposal or patch draft within the
authorized scope; do not assume access or permission to publish an upstream release.
Existing authorization persists across steps. Do not ask again for routine work already
covered, but do not treat feedback collection as permission to change installed code,
migrate user data, publish or upload task material.

A proposal must name its target component, change kind, concrete issue/requirement,
evidence and gaps, base versions, intended artifact, compatibility, checks and rollback.
Keep it out of ordinary project-memory records and ranking feedback. New Runtime versions
can explicitly save reports and proposal snapshots in dedicated SQLite governance tables.
Inspect real returned record IDs; conversation-only proposals are not persisted records.

## Inspect And Record Governance State

Use `maintain-system --json` for a bounded summary, `--review-key <key>` for the latest
report and revision metadata, `--change-id <id>` for a proposal, audit events and bounded
check-run history, or `--run-key <key>` for one execution record.
Bind the real --project/--memory-home; limit is 1-20, default 5. These reads do not create
an archive or governance tables. State filtering is for summary lists only.

```bash
python3 tools/agent_memory.py maintain-system --project . --limit 5 --json
python3 tools/agent_memory.py maintain-system --project . --change-id <id> --json
python3 tools/agent_memory.py maintain-system-status --project . --id <id> --expected-revision <state_revision> --status needs_evidence --note <brief-reason> --json
```

State changes need the observed state_revision and an actual note; stale writers fail.
`prepared` additionally requires --development-root, --base-version and 1-3 relative
--artifact-file paths inside that directory. Each file is bounded at 1 MiB; the writer
stores byte digests and metadata only. The base version remains caller-declared; no
code, SQL, tests, installation or application is executed by observing an artifact.
Use only artifact paths covered by the current authorization.

If the archive/registry is absent, report the gap and use already available proposals;
do not run ordinary initialization or repair by default. If the installed Runtime lacks
these commands, retain the client workflow and explicitly state the version limitation.

## Match The Evidence To The Change

- For a serving defect, require an independent controlled reproduction in the actual
  public query output and identify the first proven failing layer before changing behavior.
- For a new requirement, make the intended behavior and compatibility scope explicit;
  do not label old behavior defective merely because it differs from a new proposal.
- For a new domain/architecture abstraction, require at least two independent defect
  classes demonstrating the missing contract. Different retries or model opinions do not qualify.
- Change an evaluator only when it misclassifies a controlled case with an independently
  known expected result. A candidate cannot pass by lowering its own acceptance standard.
- Preserve classified/consumed sealed evaluation assets and current project rules.
  Evidence gaps stop the affected change, not unrelated authorized work.

Model assessments help formulate hypotheses. Format validation, evidence strings,
verified flags, reported states and task success do not authenticate correctness or benefit.
Do not generate missing logs, symptoms, causal paths, approvals or Oracle evidence.

## Prepare A Concrete Artifact

Work in an authorized development copy. Produce the smallest coherent rule/Skill/config
diff, Runtime patch or structural change. Declare the target assertions, counterexamples,
unaffected capabilities and cost/performance constraints before evaluating the candidate.

For Query/Learn/Reflect changes, inspect actual selected inputs, extraction, persisted
records/generation, candidates, selection/compression and Agent use as evidence permits.
Do not assume a missing query result is a ranking defect or compensate indefinitely for
a learning defect by adding task-specific terms.

Same-version CLI/MCP adapters and the review workflow must preserve query behavior in
equivalent state. A new algorithm version may intentionally improve results while keeping
input/output types, defaults, status meanings, provenance and budget contracts compatible.
Breaking public changes need an explicit version and upgrade path.

For data-model changes, prepare:

1. The demonstrated expression gap, alternatives and old/new identities/field/relationship mapping.
2. An old/new Runtime versus old/new data read/write support matrix; unknown is not supported.
3. Migration/backfill/derived-rebuild artifacts, data-preservation assertions, idempotency,
   checkpoints and interruption/retry boundaries, including initialization on ordinary commands.
4. A backup/recovery and switch-over plan that covers writes after upgrade. Code rollback,
   data restore and forward repair have distinct conditions; do not promise one undoes another.

Do not run ad hoc model-generated SQL against the user's live archive. Keep SQLite as
truth, derived indexes/mirrors regenerable, and missing legacy evidence explicitly unknown.

## Check, Apply And Follow Up

For an actual Git-patch test subject, read [system-candidates.md](system-candidates.md)
to prepare a separate baseline-plus-patch copy and bind check plan v2 to it. Preparation
changes that isolated copy only and leaves proposal/product application states unchanged.

When actual checking is authorized, read [system-checks.md](system-checks.md) to prepare,
preview and explicitly execute a bounded plan through `maintain-system-check`. Its source
has isolated synthetic regression coverage. It records process observations and declared file bindings, keeps
the proposal prepared and does not certify test coverage or product correctness.

The original status writer supports proposed, needs_evidence, prepared, rejected and
superseded only. It refuses directly filled checked/applied/monitoring/closed/rolled_back.
The dedicated lifecycle entries establish the required bounded conditions; a check-run
receipt alone does not satisfy them:

| State | Meaning and transition condition |
|---|---|
| `proposed` | Bounded idea; no implementation or validation implied |
| `needs_evidence` | Missing reproduction, identity, source or authorization; state the specific gap |
| `prepared` | Actual version-bound artifact and its check/rollback plan exist |
| `checked` | All required checks actually ran against the bound artifact and passed; retain their references |
| `applied` | The checked artifact was actually applied within existing authorization and version compatibility |
| `monitoring` | Observing the applied version under predeclared scope; not proof of causal improvement |
| `closed` | The declared closure conditions and outstanding gaps are recorded |
| `rejected`, `superseded`, `rolled_back` | Preserve the reason, lineage and actual artifacts/results; do not erase failed candidates |

Do not advance state based solely on a model-written label. Missing, failed or skipped
checks cannot produce `checked`. A prepared unvalidated artifact can remain `prepared`.
Revise a failed candidate using the same proposal lineage; do not retry consumed holdouts.

For the current stored `prepared` state, only the listed file-byte observations have
been performed by the writer; metadata and plans remain advisory. A new review revision
creates an immutable candidate snapshot rather than overwriting the prior proposal.
Explicitly supersede an old snapshot when warranted, recording its replacement in the note.
The candidate's embedded proposal_state is its original snapshot; use the returned
top-level state and state_revision to track current governance state.

When checks are authorized, use the applicable focused, full, performance and compatibility
gates in isolated equivalent archives; compare only predeclared differences and include
all additional cost. When verification is skipped, prepare artifacts/plans only and report
the unvalidated state. Read-only inspection of existing evidence does not justify marking
unexecuted tests as passed.

Application and publication follow current user authorization and project policy. Apply
only the checked version; any artifact edit after checking invalidates that check binding.
If a rollback condition occurs, use the declared code/data recovery path and record what
actually happened. No generic rollback or upgrade command is introduced by this reference.

Finish with the proposal/task references, actual artifact/base versions, check and application
states, evidence gaps and next bounded action. Keep private task material local unless the
user explicitly authorizes a specific export or sharing action.
