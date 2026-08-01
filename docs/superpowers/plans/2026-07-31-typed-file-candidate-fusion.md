# Typed File Candidate Fusion Plan

## Objective

Prevent query-supported structural code evidence from disappearing between bounded
SQLite recall and hierarchical file localization. Keep the existing Context facade,
eight-file budget, one-hop graph depth, and downstream callable/range ranking.

## Evidence

The complete development run has 18 `candidate_file` first losses. Sixteen are Chinese
noise variants. All sixteen queries already map to the intended language-neutral
behavior markers, and every expected source file enters `structural_fts`. The loss
occurs later: the localizer groups file and symbol results by path, sorts only by their
heterogeneous downstream score, and takes eight files. Lexically dense generic symbols
can therefore displace direct structural files even though recall succeeded.

This is a candidate-fusion defect, not a translation or parsing defect.

## Architecture

Keep `SQLiteHierarchicalLocalizer` as the facade behind
`HierarchicalLocalizerPort`. Move file grouping and selection into a dedicated policy
module with a small typed contract:

- aggregate heterogeneous file/symbol records into one file candidate;
- retain ordinary score, first rank, direct symbol IDs, lanes, and reasons;
- derive structural coverage from existing `semantic_behavior_coverage` and
  `structural_behavior` evidence;
- reserve at most three of eight file slots for the strongest structural candidates
  when the query has behavior markers;
- fill all remaining slots with the existing score order and directory-diversity
  policy;
- never increase the candidate budget or add case, path, project, or language-specific
  ranking rules.

This is stratified retrieval and bounded result diversification: heterogeneous evidence
channels keep a minimum representation before ordinary rank fusion fills the remaining
budget. It follows the same principle as vertical/federated search blending and avoids
comparing incomparable raw channel scores as if they shared one calibration.

## Phases

1. Add independent unit cases for structural reservation, budget bounds, and directory
   diversity.
2. Extract the file-candidate policy from the 500-line localizer.
3. Run candidate-loss scenarios and compare every existing case against the 183/231
   baseline. Reject any pass-to-fail regression.
4. Run full Context, query, benchmark, scale, compile, JSON, four-Skill, diff, and
   500-line gates.

## Stop Rules

- Stop if a fix adds a fixture term, path, project name, or Chinese-only weighting.
- Stop if total file/callable/range budgets increase.
- Stop if structural evidence automatically becomes the final compact answer; this
  policy only preserves evidence for callable and range evaluation.
- Stop if aggregate gains hide a previously passing case regression.

## References

- Reciprocal Rank Fusion: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- BEIR heterogeneous retrieval evaluation: https://arxiv.org/abs/2104.08663
- TREC evaluation methodology: https://trec.nist.gov/howto.html

## Execution Result

The first implementation reserved structural files before all other evidence. It raised
the complete gate from 183/231 to 185/231 but displaced an exact callback chain and
reduced owner recall. That version was rejected. Giving identity reservations to every
query then restored the callback but reduced a multi-file property-flow metric; that
version was also rejected.

The accepted policy activates typed reservations only for behavior queries and orders
the lanes as exact identity, structural coverage, then ordinary score fill. All lanes
share the existing directory-diversity policy. Membership is returned in original score
order, so reservation is candidate eligibility rather than a claim of final relevance.
Behavior markers are computed once per query rather than once per candidate.

The evaluator also stopped treating `fielded_retrieval.mode=shadow` candidates as the
served first stage. It now uses fielded candidates only in `serving` mode and otherwise
measures the actual serving candidate references. This changes loss attribution, not
retrieval output or a gate threshold.

The final complete development run passes 185/231 variants and 46/77 stable scenarios,
up from 183/231 and 44/77. Two failed variants become passing and no prior check or
hierarchical metric regresses. Hierarchical file/callable/range recall rises from
0.9271/0.9069/0.8995 to 0.9769/0.9632/0.9338; owner recall and precision remain 1.0.
The overall development gate still fails honestly and is not promotion eligible.

The CI scale gate passes at 100,000 searchable entities and 300,000 edges. Candidate
hit/miss P95 is 46.485/81.839 ms, callable-pool P95 is 16.362 ms, and one-hop-owner P95
is 24.708 ms. Incremental no-change, outside-scope, single-file, and large-method P95
are 277.141, 203.947, 1,371.131, and 2,821.429 ms respectively. Related query/Context
tests pass 107/107 and benchmark/governance tests pass 97/97. Compile, evaluation JSON,
diff, four-Skill, and 500-line checks pass. No consumed external holdout was read,
changed, or rerun.
