# Builder producer reconstruction

New Development execution from published 6371d430. Prior unpublished implementation and artifacts were lost in environment recovery. This protocol reconstructs the retained supported declarations and controls; historical test counts are not evidence for this run. Tests are frozen before implementation. Positive syntax metadata only, no consumer/ranking or absence certification. Existing public Builder diagnosis in docs/eval/builder-role-current remains the consumer red; no claim of solving it.

Replay harness correction: first execution stopped at init because init does not support --json. No learn/context result existed; removed that flag before retry. Sources, queries and assertions unchanged.

## New execution results

Frozen 12c8fa6 precedes baseline: three formal learn/list tests, two failures for
missing positive roles and one passing multiline-stacked negative. Candidate now
passes all three. The necessary related selection ran 66 tests, all passed, no
expected failures. This count is from this rebuilt environment, not the lost run.

`activation-*.json` compares the same source bytes and memory: installing code
alone leaves roles unchanged; ordinary merge learn-path adds exactly four roles.
The eleven identity/range/digest/signature fields in summary.json are unchanged.
SQLite numeric IDs are not promised stable across generations.

Five compatibility queries are copied verbatim from published independent.json;
source bytes are reconstructed from retained context and frozen before this replay.
All five code-anchor dictionaries (including actual bodies/ranges) and primary
path/symbol/range remain identical. The generic Builder request still fails and
four existing controls pass. Token estimates increase by 4 except the ordinary
layout control (+0); all remain below 1500. No original failure reduction is claimed.

## Strict positive syntax contract

Only `.ets` with ArkTS adapter, whole-file known lexical masking, uniquely bound
module function or directly owned component callable receives `arkts_builder`.
Supported decorators are exact bare @Builder, standalone or inline. This is not
resolved framework API identity, runtime execution, exclusive ownership, an
absence certificate, or source-operation proof. Owner kinds and all query/ranking
consumers are unchanged. Metadata slots and token cost are explicitly checked.

Arguments, BuilderParam, arbitrary stacked decorators, duplicate identities,
nested/unknown scope, other languages, bare Builder shadow/reference, slash or
interpolation unknown inputs do not receive new proof. A preceding meaningful
line ending `)` is conservatively refused because it may close a multiline
stacked decorator; this can reject valid declarations after a field initializer.
No generic decorator resolver is claimed. Ordinary parser behavior is unchanged.

The lost earlier attempt exposed multiline stacked decorators; this rebuilt
protocol includes that negative before implementation, rather than claiming a
recovered candidate-red artifact. No old unpublished test result is substituted.
