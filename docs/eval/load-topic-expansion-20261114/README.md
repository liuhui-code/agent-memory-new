# Generic loading verb is not a user/network topic (Development)

Serving baseline 134cfcb. The Chinese verb 加载 previously emitted load/request/fetch/
network/profile/account/user/data. Its general meaning does not justify the user,
account or network topic. This change splits ONLY 加载 into the translation load.
The five remaining 请求/接口/网络/用户/资料 trigger expansions are byte-for-byte
unchanged; no scores, weights, thresholds, query scope or owner certificates change.

## Independent frozen public reproduction

The minimal source fixture contains a byte texture decoder, disk scene reader,
user profile loader and network requester. Before implementation, both local-owner
queries containing 加载 select ProfileService in actual compact query_handoff, while
the corresponding queries without that verb select the real local source. The same
frozen queries and required owner/source assertions pass after the split, with real
decodeTexture/readScene snippets. Merely removing an unwanted owner is not sufficient.

The first protocol had six queries. A seventh explicitly named network query was
added before production change, with all initial output retained in before.json and
frozen-before.json. Both generic and explicitly named network requests are OLD red
controls: the generic selects ProfileService, and the named request returns four
owners. Their query/oracle and observed paths are unchanged after this fix. They are
preserved as two expectedFailure tests, not reported as repaired or passing. The
positive user-profile query stays passing. The existing data-topic public test also
actually reruns the positive 加载用户资料的网络实现 request and real network.fetch body.

## Validation and scope

- Frozen public observations: the two loading failures improve; the other five
  observed path lists are identical, including the two network failures.
- 50 necessary focused tests: 47 pass, 3 expected failures (two OLD network controls
  explicitly retained here plus one historical weak-log expectedFailure).
- The older data-topic unit test captured the previous loading expansion as a
  compatibility contract. Only 加载 is removed from its broad-topic trigger assertion,
  because the new independently demonstrated contract is load-only. The five other
  triggers remain asserted intact; the new test expressly forbids network/user/data
  tokens for generic loading. No original evaluator or oracle is edited.
- Post-hoc selected original source-replacement group: 1/3 -> 2/3. Only zh-noise
  changes from ProfileService to SourceSwapCoordinator and passes all original
  anchor/source-span checks. English original remains WrappedProfileService/red;
  English paraphrase remains passing. Baseline JSON was produced by the parent
  against 134cfcb; no case text or oracle is changed. This is not a full score.
- Public fingerprint test passes; Python compile, diff check and existing <=500-line
  check pass. No full suite, full 231 evaluation, holdout or external promotion.

Focused command:
PYTHONPATH=tests:. python -m unittest tests.test_load_topic_expansion tests.test_data_topic_expansion tests.test_locate_intent_expansion tests.test_query_language tests.test_query_language_exclusions tests.test_query_result_alternative tests.test_weak_log_owner_admission tests.test_source_operation_contract -v
