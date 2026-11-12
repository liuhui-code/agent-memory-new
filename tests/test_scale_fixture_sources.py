# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.scale_benchmark import ScaleProfile, seed_scale_data, run_scale_benchmark
from tools.agent_memory_runtime.scale_maintenance import TARGET_PATH, prepare_git_scope
from tools.agent_memory_runtime.storage import resolve_project, ensure_initialized, connect
from tools.agent_memory_runtime.index_freshness import file_sha256


class ScaleFixtureSourceTests(unittest.TestCase):
    def test_real_maintenance_setup_preserves_synthetic_graph_and_has_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'
            root.mkdir()
            project = resolve_project(str(root), str(Path(directory) / 'memory'))
            ensure_initialized(project)
            seed_scale_data(project, ScaleProfile('tiny', 1000, 3000, 2))
            with connect(project) as conn:
                before = [tuple(row) for row in conn.execute('SELECT * FROM memory_edges ORDER BY id')]
                self.assertIsNone(conn.execute('SELECT id FROM code_files WHERE file_path=?', (TARGET_PATH,)).fetchone())
            prepare_git_scope(project)
            with connect(project) as conn:
                self.assertEqual(before, [tuple(row) for row in conn.execute('SELECT * FROM memory_edges WHERE id<=3000 ORDER BY id')])
                row = conn.execute('SELECT source_digest,index_generation FROM code_files WHERE file_path=?', (TARGET_PATH,)).fetchone()
                self.assertEqual(file_sha256(root / TARGET_PATH), row['source_digest'])
                self.assertGreater(row['index_generation'], 0)
                symbols = conn.execute('SELECT source_digest,index_generation FROM code_symbols WHERE file_path=?', (TARGET_PATH,)).fetchall()
                self.assertTrue(symbols)
                self.assertTrue(all(tuple(symbol) == tuple(row) for symbol in symbols))

    def test_v2_discloses_count_snapshots_and_keeps_primitive_counts(self):
        report = run_scale_benchmark(ScaleProfile('tiny', 1000, 3000, 2))
        self.assertEqual('scale-fixture/v2', report['fixture_version'])
        self.assertEqual('pass', report['status'])
        self.assertEqual(report['configured_counts'], report['observed_counts'])
        fixture = report['incremental_maintenance']['fixture']
        self.assertEqual('scale-maintenance-fixture/v2', fixture['version'])
        self.assertEqual(report['observed_counts'], fixture['counts_before_setup'])
        for key, added in fixture['rows_added_at_setup'].items():
            self.assertEqual(fixture['counts_after_setup'][key] - fixture['counts_before_setup'][key], added)
        self.assertGreater(fixture['rows_added_at_setup']['code_files'], 0)
        self.assertGreater(fixture['counts_after_operations']['searchable_entities'], 1000)
        self.assertIn('not directly comparable', fixture['historical_comparability'])
