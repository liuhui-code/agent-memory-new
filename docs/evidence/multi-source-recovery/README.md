# Selected callable source recovery with multiple retained anchors

Baseline a6c1d93. This extends only the previously accepted transactional rank-detail
trade, not anchor selection, priority, source identity or budget limits.

## Discovery and independent freeze

Actual color English has three role=primary anchors plus one expansion. Its target
range is 2..12 but excerpt is only 2..5. Copy-only rank trade fits complete target
in 1460 tokens, with all other anchors retained. Webview original has three primary
roles; its build range 8..18 differs from Column excerpt9..13. English has a single
primary but component range4..19 differs from Column9..12. These cannot use the
strict same-identity/start restoration, and remain unchanged.

Role=primary means up to three source slots, not sole callable ownership. The
approved narrow extension uses existing callable_evidence.primary to identify
exactly one matching existing anchor (file, symbol, start and end). It neither
downgrades other primary roles nor asserts they are less relevant or complete.

Independent probes were frozen before implementation: class targets produced
multiple ranges (reject); an unqualified function query retained only one source;
explicit file comparison retained three sources. The initial 12-slot formatter
had already lost ranking details and cannot trade them again. A predeclared
6/8/10-slot length matrix then demonstrated three complete retained target sets,
where selected formatter had a matching single range but its return tail was
truncated and optional ranking diagnostics remained. c2b12fc records these public
reds and original snapshots, not only helper-constructed inputs.

## Contract

For multiple anchors only, callable primary must have valid integer bounds and
nonempty path/symbol; exactly one anchor may share its path, must be role primary,
and must match the complete single source range. Unknown/ambiguous/multiple-range
identity rolls back. Single-anchor behavior retains the previous contract.

All previous guards remain: current freshness, exact raw record kind/id/path/
symbol/bounds, unique digest, one <=2MiB raw byte snapshot for hash and extraction,
unchanged prefix, <=40 lines, <=1500 source characters, <=2600 total excerpt
characters, and <=1500 estimated payload tokens. Total characters now sum the
replacement AND every other preserved excerpt; unknown external excerpt content
or source metadata causes rollback. No other body, anchor, role, alternative,
log, path, identity, mechanism, certificate, uncertainty or unknown reason is
removed. An unrelated partial source remains partial, not silently completed.

Only the existing optional numeric scores and four allowlisted ranking reasons
can be removed. This is explicitly a LOSSY ranking-detail trade, not lossless
output compression. Complete replacement is accepted on a deep copy only when
it fits; otherwise the original object and all its fields remain unchanged.

## Results

Independent length matrix restores the selected formatter including its return
while preserving both explicitly requested side sources and all three primary
roles. Actual final sizes are 1368/1407/1443 tokens; source totals718/856/994.
Tests compare the full payload modulo only allowed ranking fields, target excerpt
and budget statistics. Unknown-source, missing/raw type identity, ambiguous path,
multiple range, bool range, changed digest, token/line/individual/total caps and
additional protected log/path/certificate controls cover rollback/preservation.

Existing targeted original groups remain 7/9 before and after: causal-profile3/3,
color2/3, webview2/3; individual statuses unchanged. Color English now has full
2..12 body at1460 tokens but remains precision-failing. Webview mismatched source
identities are unchanged. No original-failure reduction is claimed. No full gate.

Final related run: 59 tests passed, 0 failures/errors, 0 expected failures.
