# Generic data is not a network/user-profile topic (Development)

Runtime baseline 6a319253 (preceding 75c0939 is diagnostics only).
Previously the standalone Chinese data term 数据 triggered load/request/fetch/network/
profile/account/user/data together. That relationship is not justified by a generic
data request. Split 数据 into its own rule retaining data translation and literal
tokenization; leave all six explicit network/profile/loading trigger relations intact.
No selection, scoring, thresholds, source-operation or other expansion rules change.

Two independent nonnetwork domains (clipboard content and numeric palette conversion)
were frozen with competing ProfileService source. Both data requests returned the
network profile owner, while otherwise equivalent content requests returned the local
source. After the split, all four return the intended source with real operation
snippets. Explicit loading-user-profile and qualified network-source controls remain.
Initial pure-Chinese clipboard probe had no useful recall without a literal source
identity; retained data-before output records that limitation. The frozen competitive
protocol adds the same clipboard identity to both query variants before production
change. No new Chinese clipboard translation is claimed.

Existing clipboard group: 2/3 -> 3/3; Chinese now includes only the correct reader.
45 focused tests: 44 pass and one existing expectedFailure in weak-log baseline.
Public tests assert nonempty exact expected owner path and actual source snippet,
not merely removal of unwanted source. This does not prove aggregate or language-wide
generalization. No full gate, consumed holdout or remote write. Native-color remains
2/3 as separately documented, and is not counted as a repair.

Command: PYTHONPATH=tests:. python -m unittest tests.test_data_topic_expansion tests.test_locate_intent_expansion tests.test_query_language tests.test_query_language_exclusions tests.test_query_result_alternative tests.test_weak_log_owner_admission tests.test_source_operation_contract -v

Previously repaired language-priority group stays 3/3 under this candidate.
