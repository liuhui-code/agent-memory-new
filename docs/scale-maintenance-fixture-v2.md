# Scale maintenance fixture v2

This is a benchmark-fixture correction, not relaxation of source safety. The original
primitive database has synthetic files/symbols/edges but no source files or digests. Its
maintenance target collided with a synthetic file, so incremental discovery found missing
callers. A controlled 1,000-entity/3,000-edge reproduction found 49 of 50 sources absent
and all 50 digests absent; strict indexing correctly refused it. The original failing full
regression and independent reproduction are retained.

V2 retains synthetic primitive row counts, latency thresholds, sample repetitions,
operation names and existing assertions. Maintenance uses `maintenance_fixture/Service1.ets`,
initialized by the real writer, in the SAME large database. It no longer exercises fake
reverse dependencies. The separate real 2001-caller fixture supplies fan-in coverage.

Top-level configured/observed counts describe the synthetic primitive snapshot before
maintenance setup, explicitly labeled by `count_snapshot`. Maintenance reports disclose
counts before setup, after setup, rows added and totals after all operations. Thus a
million primitive entities does not imply exactly a million rows throughout maintenance.
The final database-size field includes real maintenance rows.

Results carry `fixture_version=scale-fixture/v2`. V1 maintenance numbers are NOT directly
comparable, and passing v2 cannot be presented as passing the unchanged original maintenance
fixture. No full regression or CI/million result is claimed until separately executed.
