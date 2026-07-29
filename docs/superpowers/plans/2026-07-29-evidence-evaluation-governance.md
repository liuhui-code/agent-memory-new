# Evidence Evaluation Governance

## Objective

Make context retrieval improvements attributable, reproducible, and safe to promote. The Runtime remains a context provider: it ranks and compresses source, log, graph, and memory evidence. The local Agent CLI owns diagnosis, design reasoning, and verification.

## Design

The evaluation pipeline has two independent tracks.

1. **Strict context gate.** `eval-context-capability` evaluates compact context without an Agent response. A case records the first missed stage in `candidate_file -> localizer_file -> callable -> source_range -> evidence_primary -> compact_primary -> compact_anchor`. The aggregate funnel is informational, so it locates loss without silently changing ranking or a promotion decision.
2. **Agent evidence utility.** `eval-agent-benchmark` compares baseline and memory-assisted Agent runs offline. It measures whether the Agent inspected expected source, had sufficient evidence before a supported/verified claim, reported uncertainty after missing evidence, and avoided unnecessary non-anchor files. It is deliberately not a Runtime promotion gate.

Case packs may declare `governance.evaluation`: split (`development`, `calibration`, `holdout`), change policy (`editable`, `frozen`, `sealed`), source isolation, and per-case lineage. Legacy packs remain valid but are reported as unclassified. Development may tune, calibration is frozen, and an external holdout must be sealed.

## Execution Plan

- [x] Add evaluation governance validation and persist classification with benchmark outputs.
- [x] Add funnel-level loss attribution using existing query audit and compact handoff fields.
- [x] Add independent Agent evidence-utility metrics without inspecting private reasoning or generating Runtime conclusions.
- [x] Add a project-neutral ArkTS development fixture with ViewModel, Store, and Component owner roles, two user phrasings each, and same-domain decoys.
- [x] Add unit regression coverage for governance, funnel attribution, and Agent evidence utility.
- [x] Apply bounded callable-focused compact projection after the funnel isolated compact ranking precision as the first failing layer.
- [x] Run focused tests, the neutral context capability suite, full suite, scale guard, and line-limit guard.

## Verification Result

The neutral development suite passed all six query variants across ViewModel, Store, and Component roles. File, callable, range, primary evidence, and compact-anchor stage pass rates were all 1.0; average compact context was 941 tokens. The full suite passed 692 tests. The CI scale profile passed at 100,000 searchable entities, 80,000 symbols, and 300,000 edges; candidate recall hit/miss p95 was 47.193/74.712 ms and bounded one-hop owner lookup p95 was 18.773 ms. These are development results, not an external holdout claim.

## Promotion Rules

Only a passing strict context gate and its applicable calibration contract may mark a Runtime context change as promotion-eligible. Funnel metrics tell maintainers where to investigate. Agent A/B and external holdout results are review evidence, never automatic tuning instructions. Do not alter sealed holdouts after observing their results; create a separately governed case pack instead.

## References

- TREC separates development from final test data and recommends late release of final relevance judgments: <https://trec.nist.gov/howto.html>
- BEIR evaluates retrieval across heterogeneous datasets to measure out-of-distribution robustness rather than a single tuned corpus: <https://arxiv.org/abs/2104.08663>
- SWE-bench documents dataset construction and split-aware evaluation for software-engineering agents: <https://www.swebench.com/SWE-bench/guides/datasets/>
