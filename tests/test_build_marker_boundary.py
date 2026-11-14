# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_code_selection import (
 structural_boundary_query,build_word_or_component,preserve_structural_boundary_neighbors)

class BuildMarkerBoundaryTests(unittest.TestCase):
 def test_all_frozen_predicate_controls(self):
  path=Path(__file__).parents[1]/'docs/evidence/build-marker-boundary/protocol.json'
  for c in json.loads(path.read_text())['predicate_controls']:
   with self.subTest(query=c['query']):self.assertEqual(structural_boundary_query(c['query']),c['expected'])
 def test_isolated_components_without_native_fallback(self):
  for q in ['BuildCache','build_cache','build-profile.json5','build.sh','源码Build配置','Build2Cache']:
   with self.subTest(query=q):self.assertTrue(build_word_or_component(q))
  for q in ['Builder','bodybuilder','builderCache','mybuild','buildable','bodybuild2']:
   with self.subTest(query=q):self.assertFalse(build_word_or_component(q))
 def test_only_build_marker_changes(self):
  for q in ['prefixcmakesuffix','prefixhnpsuffix','makefile','native','package','.so','构建','原生','打包','跨语言']:
   with self.subTest(query=q):self.assertTrue(structural_boundary_query(q))
 def test_preserve_actual_import_neighbor_only_for_build_request(self):
  focused=[{'file_path':'ProfileTile.ets'},{'file_path':'ProfileScreen.ets'}]
  neighbor={'file_path':'TrainingPalette.ts','match_reasons':['graph_neighbor','graph_relation:imports']}
  self.assertEqual(preserve_structural_boundary_neighbors(focused,[*focused,neighbor],'Find the declared Builder that sets padding, background color and width.'),focused)
  self.assertEqual(preserve_structural_boundary_neighbors(focused,[*focused,neighbor],'Find build imports and source.'),[*focused,neighbor])
 def test_negative_cleanup_fallback_remains_old(self):
  self.assertFalse(structural_boundary_query('Find handler; exclude build artifacts.'))
  self.assertTrue(structural_boundary_query('exclude build artifacts'))
  self.assertTrue(structural_boundary_query('Find handler; exclude NativeBuildCache.'))
