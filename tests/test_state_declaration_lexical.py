# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.code_wiki_extractors import extract_arkts_reference_symbols

P = Path(__file__).resolve().parents[1] / 'docs/eval/state-declaration-lexical/protocol.json'

class StateDeclarationLexicalTests(AgentMemoryTestBase):
    def test_public_only_real_state_identity_and_exact_positions(self):
        source = json.loads(P.read_text())['sources']['StateBoard.ets']
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'StateBoard.ets').write_text(source)
            self.run_memory(root, 'init')
            self.run_memory(root, 'learn-path', '--path', '.')
            records = json.loads(self.run_memory(root, 'list', '--type', 'code-symbol', '--limit', '100', '--json').stdout)
            states = [r for r in records if r['symbol_type'] == 'state']
            self.assertEqual(2, len(states))
            self.assertEqual({('StateBoard.live', 2, 2), ('SecondBoard.live', 11, 11)},
                {(r['qualified_name'], r['start_line'], r['end_line']) for r in states})

    def test_legacy_state_only_mask_preserves_other_contracts(self):
        source = json.loads(P.read_text())['sources']['StateBoard.ets']
        self.assertEqual([('live', 'state'), ('live', 'state')], extract_arkts_reference_symbols(source))
        # Event parsing is deliberately outside this repair's scope.
        self.assertIn(('oldEvent', 'event'), extract_arkts_reference_symbols('"@Event oldEvent"'))
        self.assertEqual([('value', 'state')], extract_arkts_reference_symbols('@State\nprivate value: boolean'))

    def test_unknown_full_file_fallback_is_not_absence(self):
        source = json.loads(P.read_text())['sources']['UnknownBoard.ets']
        self.assertEqual([('real', 'state'), ('interpolationGhost', 'state'), ('slashGhost', 'state')],
            extract_arkts_reference_symbols(source))
