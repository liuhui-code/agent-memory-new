# Error-topic lexical investigation: candidate rejected

Base e760097. This checkpoint is diagnostic only. No accepted runtime or test
changes. The broad 错误 -> logging vocabulary was investigated independently of
the original validation failure; the original case was not used for design or
rerun after this candidate failed its independent guard.

## Independent red reproduction

The initial frozen synthetic badge UI validator writes an error feedback field;
the packet decoder returns an error value. Neither emits logs. A ConsoleSink and
RuntimeSink really emit logs. On unchanged runtime, adding generic Chinese 错误
to both domain queries selects ConsoleSink, not the requested local source.
Corresponding no-error-word and English error queries return the actual source.
The English error queries have the same inferred runtime_log_diagnosis intent.
Explicit code_location preserves the two Chinese failures, so the topic injection
is separable from the intent lane selection. No code was changed for these probes.

Two explicit sink.method error-log controls were added and frozen before production
changes. Both pass on baseline; generic hilog was already red (ConsoleSink selected)
and is not portrayed as a successful control. All initial observations retained.

## Narrow candidate and decisive rejection

Candidate changes only 错误 to error translation, leaving the other six triggers
and ALL intent logic unchanged. The two nonlog red queries pass and the other eight
frozen observations remain identical. This alone is insufficient acceptance.

A further independently frozen guard explicitly asks to record/output an error
without saying 日志. Each scenario has one genuine logging sink plus the two nonlog
sources. Required owners/body were fixed before running this new guard:

- ConsoleSink: “查找记录错误的实现。” baseline returns ConsoleSink + console.error;
  candidate returns NO anchor. NEW REGRESSION.
- ConsoleSink: “错误在哪里输出？” same baseline pass -> candidate empty regression.
- RuntimeSink-only versions: baseline and candidate both empty. These are existing
  limitations, not green controls or newly caused regressions.

Thus global error-only translation removes useful evidence for genuinely requested
error output. It is not a safe equivalent of the generic loading translation repair.
The candidate is rejected, production and old test files restored byte-for-byte
against e760097. New candidate tests are saved as .py.txt evidence, not installed as
passing regressions or weakened with expectedFailure for the NEW defects. The saved
patch describes the rejected production/token-test candidate; it is not applied.

## Intent/compatibility boundary and next evidence

query_intent_contract deliberately infers runtime_log_diagnosis for Chinese 错误 and
English error. docs/runtime.md specifies legacy lexical inference remains compatible
when no explicit --intent is supplied. That intent inference is unchanged throughout.
The old locate expansion unit also explicitly treats 错误 as a diagnostic expansion;
it was tentatively narrowed with the candidate, then fully restored on rejection.

A future change would need context-sensitive, source-grounded distinction between
error-as-value/UI feedback and a request to record or emit errors. It must preserve
positive output/record intents without requiring users to use a magic 日志 word, plus
English parity, explicit lanes, literal/API names and uncertain generic errors.
No query-specific exception, new word boost, intent override or weights are added.
The present evidence identifies both a real broad-topic failure and the concrete
regression of the proposed remedy; it does not prove all possible fixes impossible.

## Evidence

- protocol.json, frozen-before.json, after.json: unchanged ten-query expectations.
- independent.json: initial eight cases; explicit-code-location.json: explicit lane.
- explicit-output-protocol.json, output-before.json, output-after.json: decisive guard.
- rejected-error-only.patch, candidate-tests.py.txt, red-tests.txt: unaccepted candidate.
- probe*.py use formal init/learn/context; probe-output.py accepts RUNTIME_REPO for
  unchanged baseline pairing (native-listener-current has e760097-equivalent runtime).

No full suite, original validation after-test, holdout, remote publication or original
failure-count improvement. This is not a green serving fix. Parent should preserve
this rejected evidence rather than silently revive the global token split later.
