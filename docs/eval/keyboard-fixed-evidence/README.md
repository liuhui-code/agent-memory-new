# Fixed keyboard evidence pass: no independent generic failure reproduced

Base c711f32. Runtime is unchanged. This executes the four queries already specified
in the local-binding proposal, not the original capability pack or a full suite.

## Freeze and execution

Five source files, four exact query strings, expected identities/body fragments,
forbidden generic competitors and SHA256 hashes were committed before any context
execution. The protocol was not changed after seeing outputs. Exactly one successful
init, one learn-path and eight context calls (raw + compact for each query) appear
in commands.json, all return code 0. public.json contains the actual full results.

Two setup mistakes are retained transparently. An initial protocol-authoring syntax
error left the manifest absent, so the runner failed before any CLI call. After
sources/oracles were fully frozen, init rejected an unsupported --json argument
before execution. The runner setup was corrected and the same frozen sources and
queries were used; neither failure ran a query. setup-error.txt and
init-argument-error.txt preserve them. These are not extra experimental trials.

## Actual results

| Frozen query | Compact source paths | Tokens | Oracle result |
|---|---|---:|---|
| Generic Chinese event-height → focus callback | FocusBinding.ets | 1060 | Pass |
| Exact FocusBinding.attach | FocusBinding.ets | 1093 | Pass |
| Explicit FocusBinding + FocusPreference | FocusPreference.ets, FocusBinding.ets | 1283 | Required identities pass; no extras |
| Literal keyboard height focus | FocusBinding.ets, FocusPreference.ets, StatusText.ets | 1410 | Literal-source recall passes; two extras remain |

Generic output includes the actual viewport.on registration, if(pixels > 0) and both
this.canFocus=true/false writes. It does not merely mention the right filename.
All returned excerpts match the exact frozen source line bytes. Each compact
payload is within the existing 1500-token budget. The literal control's oracle is
source recall, so its pass is NOT a perfect-precision claim.

## Stop condition applied

The generic request passes on the unchanged runtime. Therefore this pass provides
NO independent keyboard red. No additional competitor, changed wording, extra
query, ranking edit, producer, schema, architecture, or original-pack rerun follows.
The root's two-independent-defect requirement for a unified local-binding design
is not satisfied by this result. The existing render red remains a separate result;
this does not show keyboard behavior is universally correct or mark its original
historical failure solved. No original-failure count changes.

No test suite was run. Static git diff checks confirm tools/ and tests/ unchanged.
The task here was the fixed evidence pass, and its stop rule is satisfied.
