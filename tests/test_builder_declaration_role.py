# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
D = Path(__file__).resolve().parents[1] / 'docs/evidence/builder-role-rebuild'

class BuilderDeclarationRoleTests(AgentMemoryTestBase):
    def check_sources(self, sources, expected):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, source in sources.items():
                (root / name).write_text(source)
            self.run_memory(root, 'init')
            self.run_memory(root, 'learn-path', '--path', '.')
            rows = json.loads(self.run_memory(root, 'list', '--type', 'code-symbol', '--limit', '300', '--json').stdout)
            actual = {(r['file_path'], r['qualified_name']) for r in rows
                      if 'arkts_builder' in json.loads(r['callable_roles'] or '[]')}
            self.assertEqual({tuple(x) for x in expected}, actual)

    def test_public_declaration_roles(self):
        p = json.loads((D / 'protocol.json').read_text())
        self.check_sources(p['sources'], p['expected'])

    def test_unsupported_binding_and_known_neighbors(self):
        p = json.loads((D / 'protocol.json').read_text())
        self.check_sources(p['controls'], p['controls_expected'])

    def test_multiline_stacked_is_unknown(self):
        p = json.loads((D / 'protocol.json').read_text())
        self.check_sources(p['stacked'], [])
