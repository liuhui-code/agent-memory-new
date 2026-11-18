# Request-scoped reading completion

The Query Skill applied a causal-only stopping rule to both diagnosis and code understanding. This clarification scopes causal success and user-log analysis to diagnosis. Source reading completes only for inspected requested facts, with contradiction/gap disclosure; log-path and callback incompleteness are explicit counterexamples. Design keeps its separate protocol. No Runtime fields, scores, budgets, historical outputs, benchmark prompts or evaluators change.

## Actual consumer observations before this clarification

Two isolated no-history internal Agent development probes consumed the already published Skill and existing real CLI JSON in ../query-reading-roles-20261118. Neither was shown an oracle or expected target. They were instructed to preserve the JSON, avoid rereading excerpts, and report source reads. These are two developer-consumer observations, NOT independent real projects, a Codex benchmark run, controlled A/B, or original acceptance improvements. Both successfully distinguished target from support despite the text ambiguity; no behavioral failure or improvement is claimed.

- Source-reading original Chinese request: target SecureDocumentBrowser.build, fileAccess line11 and callback12–16. Consumed supplied Web9–14 and two callers1–9; read only Web15–18 to establish return predicate. No source searches, one extra file/read, four lines. Both wrapped callers retained as support with relationship unknown. Static source does not prove reported runtime symptom.
- Exact WRAP_PROFILE_7F19 request: target WrappedProfileService.load6–8; consumed supplied1–9 and read DomainLogger1–9 plus LogSink1–7, one expansion round/two new files, zero searches. Confirmed report→emit→hilog.error with unchanged message. Did not read unrelated ProfileService candidate merely to classify it. No claim about callers into load or actual occurrence.

Both reported current/generation1 without treating that as a Git revision. The source-reading probe received the root-entry reminder only after its initial reference-driven observation, so it is not evidence of complete initial Skill activation. All observations precede this change; tests below verify scope/packaging, not model improvement.

## Separate limitation

The benchmark accepts diagnosis/design, not generic source-reading. Its shared prompt and scoring still use causal/root-owner terms even for design. Do not repurpose it to declare these original Context failures fixed. This separate protocol issue is recorded, not modified here.
