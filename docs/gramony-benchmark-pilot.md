# Gramony Real-Repository Benchmark Pilot

## Purpose

Use a real ArkTS application to test whether Agent Memory improves an external
Agent CLI's diagnosis quality, file recall, query cost, and unsupported-direction
rate. This pilot evaluates context supply. It does not claim that the Runtime
diagnoses incidents.

Repository:

- <https://github.com/Gramony/Gramony>
- reviewed branch: `dev`
- reviewed head: `0a1ee4b026b6736671f0030ba9859aceaa962298`
- license: Apache-2.0

The reviewed repository has 74 commits and 73 `.ets` files. Its history includes
profile loading, message startup, split navigation, responsive layout, login
request state, sticker persistence, local media access, and chat state fixes.

## Current Artifact

`docs/eval/gramony-history-cases.json` contains ten reviewed records: nine
development drafts and one rejected case.

Exploratory execution results are recorded in
`docs/eval/gramony-pilot-results.json`.

Every case is:

- derived from a non-merge Git change;
- inspected against the before/after source diff;
- rewritten as a symptom rather than a commit-message prompt;
- frozen at the parent revision;
- protected by the existing public-case projection;
- still marked `draft`.

The profile-loading record was rejected after the first real Agent A/B run.
Both Agents found `ProfilePage.ets`, but they also identified navigation and
`Me.ets` async state as plausible causal inputs. The historical fix only changes
an error branch into a loading branch, so the original source-only oracle was
too narrow and did not prove root-cause resolution.

`source_diff_reviewed` is not equivalent to runtime validation. Gramony does not
ship focused tests for these fixes, and several cases require a HarmonyOS device,
ArkWeb, responsive viewport, Telegram account, or native library.

## Case Selection

Selected:

| Case | Main signal | Remaining validation |
|---|---|---|
| new messages not loaded | startup lifecycle | logged-in startup |
| split-view chat navigation | route stack behavior | SM and wide-screen navigation |
| responsive breakpoints | layout ownership | SM/MD/LG/XL screenshots |
| login duplicate submit | pending async state | repeated taps |
| sticker extension resolution | persisted media metadata | WebP/TGS/WebM replay |
| chat avatar layout | stable row geometry | loading/failure avatar states |
| WebM local file access | ArkWeb file boundary | on-device render |
| new chat title | fallback state source | sender absent from chat list |
| reply preview width | constrained layout | narrow/wide preview |

Rejected after execution:

| Case | Reason |
|---|---|
| profile loading state | fix is a presentation workaround and the causal file set is wider than the original oracle |

## Execution Results

Two one-case A/B runs were executed with `codex-cli 0.142.0`.

The first run rejected the profile-loading oracle rather than treating a failed
gate as a retrieval regression.

The second run used `gramony-new-messages-not-loaded`:

| Metric | Baseline | Memory |
|---|---:|---:|
| Agent outcome score | 1.0 | 1.0 |
| Expected file | `Index.ets` | `Index.ets` |
| Root-cause category | lifecycle | lifecycle |
| Reported query rounds | 4 | 1 |
| Token usage | 242,113 | 230,525 |
| Agent elapsed time | 101,441 ms | 86,810 ms |

This pair passed with equal diagnosis quality, 11,588 fewer tokens, and 14,631
ms lower Agent elapsed time for the Memory variant. It is only one development
pair. The model was not pinned and the project lacks a runtime verification
test, so this is evidence that the A/B loop works, not evidence of general
Memory uplift.

A reproducible run then selected three cases explicitly and pinned:

- `codex-cli 0.142.0`
- `gpt-5.5`
- reasoning effort `low`
- read-only, ephemeral sessions
- isolated temporary `HOME` and `CODEX_HOME`
- Runner-preloaded Memory context

| Metric | Baseline | Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 0.8667 | 1.0 | +0.1333 |
| Root-cause accuracy | 0.6667 | 1.0 | +0.3333 |
| Expected-file recall | 1.0 | 1.0 | 0 |
| Query rounds | 2.6667 | 1.0 | -1.6667 |
| Token usage | 71,424 | 137,848 | +66,424 |
| Agent elapsed time | 41,626 ms | 47,264 ms | +5,638 ms |

The cases covered split-view chat navigation, duplicate login submission, and
local WebM access. Memory improved category consistency and reduced
investigation rounds, but more than doubled average token usage. Compact
context selection is therefore the next optimization target.

The diagnosis benchmark originally called full `context`, unlike the normal L1
Agent workflow. It now calls `context --compact`. A local frozen-revision
measurement, without invoking an external model, produced:

| Case | Full bytes | Compact bytes | Estimated tokens | Reduction |
|---|---:|---:|---:|---:|
| split-view navigation | 51,544 | 1,775 | 444 | 96.56% |
| duplicate login submit | 51,576 | 1,656 | 414 | 96.79% |
| WebM local access | 45,664 | 2,031 | 508 | 95.55% |

The table uses the compact UTF-8 JSON serialization injected by the Runner,
rather than CLI pretty-printed output. All three payloads fit the 1,500-token
compact budget with substantial headroom. Weak log matches are suppressed when
there is no strong log identity, code anchors are deduplicated by file,
generated summaries are omitted when they repeat path and symbol, and relation
hints must connect to a returned anchor. Missing evidence is reported as a gap
instead of being replaced with low-relevance context. The benchmark records
`memory_context_bytes` and `memory_context_token_estimate`, and fails its quality
gate when a reporting Runner exceeds that budget. The external Agent quality
rerun and the repeated-trial stability run were completed after explicit
approval to send the frozen project context to the configured model service.

## Compact External A/B

After explicit approval, the same three frozen cases were rerun with the compact
context and pinned isolated configuration.

| Metric | Baseline | Compact Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 0.8667 | 0.8667 | 0 |
| Root-cause accuracy | 0.6667 | 0.6667 | 0 |
| Query rounds | 2.3333 | 0.6667 | -1.6666 |
| Total model tokens | 79,917 | 114,390 | +34,473 |
| Memory context tokens | 0 | 455 | +455 |
| Agent elapsed time | 45,909 ms | 65,326 ms | +19,417 ms |

The aggregate score was unchanged, but the run failed the corrected quality
gate because one case regressed:

- split-view navigation: `+0.4`
- duplicate login submit: `0`
- WebM local access: `-0.4`

The WebM Memory response still identified `MessageBubble.ets`, Base64 loading,
`audio/webm`, and the ArkWeb local-resource boundary. It selected the category
`resource` instead of the frozen `media` oracle. The Oracle was not changed
after seeing the result.

This exposed a gate defect: aggregate improvement could previously offset an
individual regression. `every_case_outcome_non_regression` is now mandatory.
The run also shows that a 455-token Memory payload does not directly account for
the 34,473 additional total tokens. The remaining difference comes from Agent
tool interaction, model-run variance, or both, rather than serialization size
alone.

## Three-Trial External A/B

The same three cases were then run for three independently paired trials, for
18 total external Agent calls. The model, reasoning effort, sandbox, isolated
user context, compact Memory payload, and Runner policy remained fixed.

| Metric | Baseline | Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 0.8667 | 1.0 | +0.1333 |
| Root-cause accuracy | 0.6667 | 1.0 | +0.3333 |
| Expected-file recall | 1.0 | 1.0 | 0 |
| Query rounds | 2.4444 | 0.5556 | -1.8888 |
| Total model tokens | 91,593 | 142,577 | +50,983 |
| Agent elapsed time | 42,371 ms | 70,228 ms | +27,857 ms |
| Source files inspected | 3.2222 | 4.3333 | +1.1111 |
| Memory anchor hit rate | n/a | 0.6815 | n/a |

All quality and stability gates passed:

- all 18 observations were present with no duplicates;
- every case had a `1.0` trial non-regression rate;
- every Memory root-cause and predicted-file consistency rate was `1.0`;
- split-view navigation improved by `+0.4` in all three trials;
- duplicate login submission was equal in all three trials;
- WebM local access was equal in all three trials and selected `media` every
  time, showing the earlier `resource` response was a single-run variation;
- all Memory contexts remained within the 1,500-token budget.

The stable quality improvement does not establish efficiency. Memory inspected
more source files and used substantially more total model tokens despite fewer
reported query rounds. The next optimization target is Agent source expansion
and stopping behavior after the returned anchors have established a scoped
cause, not further payload compression.

The Runtime and bundled Runner now implement `anchor_first_gap_driven_v1` for
that target: primary and expansion anchor roles, named evidence-gap reasons,
bounded expansion rounds/files/searches, minimum sufficient evidence, explicit
stop reasons, and a benchmark budget gate. The result above remains the
pre-optimization baseline.

## Post-Optimization Three-Trial A/B

The same fixed three-case, three-trial configuration was rerun after adding
`anchor_first_gap_driven_v1`. All quality, stability, context-budget, and source
exploration gates passed.

| Memory metric | Before | After | Change |
|---|---:|---:|---:|
| Agent outcome score | 1.0 | 0.9833 | -0.0167 |
| Root-cause accuracy | 1.0 | 1.0 | 0 |
| Expected-file recall | 1.0 | 1.0 | 0 |
| Predicted-file precision | 1.0 | 0.8889 | -0.1111 |
| Query rounds | 0.5556 | 1.0 | +0.4444 |
| Total model tokens | 142,577 | 139,854 | -2,722 |
| Agent elapsed time | 70,228 ms | 67,940 ms | -2,287 ms |
| Source files inspected | 4.3333 | 4.0 | -0.3333 |
| Memory context tokens | 455 | 650 | +195 |
| Memory anchor hit rate | 0.6815 | 0.6722 | -0.0093 |

The new controls produced a small cost reduction: about 1.9% fewer model
tokens, 3.3% lower Agent elapsed time, and 7.7% fewer inspected files. They did
not reach the original cost target. The static exploration contract also added
about 195 context tokens.

Quality remained above the same-batch Baseline and every case was non-regressing
in all three paired trials. However, split-view navigation predicted
`Index.ets` in addition to the expected `ChatList.ets` in two trials. That
reduced overall file precision and Memory outcome score. Root-cause accuracy,
expected-file recall, causal calibration, and forbidden-direction rate stayed
unchanged.

Memory averaged 1.4444 source searches, one expansion round, 2.6667 primary
anchor hits, 1.3333 non-anchor files, and always stopped with
`supported_cause_found`. The current conclusion is partial improvement with a
precision tradeoff, not a completed efficiency optimization. The next change
should make predicted-file reporting distinguish the causal owner from inspected
supporting callers, while reducing repeated static contract text.

That protocol refinement is now implemented locally. `predicted_files` is
reserved for causal or repair owners, `supporting_files` carries inspected
callers and corroborating boundaries, and both remain in `investigated_files`.
The compact exploration contract was reduced from about 175 estimated tokens
to 28 by retaining only the policy id and numeric limits. A new external A/B is
required before attributing any precision or total-token change to this
refinement.

A local frozen-revision measurement, without external model calls, produced
490, 456, and 564 context tokens for split-view navigation, login duplicate
submission, and WebM local access. The previous post-optimization payloads were
637, 603, and 710 tokens, so each case dropped by about 147 tokens. The new average is
about 503 tokens: 47.7 tokens above the original compact baseline but well below
the 1,500-token budget.

## File-Role Refinement External A/B

The refined protocol was then tested with the same three cases, three paired
trials, pinned model, and isolated Runner configuration. The run completed all
18 external Agent calls, but failed the quality gate.

| Metric | Baseline | Refined Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 0.9556 | 0.9000 | -0.0556 |
| Root-cause accuracy | 0.8889 | 0.8889 | 0 |
| Expected-file recall | 1.0 | 0.8889 | -0.1111 |
| Predicted-file precision | 1.0 | 0.8889 | -0.1111 |
| Query rounds | 2.4444 | 1.0 | -1.4444 |
| Total model tokens | 108,668 | 103,495 | -5,172 |
| Agent elapsed time | 54,223 ms | 62,003 ms | +7,780 ms |
| Source files inspected | 3.8889 | 4.0 | +0.1111 |
| Memory context tokens | 0 | 503 | +503 |
| Source searches | 2.4444 | 0.7778 | -1.6666 |

The file-role change worked on split-view navigation: `ChatList.ets` was the
only causal file and `Index.ets` moved to `supporting_files`, restoring that
case's predicted-file precision and consistency to `1.0`. Login duplicate
submission also remained fully stable.

WebM local access failed in one of three Memory trials. The failed trial chose
`ChatDetail.ets`, classified the problem as `resource`, and stopped with
`supported_cause_found` without inspecting `MessageBubble.ets`. The other two
Memory trials found `MessageBubble.ets` and scored `1.0`. Consequently, WebM
root-cause consistency, predicted-file consistency, and trial non-regression
were each `0.6667`.

A local reconstruction of the frozen Memory query explains the variation. Its
five returned anchors were generic chat components; `MessageBubble.ets` was not
present. Successful trials recovered through source search, while the failed
trial treated an expansion anchor as sufficient evidence. The quality gate
correctly rejected the batch through `context_agent_outcome_non_regression` and
`every_case_outcome_non_regression`. This is a retrieval-recall and stopping
precondition defect, not evidence that the file-role distinction regressed
causal reporting.

The next optimization must improve domain-token/code-owner anchor recall and
forbid `supported_cause_found` when the inspected source does not establish a
direct mechanism or repair owner. It should be evaluated as a new batch rather
than rewriting this failed result.

That follow-up is now implemented locally as `anchor_first_gap_driven_v2`.
Natural-language retrieval filters English stopwords and low-discrimination
code metawords, and FTS5 prefix recall maps domain words to compound symbols.
The Runner also requires `evidence_basis` and `mechanism_evidence_files`:
`supported_cause_found` passes its exploration gate only when a directly
inspected causal file contains the concrete mechanism. A likely owner must be
reported as `inference_only` with an uncertainty stop reason.

The same frozen WebM query now returns `Message.ets / StickerInfo` and
`MessageBubble.ets / StickerOnlyView` as its two primary anchors. Previously,
`MessageBubble.ets` was absent from all five anchors. The compact payload is
about 541 estimated tokens, still below the 1,500-token budget. This is a local
retrieval regression check, not an external quality result; a new three-trial
A/B is required before claiming that v2 resolves the stochastic failure.

## V2 Retrieval And Stop External A/B

The same pinned three-case, three-trial configuration then completed 18
external Agent calls with `anchor_first_gap_driven_v2`. The batch failed two
gates: `every_case_outcome_non_regression` and
`source_exploration_within_budget`.

| Metric | Baseline | V2 Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 0.9556 | 0.9556 | 0 |
| Root-cause accuracy | 0.8889 | 0.8889 | 0 |
| Expected-file recall | 1.0 | 1.0 | 0 |
| Predicted-file precision | 1.0 | 1.0 | 0 |
| Query rounds | 2.4445 | 1.0 | -1.4445 |
| Source searches | 2.2222 | 1.0 | -1.2222 |
| Total model tokens | 135,829 | 137,468 | +1,638 |
| Agent elapsed time | 56,246 ms | 65,838 ms | +9,592 ms |
| Source files inspected | 4.6667 | 4.0 | -0.6667 |
| Memory context tokens | 0 | 502.6667 | +502.6667 |

The targeted WebM defect was resolved across all three Memory trials. Every
trial selected `media` and `MessageBubble.ets`, used both returned primary
anchors, inspected only two files, and required no non-anchor expansion. Its
root-cause consistency, predicted-file consistency, and non-regression rate
were all `1.0`.

One login Memory trial selected `state` instead of the frozen `async` category,
although it identified the same three expected files and explicitly described
parallel async authentication calls caused by missing in-flight guards. That
trial scored 0.6 versus its 1.0 Baseline, so the per-case non-regression gate
correctly failed without changing the Oracle after execution.

The v2 exploration gate also exposed reporting violations. All navigation
Memory trials put supporting `Index.ets` in `mechanism_evidence_files` while
keeping it out of causal `predicted_files`. Login trials inspected three
non-anchor files, and one reported two expansion rounds with only one reason
code. WebM satisfied the complete v2 evidence and budget contract in all three
trials. The result is a real WebM retrieval improvement, but not a passing
release batch.

## V3 Exploration Audit Refinement

The follow-up protocol is implemented locally as
`anchor_first_gap_driven_v3`. It keeps the v2 retrieval ranking and changes the
Agent/Runner audit boundary:

- the Agent reports one `expansion_trace` item per round with one reason and up
  to two newly inspected files;
- the Runner derives `expansion_rounds` and `expansion_reason_codes` from that
  trace instead of trusting separate model counters;
- the budget allows up to two new files per round rather than two non-anchor
  files across the whole investigation;
- mechanism evidence may include an inspected supporting boundary, but must
  include at least one predicted causal or repair owner;
- category guidance assigns parallel in-flight requests, races, ordering, and
  duplicate async side effects to `async`, even when the missing guard is a
  state flag.

The frozen WebM query still returns `Message.ets / StickerInfo` and
`MessageBubble.ets / StickerOnlyView` as primary anchors with an estimated 541
context tokens. The saved v2 external pack retains its 0.9556 Memory score and
the same two failed gates when rescored; v3 does not rewrite the historical
observations. A separate repeated external A/B is required for v3 promotion.
The approved rerun and its non-promotion result are recorded below.

## V3 External A/B

The approved v3 run completed the same three cases with three Baseline and
three Memory trials per case, for 18 external Codex calls. The frozen Gramony
revision, model, reasoning effort, sandbox, and isolated-user configuration
were unchanged. The batch failed promotion.

| Metric | Baseline | V3 Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 0.9333 | 0.9111 | -0.0222 |
| Root-cause accuracy | 1.0 | 0.7778 | -0.2222 |
| Expected-file recall | 0.8889 | 1.0 | +0.1111 |
| Predicted-file precision | 0.8889 | 1.0 | +0.1111 |
| Query rounds | 2.3333 | 1.1111 | -1.2222 |
| Source searches | 2.3333 | 1.3333 | -1.0 |
| Average model tokens | 122,227 | 137,730 | +15,503 |
| Agent elapsed time | 55,211 ms | 65,745 ms | +10,534 ms |
| Source files inspected | 4.1111 | 4.2222 | +0.1111 |
| Memory context tokens | 0 | 502.6667 | +502.6667 |

Navigation remained stable: all six observations selected `route` and
`ChatList.ets`, and every Memory trial passed its exploration contract. Login
improved by 0.2 because all three Memory trials selected `async` and all three
expected login files; this resolves the v2 category error. Its third Memory
trial nevertheless inspected `Login/Index.ets` without recording that file in
`expansion_trace`, so the audit correctly rejected that observation.

WebM regressed in two Memory trials. All three still selected
`MessageBubble.ets` with perfect file precision and recall, but trials two and
three classified the local WebM loading failure as `api` rather than the frozen
`media` category. Trial two also performed four source searches against a
budget of three. The WebM case delta was -0.2667 and its per-trial
non-regression rate was 0.3333.

The run also exposed two evaluator inconsistencies. Repeated reason codes were
deduplicated after the Runner derived them from `expansion_trace`, and the
five-file global cap contradicted the declared two rounds of up to two new
files after three primary anchors. Validation now derives rounds and the full
reason sequence directly from the trace and permits at most seven total files.
Rescoring the immutable response pack still fails: the untraced login file,
WebM's fourth search, and WebM category regression are real observation-level
failures. The Runner now tells future Agents to use `media` for media loading,
decoding, playback, and local media-resource access even when the concrete
mechanism is API misuse; that change requires a new external batch before it
can be promoted.

## V4 Budget And Category Refinement

The next local policy is `anchor_first_gap_driven_v4`. It does not rewrite the
v3 response pack, change the frozen Oracle, or post-process an Agent category
into a passing value. It addresses the observed control failures before another
external batch:

- the Memory prompt renders the exact search, total-file, expansion-round, and
  files-per-round limits from `query_handoff.source_exploration`;
- the Agent must count `rg`, `grep`, `find`, and `fd` before executing another
  search, and stop uncertain when the next invocation would exceed budget;
- every opened source file must be reported, and each expansion/non-anchor file
  must appear exactly once in the trace round that first opened it;
- category precedence is explicit: async concurrency first, then the concrete
  failure domain, then low-level `api` or `state` details; WebM and local media
  loading remain `media` while API misuse stays in the summary;
- the Codex Runner derives search count from completed JSONL command telemetry
  and marks its source. A v4 Codex observation cannot pass the exploration gate
  with an Agent-reported search count.

The Runner still does not infer the root cause, repair missing trace entries, or
truncate actual exploration after execution. Those would hide Agent behavior
rather than improve it. Local protocol, Runner, compact-context, and benchmark
tests pass; a new repeated external A/B is still required to evaluate v4.
The approved result is recorded below.

## V4 External A/B

The approved v4 run completed 18 external calls with the same three cases,
three trials, pinned Gramony revision, `gpt-5.5`, low reasoning effort,
read-only sandbox, and isolated user context. Every quality, stability, context,
configuration, and exploration gate passed.

| Metric | Baseline | V4 Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 1.0 | 1.0 | 0 |
| Root-cause accuracy | 1.0 | 1.0 | 0 |
| Expected-file recall | 1.0 | 1.0 | 0 |
| Predicted-file precision | 1.0 | 1.0 | 0 |
| Query rounds | 2.2222 | 1.1111 | -1.1111 |
| Source searches | 2.8889 | 0.5556 | -2.3333 |
| Average model tokens | 116,996 | 138,183 | +21,187 |
| Agent elapsed time | 56,022 ms | 70,802 ms | +14,781 ms |
| Source files inspected | 3.5555 | 4.2222 | +0.6667 |
| Memory context tokens | 0 | 502.6667 | +502.6667 |

All three navigation Memory trials selected `route` and `ChatList.ets`; all
three login trials canonicalized to `async` and selected the three expected login pages; all
three WebM trials selected `media` and `MessageBubble.ets`. Every case had a
1.0 non-regression rate, root-cause consistency, and predicted-file
consistency. All 18 Baseline and Memory observations used
`source_search_count_source=runner_telemetry`. Every Memory trace passed the
v4 source-exploration contract.

The context reduced measured source-search invocations by about 80.8% and query
rounds by 50%, but it did not reduce total reasoning cost. Memory used about
18.1% more model tokens, took 26.4% longer, and inspected 0.67 more files than
its same-batch Baseline. Compared with the v3 Memory batch, v4 restored outcome
score from 0.9111 to 1.0 and root-cause accuracy from 0.7778 to 1.0 while adding
about 0.3% model tokens and 7.7% elapsed time. Search-count comparisons with v3
are invalid because v3 used Agent-reported counts.

V4 therefore passes this three-case development gate and is the current
candidate policy. It does not establish general uplift or Holdout readiness;
the remaining priority is reducing model-token and elapsed-time overhead
without weakening the now-stable quality and audit behavior.

The exact pre-, post-optimization, file-role-refinement, v2, v3, and v4 structured
responses are stored in
`docs/eval/gramony-three-trial-responses.json` and
`docs/eval/gramony-post-optimization-responses.json`, and
`docs/eval/gramony-file-role-refinement-responses.json`, and
`docs/eval/gramony-v2-refinement-responses.json`, and
`docs/eval/gramony-v3-refinement-responses.json`, and
`docs/eval/gramony-v4-refinement-responses.json`. They contain no private
reasoning or source bodies and can be rescored without another external call.

Two intermediate runs were excluded: one attempted SQLite access inside the
read-only Agent sandbox, and one inherited user Skills. The Runner now executes
the isolated Memory query before Codex starts, fails the sample if that query
fails, and uses a temporary user home containing only authentication and model
cache files.

Source-only diagnosis cannot prove runtime behavior. The bundled Runner caps
`verified` causality to `supported` and records verification as `unknown`.

Rejected from the first automatic harvest:

- `fix: chore`, `fix: warnings`, and broad cleanup changes: no stable symptom.
- pure i18n and resource-only changes: weak diagnosis value for the first suite.
- `mediaLoaded failed`: the fix explicitly says it is a temporary workaround.
- `a bit of db issues`: multiple unrelated edits and no precise symptom.
- large resource/theme changes: too broad for deterministic file scoring.
- refactors: defer until the design benchmark has a reviewed design oracle.

## Reproduce The Pack

```bash
git clone https://github.com/Gramony/Gramony.git /tmp/gramony

python tools/agent_memory.py eval-harvest-history \
  --project . \
  --source /tmp/gramony \
  --target /tmp/gramony-history-drafts.json \
  --scan-limit 100 \
  --limit 30 \
  --json
```

The generated pack is an input to review, not the checked-in curated artifact.

## Run A Development A/B

The repository includes a generic Codex CLI Runner:

```bash
chmod +x examples/codex-agent-benchmark-runner.py
```

It runs Codex in read-only, non-interactive, ephemeral mode, enforces a JSON
output schema, and uses the same CLI configuration for both variants. Override
the model explicitly when repeatability requires it:

```bash
export AGENT_BENCHMARK_CODEX_MODEL="<model>"
export AGENT_BENCHMARK_CODEX_REASONING_EFFORT="low"
```

Run exact reviewed cases:

```bash
python tools/agent_memory.py eval-agent-benchmark \
  --project . \
  --cases docs/eval/gramony-history-cases.json \
  --source /tmp/gramony \
  --runner examples/codex-agent-benchmark-runner.py \
  --allow-drafts \
  --case-id gramony-split-view-chat-navigation \
  --case-id gramony-login-duplicate-submit \
  --case-id gramony-webm-local-file-access \
  --output-responses /tmp/gramony-pilot-responses.json \
  --json
```

Start with two cases. Do not run all ten until the Runner proves:

- it cannot read Git history or hidden oracle fields;
- it uses the frozen workspace supplied in the request;
- the Memory variant uses only the supplied isolated memory command;
- it emits no private reasoning fields;
- both variants use the same model, permissions, timeout, and prompt contract.

For any result used as a release gate, set `AGENT_BENCHMARK_CODEX_MODEL`
explicitly and record it with the result.

## Promotion Gate

A case may move from `draft` to `validated` only after:

1. the symptom is reproduced independently on the before revision;
2. the expected files and root-cause category are confirmed;
3. a runnable or observable verification path exists;
4. unrelated changed files are removed from the oracle;
5. forbidden directions are added when defensible;
6. the public task does not disclose the fix;
7. the case is not duplicated through the Homogram/Gramony fork relationship.

Only independently reserved validated cases may become Holdout.
