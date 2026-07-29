# Callable Evidence Funnel Plan

## Goal

Make the Runtime a better evidence provider for Agent CLI diagnosis without
turning it into a root-cause engine. A query must retain the distinction between
file recall, callable selection, source-range selection, and Agent reasoning.

## Mature Basis

- Tree-sitter documents an incremental, error-tolerant concrete syntax tree
  model with source positions and named nodes. This project keeps its light
  parser today, but models the same adapter boundary so another parser can
  replace it later. <https://tree-sitter.github.io/tree-sitter/index.html>
- RepoBench evaluates repository retrieval separately from downstream code
  completion; its retrieval task reinforces testing context selection as an
  independent stage. <https://arxiv.org/abs/2306.03091>
- CORE-Bench separates code understanding, issue-to-edit localization, and
  broader-context retrieval. It motivates separate file/callable/range metrics
  instead of a single top-hit score. <https://arxiv.org/abs/2606.11864>

## Architecture

`semantic-index/v1` gains optional, backwards-compatible callable metadata:

- `owner_name` and `owner_kind`: the enclosing owner and its stable role;
- `callable_roles`: inspectable boundaries such as `async`, `guard`,
  `state_write`, `persistence_write`, and `navigation`;
- existing `mechanism_evidence`: operation, guard, resource, callback,
  platform, and persistence detail remains the structured operation layer.

The ArkTS/ECMA adapter emits this profile. Other languages implement the same
fields; query code never depends on ArkTS syntax. SQLite persists the values on
`code_symbols`, with a bounded owner-kind index.

The existing localizer remains bounded at file -> callable -> one-hop owner ->
source range. It now runs once per Context request and creates an advisory
`callable_evidence` projection:

- `primary`: highest retrieval candidate with a bounded source range when one
  exists;
- `alternatives`: at most two candidates that differ by file/owner role;
- `certainty`: `bounded`, `uncertain`, or `unavailable` from ranking margin
  and source-range availability;
- `boundary`: explicitly says retrieval evidence, not root cause.

Existing `code_anchors` remain the served compatibility path. This phase does
not promote the advisory projection to replace them: four consumed external
ArkTS holdouts deny that promotion. The Agent can compare the primary and
alternatives against temporary logs and current source.

## Execution Plan

1. Add the profile contract, migration, ArkTS emission, and focused persistence
   tests. Completed in this change.
2. Make the localizer a single Context funnel and expose the compact advisory
   projection without a new CLI command. Completed in this change.
3. Add neutral fixtures covering role disambiguation, same-mechanism competing
   owners, range absence, and multi-phrasing evaluation. Pending.
4. Promote any projection only after development, scale, full regression, and
   a new source-reviewed immutable external holdout all pass. Pending.

## Non-goals

No vector database, parser dependency, fifth Skill, temporary-log ingestion,
root-cause prediction, or unbounded graph traversal is added.
