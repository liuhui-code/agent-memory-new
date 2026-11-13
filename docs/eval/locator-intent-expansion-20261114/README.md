# Request action is not a log topic (Development)

Base 85534be. The only production change removes Chinese "定位" (locate) from
one log-topic expansion trigger tuple. Literal query tokenization preserves the
word. All seven explicit diagnostic triggers and their ten expansions are
unchanged; no scores, other dictionaries, thresholds, roles or source filters
change. "Locate source" does not itself request logs, matching English behavior.

## Root-cause evidence
The original language-priority Chinese failure was not a Python exclusion bug:
its callers already passed positive_retrieval_query into language filtering.
The request action added log/logger/console/hilog/error/etc, allowing an unrelated
ConsoleFailureReporter to outrank the requested Receipt implementation.

Two frozen independent non-log domains demonstrate the same cause: invoice export
and palette conversion. With generic method names and a normal diagnostic sink,
"定位" chooses ErrorConsoleSink in compact context; otherwise identical "查找"
requests return the right sources. Removing this erroneous topic implication
makes both variants return InvoiceExporter/PaletteParser with actual filesDir /
parseInt source. Explicit error log, exception output and qualified logger
requests keep their emitter. Initial strongly named method probes already passed
compact but showed irrelevant raw log evidence; those observations are retained,
not presented as failures. No runtime change was made before the competitive
sources and queries were frozen.

## Results and limits
- Existing selected language-priority group: 2/3 -> 3/3. Chinese now includes
  ReceiptExportCoordinator and the required source excerpt. It still has other
  allowed anchors; this is NOT claimed as perfect precision.
- Two independent behavior pairs and four real diagnostic controls pass. All
  seven old explicit diagnostic expansion triggers have token-level controls.
- 67 focused tests finish: 66 pass and one pre-existing expected failure in
  test_preserved_generic_log_caller_expectation, unchanged in this patch.
- Compile/diff checks pass. No full aggregate suite, consumed holdout or remote.

Command: PYTHONPATH=tests:. python -m unittest tests.test_locate_intent_expansion tests.test_query_language tests.test_query_language_exclusions tests.test_source_path_policy tests.test_query_result_alternative tests.test_log_event_identity tests.test_log_anchored_paths tests.test_context_log_alignment tests.test_opaque_log_admission tests.test_weak_log_owner_admission tests.test_log_api_callable_contract -v

Fixtures are synthetic. Public outputs are bounded projections with raw stdout
hashes. Runners accept RUNTIME_REPO and use tools/agent_memory.py only. The opaque
regression test's generated tracked output was restored after testing, not
included in this stage.
