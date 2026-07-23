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

## Cost Attribution And Efficiency Gate

The next stage keeps the v4 diagnosis policy frozen and separates quality from
cost. The Codex Runner now extracts aggregate input, cached input, uncached
input, output, and reasoning Token counts from JSONL usage events. It also
counts completed commands, source-read commands, command-output bytes,
source-read-output bytes, and non-zero command exits. It never persists command
output, source text, or private reasoning.

`quality_gate` retains the v4 outcome and evidence semantics. The independent
`efficiency_gate` requires complete cost attribution, at most 10% Memory Token
overhead, at most 15% elapsed-time overhead, and non-regressing source-search
count. `promotion_gate` requires both gates. CI can enforce the efficiency gate
with `--fail-on-efficiency-fail` without changing `--fail-on-fail` compatibility.

Rescoring the immutable v4 pack produces `quality_gate=pass`,
`efficiency_gate=fail`, and `promotion_gate=fail`. Its measured Token overhead
is 18.11%, elapsed overhead is 26.38%, and source-search non-regression passes.
Cost-attribution coverage is zero because the pack predates the new aggregate
fields.

The authorized attribution run then completed another 18 external calls with
the same frozen cases, revisions, model, reasoning effort, sandbox, and v4
policy. All observations reported the full cost schema and all source-search
counts came from Runner telemetry.

| Metric | Baseline | V4 Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 0.9333 | 1.0 | +0.0667 |
| Root-cause accuracy | 1.0 | 1.0 | 0 |
| Expected-file recall | 0.8889 | 1.0 | +0.1111 |
| Predicted-file precision | 0.8889 | 1.0 | +0.1111 |
| Source searches | 2.1111 | 1.0 | -1.1111 |
| Model input tokens | 88,206 | 144,931 | +64.31% |
| Cached input tokens | 60,373 | 119,054 | +97.20% |
| Uncached input tokens | 27,832 | 25,877 | -7.03% |
| Model output tokens | 1,543 | 1,748 | +13.28% |
| Reasoning output tokens | 199 | 380 | +90.58% |
| Commands | 8.8889 | 9.5556 | +7.50% |
| Command output bytes | 66,625 | 48,714 | -26.88% |
| Source reads | 8.2222 | 7.2222 | -12.16% |
| Source-read amplification | 2.0556 | 1.7568 | -0.2988 |
| Source-read output bytes | 31,818 | 40,019 | +25.77% |
| Non-zero command exits | 0 | 1.5555 | +1.5555 |
| Agent elapsed time | 54,553 ms | 69,668 ms | +27.71% |

The quality gate passed, while the efficiency and promotion gates failed.
Raw cumulative model tokens increased by 63.43%, above the 10% limit, and
elapsed time increased by 27.71%, above the 15% limit. The 502.7-token Memory
payload is not the direct size driver: Memory used fewer uncached input tokens,
fewer source-searches, fewer source-read commands, and fewer command-output
bytes. The increase is dominated by cached input replay and higher reasoning
output, which indicates longer interaction paths after useful anchors were
already available.

The split-view navigation case is the primary hotspot: Memory cached input
increased 139.0%, commands increased 29.63%, and elapsed time increased 49.66%,
despite uncached input falling 23.66%. Login was effectively elapsed-neutral
and used 32.14% fewer source reads. One Baseline WebM trial returned a root
cause without opening source, lowering its file and causal scores and making
the aggregate overhead look worse; excluding that paired trial still leaves
52.00% model-input and 20.56% elapsed overhead, so the failure is not explained
by the outlier.

In this v4 artifact, `tool_error_count` means any non-zero command exit. It cannot
distinguish an expected no-match search from a real tool failure because raw
commands and outputs are deliberately not persisted. Treat the 1.5555 Memory
average as a review signal, not a proven runtime defect.

The next optimization target is therefore the Agent interaction protocol:
reduce post-anchor turns, stop after the first sufficient mechanism, and avoid
re-reading broad source ranges. Do not shrink the already-small Memory payload
or weaken the quality contract first. A future efficiency model should also
report cumulative and pricing-weighted cached tokens separately instead of
calling raw cumulative tokens monetary cost.

## V5 Sufficient-Evidence Candidate

The local candidate policy is now `anchor_first_sufficient_evidence_v5`. It
keeps the v4 ranking, category precedence, evidence gate, Oracle, and global
search/file limits, but replaces the repeated Memory instructions with one
versioned `TRIAGE -> GAP -> VERIFY -> STOP` loop:

- inspect the highest-ranked primary anchor first instead of opening every
  anchor by default;
- name one unresolved evidence gap before each expansion;
- use one bounded source read per file, with at most 180 relevant lines around
  the anchor;
- inspect at most one supporting boundary when it is required for the causal
  link or task constraint;
- stop all source search and reading immediately after a causal/repair-owner
  file provides sufficient direct mechanism evidence.

The prompt protocol moved into `examples/codex_benchmark_prompt.py`, leaving the
Runner as the execution facade. The fixed Memory protocol is eight lines and
1,592 characters in the minimal fixture, down from 15 lines and 1,848
characters. This static reduction is secondary; the main hypothesis is fewer
post-anchor tool turns and therefore less cached-input replay.

Telemetry now separates expected `rg/grep` exit-code-1 misses into
`source_search_miss_count`; `tool_error_count` retains other non-zero exits.
Efficiency output also reports Baseline and Memory source-read amplification.
Historical v4 and new v5 Codex samples both continue to require Runner-derived
search counts during offline rescoring.

The authorized v5 external gate completed the same 18-call Gramony matrix. All
three cases and all Memory trials produced the expected category, causal level,
and repair-owner files, but the quality gate failed because two observations
violated the source-search budget. Efficiency also narrowly failed.

| Metric | Baseline | V5 Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 1.0 | 1.0 | 0 |
| Root-cause accuracy | 1.0 | 1.0 | 0 |
| Expected-file recall | 1.0 | 1.0 | 0 |
| Predicted-file precision | 1.0 | 1.0 | 0 |
| Source searches | 2.5555 | 2.4445 | -0.1110 |
| Model tokens | 115,107 | 127,296 | +10.59% |
| Cached input tokens | 84,452 | 101,191 | +19.82% |
| Uncached input tokens | 28,967 | 24,540 | -15.28% |
| Commands | 9.4444 | 8.0 | -15.29% |
| Command output bytes | 77,919 | 31,777 | -59.22% |
| Source reads | 7.7778 | 4.7778 | -38.57% |
| Source-read output bytes | 32,277 | 18,397 | -43.00% |
| Source-read amplification | 2.0 | 1.5926 | -0.4074 |
| Agent elapsed time | 56,967 ms | 67,376 ms | +18.27% |

Token overhead missed the 10% limit by 0.59 percentage points and elapsed
overhead missed the 15% limit by 3.27 points. Compared with the separate v4
Memory batch, v5 reduced model tokens 13.21%, commands 16.28%, source reads
33.85%, source-read output 54.03%, and inspected files 27.03%. This cross-batch
comparison is directional only; the same-batch gate remains authoritative.

Navigation trial 2 used four source searches and WebM trial 1 used five, against
the limit of three. The other seven Memory observations passed the exploration
contract. V5 compressed away the explicit pre-command search ledger used by
v4; the hard limit remained visible, but two Agents did not apply it before
compound searches. Read discipline also remained imperfect, especially in the
WebM trials. `source_search_miss_count` was reported on all observations and
was zero; the remaining non-zero exits are therefore real search/read/other
command failures, not `rg/grep` exit-code-1 misses.

V5 is not promotable. The next candidate must restore concise SEARCH and READ
ledgers before every command while keeping the sufficient-evidence stop rule.
The gate limits must not be relaxed to make this batch pass.

## V6 Ledgered-Stop Candidate

The local follow-up is `anchor_first_ledgered_stop_v6`. It preserves the v5
evidence loop and all limits, while restoring an explicit pre-command ledger:

- update `searches_used` and `read_paths` before every command;
- count each `rg/grep/egrep/fgrep/find/fd` occurrence, including pipelines and
  compound commands, and refuse the command before the cumulative limit is
  exceeded;
- read known anchor paths directly instead of searching for them;
- count each `cat/sed/head/tail/nl/bat` path and never read one path twice;
- keep the one-file/180-line read and sufficient-evidence stop rules.

V6 makes the read rule auditable for current Codex observations:
`source_read_count > source_file_count` now fails the exploration gate when the
v6 Runner reports complete cost telemetry. Historical v4/v5 observations retain
their original gate semantics. Search telemetry remains mandatory for v4, v5,
and v6.

Non-zero exits are now split into search-command, source-read-command, and
other-command counts, in addition to the existing no-match count and total.
These fields identify the command family only; they do not persist the command
or infer why it failed.

The minimal v6 Memory protocol remains eight lines and 1,750 characters. It is
longer than v5's over-compressed 1,592 characters but shorter than v4's 1,848,
and restores the instruction whose removal caused the v5 search regressions.
The authorized v6 external A/B completed the same 18-call matrix. The search
ledger worked, but the read ledger and overall gates did not.

| Metric | Baseline | V6 Memory | Delta |
|---|---:|---:|---:|
| Agent outcome score | 0.9333 | 0.9333 | 0 |
| Root-cause accuracy | 1.0 | 1.0 | 0 |
| Expected-file recall | 0.8889 | 0.8889 | 0 |
| Predicted-file precision | 0.8889 | 0.8889 | 0 |
| Source searches | 2.0 | 0.8889 | -55.56% |
| Model tokens | 97,855 | 121,970 | +24.64% |
| Cached input tokens | 71,552 | 102,116 | +42.72% |
| Uncached input tokens | 24,757 | 18,134 | -26.75% |
| Commands | 7.7778 | 6.4444 | -17.14% |
| Command output bytes | 62,774 | 28,225 | -55.04% |
| Source reads | 8.7778 | 4.0 | -54.43% |
| Source-read output bytes | 30,724 | 20,140 | -34.45% |
| Source-read amplification | 2.5484 | 1.5 | -1.0484 |
| Agent elapsed time | 56,163 ms | 67,576 ms | +20.32% |

Every Memory observation stayed within the three-search limit. Compared
directionally with v5 Memory, v6 reduced searches 63.64%, commands 19.45%,
source reads 16.28%, and model tokens 4.18%; elapsed time was effectively flat.
The stronger prompt therefore fixed the targeted search regression.

V6 still failed quality. Navigation trials 1 and 2 read `4/3` and `6/3`
times/files; WebM trials 2 and 3 read `7/2` and `5/2`. Login trial 2 omitted one
opened expansion file from its trace. Login trial 1 opened no source and
returned uncertainty, scoring 0.4; with no command events its zero search count
also fell back to Agent-reported telemetry. The latter is a Runner telemetry
edge case, not evidence that a search occurred.

Error-family telemetry was complete. Memory averaged 1.6667 non-zero exits,
all classified as `other_tool_error_count`; search misses, search errors, and
source-read errors were zero. The aggregate fields cannot identify the exact
other command without violating the no-command-content privacy rule.

V6 also failed efficiency: Token overhead was 24.64% and elapsed overhead was
20.32%. It is not promotable. The next design should retain the successful hard
search ledger, fix zero-command Runner telemetry, and reconsider whether an
exact one-read-per-file rule belongs in the quality gate. Read amplification
can remain measured and bounded through efficiency without rewriting this v6
result.

The exact pre-, post-optimization, file-role-refinement, v2, v3, and v4 structured
responses are stored in
`docs/eval/gramony-three-trial-responses.json` and
`docs/eval/gramony-post-optimization-responses.json`, and
`docs/eval/gramony-file-role-refinement-responses.json`, and
`docs/eval/gramony-v2-refinement-responses.json`, and
`docs/eval/gramony-v3-refinement-responses.json`, and
`docs/eval/gramony-v4-refinement-responses.json`, and
`docs/eval/gramony-v4-cost-attribution-responses.json`, and
`docs/eval/gramony-v5-sufficient-evidence-responses.json`, and
`docs/eval/gramony-v6-ledgered-stop-responses.json`. They contain no private
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

## V7 Search-Ledger Candidate

The v6 run showed that the hard search ledger is effective, but its one-read-per-file
quality rule conflated evidence quality with interaction efficiency. V7 therefore keeps
the audited three-search ceiling and gap-driven expansion unchanged while replacing the
read ledger with a bounded read plan: one 180-line window per file, plus one additional
window only for a named unresolved evidence gap.

Repeated reads no longer fail `quality_gate` under v7. They are measured by
`average_source_read_count / average_source_file_count`; `efficiency_gate` requires the
Memory value to be at most 2.0 and no higher than Baseline. A complete tool-less Codex
turn is recorded as Runner-telemetry zero searches, fixing the v6 no-source attribution
ambiguity. The next action is the same three-case, three-trial external A/B; v7 is not a
promotion candidate until both quality and efficiency pass.

The repeated v7 run completed on 2026-07-18 with the same three cases, three
trials per variant, frozen revisions, `gpt-5.5`, low reasoning effort, and
isolated read-only Runner. The raw 18-observation pack is
`docs/eval/gramony-v7-search-ledger-responses.json`.

All Memory trials selected the expected root-cause category and repair-owner
files, producing 1.0 outcome, root-cause accuracy, file recall, file precision,
and per-case non-regression. All search counts came from Runner telemetry and
all observations reported complete cost fields. Quality nevertheless failed:
all three Login trials omitted opened files from `expansion_trace`; trial 2
also investigated four expanded files in one round against the two-file limit.

Efficiency also failed. Memory Token overhead was 16.41% and elapsed overhead
was 23.10%. Source searches fell from 2.6667 to 1.0, source reads from 6.2222
to 4.8889, command output by 67.70%, and read output by 14.07%. Aggregate read
amplification improved from 1.6470 to 1.4667 and passed both v7 read checks.
However, the WebM Memory case alone reached 2.8333 reads per file, while
navigation was 1.3333 and login was 1.0. Aggregate read efficiency therefore
masked a case-level hotspot.

Compared directionally with v6 Memory, v7 restored perfect quality scores and
reduced elapsed time 2.81%, but increased model tokens 15.66%, commands 27.59%,
searches 12.50%, and source reads 22.22%. V7 is not promotable. The next policy
must make expansion accounting deterministic and add per-case efficiency
non-regression before another external run.

## V8 Deterministic Expansion Candidate

V8 keeps the v7 search ledger and bounded read plan, but changes ownership of
expansion accounting. The Agent reports every opened path in
`investigated_files` and gives a gap reason plus representative files in
`expansion_trace`. The Runner derives `expansion_file_count` from investigated
files minus primary anchors and derives the minimum number of two-file rounds.
Only v8 observations carrying `expansion_accounting_source=runner_investigated_files`
use this audit; v4-v7 artifacts retain their historical trace rules.

The efficiency gate now applies Token overhead, elapsed overhead, source-search
non-regression, the 2.0 read-amplification ceiling, and read-amplification
non-regression to every case as well as the aggregate. The result includes a
compact `per_case` efficiency section, while `maintain-health` exposes failed
case count and IDs. This directly detects the v7 Login Token/time hotspot and
WebM read-amplification hotspot that its aggregate checks masked.

Local prompt size is 1,816 characters across eight Memory-protocol lines.
Focused regression and v4-v7 offline replay pass: historical quality and
promotion outcomes are unchanged, while the new per-case checks explain the
existing efficiency failures. V8 remains pending the same repeated external
A/B and does not change retrieval ranking, Oracle data, or SQLite storage.

## V8 Core Context Development Checks

The next work changed the actual query context rather than another gate. Exact
query/path-segment identity now outranks generic symbol overlap, bounded wiki
results keep at most two records per file before backfill, resource references
rank below source-locatable declarations, and long exact identifier terms add
a small language-neutral signal. Compact code anchors group records by file,
retain source ranges, and omit redundant containment edges.

On the frozen source, Login changed from two unrelated anchors to the Password,
PhoneNumber, and VerifyCode pages with declaration ranges. WebM ranks
`Message.ets / StickerInfo` and `MessageBubble.ets / StickerOnlyView` first;
the latter also carries the `StickerView` range. Estimated compact sizes are
592 and 569 Tokens, below the 1,500-Token budget.

A two-case, one-trial development A/B used four external calls. Login Memory
read three files once each, performed no search, and used about half the Token
count of its Baseline while preserving a 1.0 outcome. WebM Memory corrected a
tool-less Baseline miss and selected `MessageBubble.ets`, but read seven times
across two files. The raw pack is
`docs/eval/gramony-v8-core-context-responses.json`. This is directional evidence,
not a promotion run.

Compact anchors now also derive one `read_window` when all source ranges fit
within 180 lines. The Runner asks the Agent to read that window once and treat
individual ranges as targets rather than separate reads. The frozen WebM
window is lines 446-586. A one-case paired check retained perfect diagnosis,
reduced Token use by 21.6% against that run's Baseline, but still made six
reads across two files. Its raw pack is
`docs/eval/gramony-v8-read-window-responses.json`.

The remaining WebM issue is therefore not anchor recall or gate accounting.
Prompt-only read guidance is insufficient. The next architecture stage should
evaluate budgeted, current-revision source excerpts returned by the query
runtime, with excerpt bytes included in context cost and no persisted source
body. It must be tested separately before the repeated 18-call promotion A/B.

## Budgeted Current-Source Excerpts

The local query runtime now implements that stage without a new public command.
`context --compact` reads at most two primary anchors, at most two ranges per
anchor, and at most 40 lines per range. A dynamic character allowance reserves
space inside the existing 1,500-Token payload budget. Paths are resolved under
the current project root; absolute paths, traversal, missing files, and symlinks
outside the root produce no excerpt. SQLite and the code index remain unchanged.

The frozen WebM context is approximately 1,216 Tokens. It includes the current
`StickerInfo` declaration, `StickerOnlyView` delegation, and the beginning of
`StickerView` through the concrete
`loadData(this.videoBase64, 'audio/webm', 'base64')` mechanism. Frozen Login is
approximately 1,244 Tokens and retains all three Login anchors while attaching
bounded source only where the remaining global budget permits.

Excerpt bodies exist only in the command response. `runtime/last_context.json`
replaces them with symbol, line, source, and truncation metadata. The Agent
contract treats current-worktree excerpts as already-read source and forbids
rereading those lines without a named gap.

A new external A/B was not run. The attempted WebM pair was rejected because
the prompt would transmit current source bodies to an external model. No
workaround or result artifact was produced. Future behavioral validation must
use a trusted local Runner or an explicitly approved source-disclosure path;
local payload, privacy, ranking, and regression checks remain valid meanwhile.

The bundled Codex Runner now closes that transmission path. It redacts every
excerpt body after the isolated query and before prompt construction, retains
only source-range metadata, and reports
`source_excerpt_delivery=external_metadata_only`. An end-to-end fake-Codex
regression fails if a unique source marker reaches stdin. Existing external A/B
can therefore continue safely, but it measures anchors and ranges only. Full
source-excerpt behavior remains a trusted-local-Runner test and no local model
CLI was detected on this machine.

## Trusted Local Runner Readiness

The repository now includes a loopback-only Ollama Runner for the deferred
full-excerpt comparison. It verifies the requested installed model, uses native
Ollama tool calls, exposes only bounded workspace source reads and literal
searches, and derives investigated files, tool costs, and Token totals from the
Runner. Compact excerpt bodies stay in the local process/model boundary and are
not copied into response packs or runtime history.

A fake loopback Ollama service validates the complete Memory prompt, tool loop,
structured final response, telemetry, missing-model rejection, and external-host
rejection. Path traversal, external file symlinks, search limits, read limits,
and literal matching have separate tests. This is protocol and privacy evidence,
not an Agent-quality result.

## Trusted Local Model Smoke Results

Ollama `0.32.1` was installed on an Intel six-core, 16-GB host. Generation is
bounded to 256 Tokens for tool turns and 512 for the final JSON response, with
thinking disabled at the API boundary. Four local model tags were evaluated:

| Model | Digest | Tool probe | Decision |
|---|---|---|---|
| `qwen3:8b` | `500a1f067a9f` | Timed out after 300 seconds at about 19 generated Tokens | Too slow |
| `qwen3:4b` | `359d7dd4bcda` | Repeated task narration; no tool call within 256 Tokens | Incompatible |
| `qwen3:1.7b` | `8f68893c685c` | Valid native tool call in 7.6 seconds | Protocol only |
| `llama3.2:3b` | `a80c4f17acd5` | Valid native tool call in 12.3 seconds | A/B candidate |

Both viable models then ran the frozen Login case once per variant:

| Model | Baseline score | Memory score | Baseline/Memory Tokens | Baseline/Memory elapsed | Result |
|---|---:|---:|---:|---:|---|
| `qwen3:1.7b` | 0.5000 | 0.3667 | 2,773 / 19,697 | 26,075 / 144,155 ms | Quality and efficiency fail |
| `llama3.2:3b` | 0.4000 | 0.0000 | 3,061 / 8,443 | 75,007 / 199,850 ms | Quality and efficiency fail |

The Qwen Memory run received two correct Login source excerpts but searched the
literal phrase `repeated taps`, used all three searches without a match, and
misclassified the async duplicate-submit defect. The Llama Memory run also
received two correct anchors, made one no-match search, and returned the schema
placeholder category. Its Baseline invented JavaScript file names without
reading source. These failures demonstrate model planning/calibration limits;
they do not show a retrieval-ranking failure.

The privacy-safe raw packs are
`docs/eval/gramony-ollama-qwen3-1.7b-smoke-responses.json` and
`docs/eval/gramony-ollama-llama3.2-3b-smoke-responses.json`. The Llama pack was
captured before a telemetry correction and therefore counts model-claimed
fictional files in Baseline `source_file_count`; future local runs derive that
metric only from actual source reads and delivered excerpts. The failed smoke
gate stops the planned 18-call matrix. A stronger tool-calling local model or
more capable hardware is required before full-excerpt quality promotion testing.
The unusable 8B and 4B model blobs were removed after recording their digests;
only the 1.7B protocol fixture and 3B smoke candidate remain locally.

## System Context Capability Gate

The next stage stopped treating local-model compatibility as the primary test.
A model-free `eval-context-capability` gate now rebuilds each frozen revision and
scores only context supply against the hidden Oracle.

Its first three-case run failed split-view navigation: the full query found
`ChatList.ets` through an exact log-emitter function identity, but compacting
removed every log emitter because no causal log path was activated. Generic
`chat` matches then occupied all primary anchors. The fix preserves weak-log
suppression while allowing one score-qualified exact code identity into the
primary anchor set and deriving a source range from the log line.

The repeated run passed all three cases with 1.0 code-anchor and primary-anchor
recall, 0.8889 source-excerpt recall, 1,215.3333 average context Tokens, 1,284.3333
ms average isolated-index preparation, and 287 ms average query time. Log graph,
experience, and causal-path quality remain informational because these cold
source cases have no reviewed Oracle for those capabilities. This result permits
an Agent A/B; it does not override the failed small-model smoke results or claim
that a local Agent can diagnose the cases.
