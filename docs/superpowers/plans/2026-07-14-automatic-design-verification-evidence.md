# Automatic Design Verification Evidence Plan

**Goal:** Remove caller-supplied verification blind spots by collecting symbol, API, source-graph, and test evidence automatically without executing arbitrary commands or persisting source/diffs/logs.

## Boundaries

- `design-verify` remains read-only and deterministic.
- Git is invoked with argument arrays only; no shell-generated commands.
- Test commands are not executed by the runtime. Existing machine-readable reports are parsed.
- Source, Git diff bodies, test report bodies, and reasoning are never persisted.
- Existing `--files`, `--actual-symbols`, `--executed-tests`, and `--test-evidence` inputs remain compatible.
- Keep the four public Skills, SQLite truth, one runtime entry, and the 500-line file limit.

## Phase 1: Diff Evidence

- [x] Read zero-context Git diff from `--base` or caller-owned `--diff-file`.
- [x] Parse added/deleted line ranges and rename-aware paths with strict bounds.
- [x] Map current changed lines to fresh semantic entity spans.
- [x] Fall back to learned symbol spans only when fresh source parsing is unavailable.
- [x] Distinguish automatic and explicit symbol evidence.

## Phase 2: API and Source Graph Delta

- [x] Parse supported current and Git-base ArkTS/TypeScript source through the language adapter parser.
- [x] Compare exported entity additions, removals, and signature changes.
- [x] Compare normalized source relations before and after the change.
- [x] Report unsupported languages, missing base files, and parser gaps explicitly.
- [x] Bind all evidence to base revision and current source digest without storing source.

## Phase 3: Test Report Evidence

- [x] Add repeatable `--test-report` input.
- [x] Parse JUnit XML suites/cases, failures, errors, skips, and optional verification properties.
- [x] Parse generic `test-report/v1`, pytest-json-report, and Jest-style JSON.
- [x] Merge reports with explicit `test-evidence/v1` and legacy commands deterministically.
- [x] Cap reports, tests, summaries, and verification references.

## Phase 4: Design Verification Integration

- [x] Use automatic symbols when explicit symbols are absent.
- [x] Expose API and source-graph Delta separately from refreshed learned-graph alignment.
- [x] Add verification capabilities, provenance, evidence gaps, and bounded replan triggers.
- [x] Let passed report evidence satisfy declared verification obligations.
- [x] Keep v1 verification output and direct function callers compatible.

## Phase 5: Quality Gates

- [x] Add end-to-end Git diff, symbol mapping, API signature, JUnit, JSON, compatibility, and failure tests.
- [x] Update design runtime, usage, schema/protocol, Query Skill, Agent, and development log docs.
- [x] Run complete tests, compilation, diff checks, fixed four-Skill count, and 500-line gate.
- [x] Benchmark automatic evidence collection on a representative ArkTS repository.

## Acceptance

- A changed method is identified without `--actual-symbols`.
- An exported signature change is reported with old/new signatures.
- JUnit/JSON failures cannot become verified obligations.
- Source graph Delta and learned graph alignment remain distinct evidence classes.
- No source, diff body, or test report body enters SQLite or Design Outcome.
