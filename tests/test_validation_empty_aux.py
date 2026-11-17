# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Frozen empty-auxiliary component controls; no product CLI."""
import importlib
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'docs/evidence/validation13-empty-aux'
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
parse = importlib.import_module('agent_memory_runtime.validation_field_source').parse_validation_field_file
controls = json.loads((HERE / 'INPUT-CONTROLS-DRAFT.json').read_text())

class FrozenEmptyAuxControls(unittest.TestCase):
    def test_frozen_controls(self):
        self.assertEqual(len(controls['controls']), 38)
        expected_fact = controls['expected_fact']
        for case in controls['controls']:
            with self.subTest(id=case['id']):
                expected = case['expected']
                if expected in ('one_validation_fact', 'same_exact_fact_as_typed_baseline'):
                    expected = [expected_fact]
                self.assertEqual(parse(case['source']), expected)

if __name__ == '__main__':
    unittest.main()
