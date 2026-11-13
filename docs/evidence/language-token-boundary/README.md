# ETS short-alias token boundary

Baseline 5715206. Independent protocol/public red committed as bc82183 before
serving changes. An ordinary packet query correctly recalls packet_decoder.py
but also unrelated EntryStage.ets: substring `ets` inside `packets` activates the
entire platform expansion. The independent frozen compact acceptance requires
only the actual decoder and verifies decoded.append(packet.decode("utf-8")) source.

The implementation changes ONLY matching of the short `ets` trigger. ASCII
identifier characters [a-z0-9_$] on either side prevent expansion. Ordinary
packets/assets/sets/getStatus/ets_handler/ets2/$ets do not assert ETS intent.
Standalone ETS, punctuation/file extension source.ets and Chinese-adjacent
用ets实现 still trigger the complete existing expansion. No expansion list,
ranking, scoring or language-versus-platform semantics changes.

The original token protocol explored arktsHelper and harmonyosAdapter as well.
They are explicitly OUT OF SCOPE, not repaired negatives: their existing broad
expansion remains, and regression tests now assert that unchanged behavior.
The broader four-word boundary prototype was narrowed before acceptance; only
ETS has independently proven public impact in this stage. It does not incorporate
the separately rejected language-only/platform group split.

## Results

- 47 tests passed; 0 failures/errors, 0 expected failures. Modules: new boundary,
  text normalization, query language/exclusions, candidate recall, mechanism
  precision. Public source-content assertion included.
- Independent packet compact output loses only the unrelated platform source;
  real decoder/source is retained. Assets/sets without matching source no longer
  return the unrelated EntryStage in the same exploratory fixture.
- Independent application startup controls copied from the separate language
  investigation are frozen in startup-protocol.json. This baseline and candidate
  both pass all 4 English/Chinese ETS/ArkTS queries with EntryAbility.ets and
  stage.loadContent body. These results were rerun here, not inferred.
- No original231 failure reduction is claimed; no full acceptance run performed.

Artifacts: before/after.json, red.txt, related.txt, startup-before/after.json.
The broad-expansion green prototype log is not the final result; related.txt
records the final ETS-only candidate. Normalization is query-time, not an index
schema change.
