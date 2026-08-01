# Context Supply Repair Development Plan

## Objective

Repair independently reproducible Context supply defects without reading, rerunning,
or tuning against any consumed external holdout. Keep `context` as the sole public
retrieval facade and keep diagnosis in the local Agent CLI.

## Method Basis

- BEIR treats BM25 as a strong general baseline while showing that heterogeneous
  retrieval benefits from explicit reranking and must be validated out of domain:
  <https://arxiv.org/abs/2104.08663>.
- TREC Deep Learning evaluates document and passage ranking as distinct tasks; finding
  a file is not equivalent to selecting the useful passage:
  <https://www.nist.gov/publications/overview-trec-2019-deep-learning-track>.
- GraphRAG local search maps structured entities to candidate text units, then ranks
  and filters those units into a bounded context:
  <https://microsoft.github.io/graphrag/query/local_search/>.

The repository already has the matching boundaries: `CandidateRecallPort`, a derived
fielded `code_passage_fts`, `HierarchicalLocalizerPort`, and current-source excerpt
selection. This phase may promote or complete those boundaries; it must not add a new
query command, vector store, graph database, or Agent-side diagnosis implementation.

## Evidence Before Change

Create project-neutral, editable development fixtures and prove each failure through
the public compact `context` handoff:

1. **String-key callable recall.** A callable is identified only by a persisted literal
   key. The current broad symbol index must miss it while the fielded `string_key_fts`
   lane contains it.
2. **Mechanism callable recall.** A callable is identified by a normalized static
   mechanism rather than its file or symbol name. The current serving candidates must
   miss it while the fielded `semantic_mechanism_fts` lane contains it.
3. **Large-file passage selection.** A known callable begins after the global source
   scan boundary and its query-relevant expression is beyond the first excerpt page.
   The handoff must locate the callable yet omit the expression.

The first two are independent defect classes supporting one missing fielded-candidate
contract. The third supports a separate random-access passage contract. If a fixture
does not reproduce in the public handoff, do not change its owning layer.

## Execution Slices

### Slice A: Fielded Candidate Serving

1. Add one public string-key fixture and establish RED.
2. Route existing fielded passage rankings into bounded reciprocal-rank fusion through
   `CandidateRecallPort`; preserve current table limits, freshness filtering, and audit.
3. Establish GREEN and verify the target callable and current-source excerpt are visible
   in compact Context.
4. Add the mechanism fixture, establish RED, and complete only the common fielded
   contract needed by both cases.
5. Mark the fielded audit as serving and retain explicit channel provenance. Full and
   compact Context must use the same serving candidates.

### Slice B: Random-Access Source Window

1. Add the large-file public fixture and establish RED.
2. Read a bounded interval from the selected callable rather than rescanning only the
   first 4,000 lines of the file.
3. Rank lines inside that interval with the existing query-focused policy and translate
   local offsets back to absolute source lines.
4. Keep path containment, maximum scan size, excerpt line count, character budget, and
   non-persistence guarantees unchanged.

### Slice C: Regression and Decision

1. Run focused candidate, localization, excerpt, compact-context, and evaluation tests.
2. Run classified development capability packs; record baseline and final per-case
   metrics without changing their Oracles after execution.
3. Run the complete unit suite, million-entity performance gate, four-Skill check,
   JSON validation, diff hygiene, and the 500-line Python gate.
4. Record proved behavior, residual gaps, and performance cost in `gitlog.md`.
5. Do not rerun a consumed holdout. A future promotion claim requires a new source
   selected after this implementation is frozen.

## Acceptance

- Both fielded fixtures expose the expected callable and source excerpt through compact
  `query_handoff`, with bounded channel audit and no new public command.
- The large-file fixture returns an excerpt overlapping the required expression while
  remaining within the existing Context budget.
- No Runtime output asserts a cause or diagnosis.
- No Python file exceeds 500 lines; exactly four user-facing Skills remain.
- Existing classified development, full regression, and performance gates do not
  regress.

## Completed Outcome

- Added three public-handoff development regressions. The string-key, normalized
  mechanism, and late-callable excerpt cases all reproduce before their owning-layer
  changes and pass afterward.
- Promoted the existing fielded passage channels into bounded serving RRF for full and
  compact Context. String and mechanism evidence contributes to downstream scoring only
  when that field supplied the candidate.
- Added bounded interval reads for already-selected callable ranges after the 4,000-line
  source prefix. Existing excerpt and Token limits remain unchanged.
- Fixed the shared source-location projection contract exposed by serving promotion:
  file evidence may inherit a callable location, while resource and route identity is
  not overwritten. The controlled log-query test now treats omitted unrelated resource
  noise as lower rank rather than as an error.
- The new development pack passes 2/2 with 1.0 query-variant pass rate and 958.5 average
  estimated Context tokens. Callable-range generalization remains 2/2; localization
  development remains at its accepted 4/5 baseline, with only the pre-existing
  cross-language cache-key gap.
- The CI scale profile passes all gates at 100,000 searchable entities. The million
  profile passes candidate-query latency and query-plan gates, including 352.751 ms
  candidate-hit P95 against 800 ms, but its independent maintenance gate fails because
  summarize and graph-rebuild phases exceed their SLOs. This query change does not call
  either maintenance phase, so the failure is recorded rather than tuned here.
- Focused suites pass 55/55 and 23/23. The first restricted full run passes 803/806;
  two errors are the known loopback socket restriction, and the one source-projection
  failure is independently reproduced and covered by the subsequent focused runs.
- No consumed holdout was read, modified, or rerun. A future promotion decision requires
  a newly selected external source after this implementation is frozen.
