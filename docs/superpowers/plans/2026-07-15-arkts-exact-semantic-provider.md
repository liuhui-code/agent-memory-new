# ArkTS Exact Semantic Provider Execution Plan

**Goal:** Add a production-safe, language-neutral external semantic-provider path for ArkTS, measure it against the existing static adapter, and let design, impact, and Incident consumers prefer higher-authority evidence without making the compiler toolchain a runtime dependency.

**Architecture:** Learning remains the only indexing entry. An explicitly configured executable receives a bounded `semantic-provider-request/v1` JSON document on stdin and returns a correlated `semantic-provider-result/v1` envelope containing a validated `semantic-index/v1` batch. Auto mode tries the external provider and falls back to the built-in static adapter. SQLite remains the source of truth; bounded provider telemetry is operational JSONL under `runtime/`.

**Boundaries:** Keep four public Skills, one CLI entry, no daemon, no shell command execution, no project-controlled provider configuration, no raw AST persistence, no graph/vector database, no runtime LLM, and every Python file at or below 500 lines.

## Phase 1: Provider Protocol

- [x] Define request/result schemas, correlation id, provider identity, toolchain, capabilities, file digests, and hard limits.
- [x] Accept provider configuration only from an explicit process environment variable.
- [x] Require a single executable path; invoke without a shell or project-provided arguments.
- [x] Validate source paths, source digests, language, deterministic symbol keys, exact evidence class, and batch bounds.
- [x] Reject malformed JSON, mismatched request ids, stale source output, unsupported schemas, and unsafe paths.

Acceptance:

- A provider cannot index files outside the requested project scope.
- Provider output cannot claim `exact` for stale source content.
- Existing `semantic-index/v1` consumers require no provider-specific branches.

## Phase 2: Bounded Process Execution and Fallback

- [x] Add timeout, accepted stdout size, bounded stderr diagnostics, deterministic cwd, and failure classification.
- [x] Implement `auto`, `external`, and `static` selection modes.
- [x] In learning, use `auto`: exact success wins; absence, timeout, nonzero exit, or invalid output falls back to static.
- [x] Surface selected adapter, duration, output bytes, fallback reason, and provider status in `parse_stats.semantic_index`.
- [x] Preserve exact-over-static duplicate-edge authority and active-edge lifecycle metadata.

Acceptance:

- Provider failure never makes learning fail when static fallback succeeds.
- Forced external evaluation fails clearly instead of silently falling back.
- No provider process remains running after timeout.

## Phase 3: ArkTS Integration Point

- [x] Register `AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS` as the opt-in ArkTS executable path.
- [x] Send only requested relative files and digests; the provider reads source from the project cwd.
- [x] Require exact ArkTS entities and relations to use the stable SemanticIndex contract.
- [x] Keep es2panda, language-server, or SCIP bridge implementation outside core runtime modules.
- [x] Document a provider authoring contract and an executable test-provider example.

Acceptance:

- Replacing the executable does not change graph, storage, Impact, Incident, or Skill code.
- TypeScript and future languages can reuse the same process protocol with a language-specific environment variable.

## Phase 4: Evidence Consumption and Governance

- [x] Rank Impact links by evidence precision before confidence and deduplication.
- [x] Rank Incident traversal edges by evidence precision before confidence and recency.
- [x] Continue labeling static/exact code paths as `possible` unless runtime evidence supports them.
- [x] Add compact bounded provider-run telemetry and health summary.
- [x] Add a Maintain action when configured provider attempts repeatedly fail or fall back.

Acceptance:

- Exact evidence is selected first but never upgraded to observed causality.
- Provider telemetry is bounded and does not grow the SQLite source-of-truth database.
- Governance proposes review; it does not execute or install a provider.

## Phase 5: Semantic Quality Evaluation

- [x] Add `eval-semantic --cases ... --mode static|auto|external` through a separate CLI parser module.
- [x] Define `semantic-eval-cases/v1` fixtures with files, expected relations, forbidden relations, and minimum evidence class.
- [x] Report expected recall, forbidden-edge rate, resolution rate, entity/relation growth, gaps, latency, output size, provider use, and fallback.
- [x] In auto/external mode, compare selected results with the built-in static baseline and report common, exact-only, and static-only relations.
- [x] Keep evaluation temporary and read-only for the target project.

Acceptance:

- A checked-in ArkTS golden pack covers local calls, typed cross-file calls, state flow, callbacks, inheritance, async, and API boundaries.
- Evaluation exposes disagreement rather than treating every difference as an error.

## Phase 6: Scale and Release Gates

- [x] Add tests for success, unavailable provider, timeout, nonzero exit, malformed output, stale digest, unsafe path, oversize output, and static fallback.
- [x] Add tests for exact edge persistence, Impact ordering, Incident ordering/roles, telemetry bounds, and Maintain action generation.
- [x] Add a many-file request test to preserve SQLite and protocol batching behavior.
- [x] Update README, runtime, schema, semantic-index, Skill protocol, Learn/Maintain instructions, and `gitlog.md`.
- [x] Run focused/full tests, compilation, CLI help, golden evaluation, diff checks, four-Skill check, and 500-line gate.

## Performance Guardrails

- Default timeout: 20 seconds per provider invocation.
- Accepted stdout: at most 16 MiB; stderr diagnostics retained at at most 32 KiB.
- Request limits inherit `semantic-index/v1`: 5,000 files, 50,000 entities, 100,000 relations, and 1,000 gaps.
- Provider telemetry retains at most 200 compact records.
- Learning invokes at most one external provider per language/scope and never starts a background process.
- Static comparison runs only under `eval-semantic`, not normal learning.

## Rollback

Unset the provider environment variable or remove external candidate selection. Learning immediately returns to the built-in static adapter. Existing exact edges remain normal versioned SQLite edges and are replaced by the next focused refresh; no destructive schema rollback is required.
