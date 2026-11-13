# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.ecma_callable_ranges import property_callback_ranges

class PropertyCallbackLexicalTests(AgentMemoryTestBase):
    def test_public_fake_owner_and_true_duplicate_owners(self):
        protocol=json.loads((Path(__file__).resolve().parents[1]/'docs/evidence/property-callback-lexical/protocol.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,source in protocol['sources'].items(): (root/name).write_text(source)
            self.run_memory(root,'init'); self.run_memory(root,'learn-path','--path','.')
            symbols=self.list_records(root,'code-symbol')
            real=[s for s in symbols if s['file_path']=='TwoOwners.ts' and s['symbol']=='execute']
            self.assertEqual({('PrimaryAction',2,4),('SecondaryAction',7,9)}, {(s['owner_name'],s['start_line'],s['end_line']) for s in real})
            self.assertEqual(2,len({s['symbol_key'] for s in real}))
            fake=[s for s in symbols if s['file_path']=='ExampleGuide.ts' and s['symbol_type']=='function']
            self.assertEqual([],fake)
            out=json.loads(self.run_memory(root,'context','--query',protocol['query'],'--json').stdout)
            self.assertNotEqual('phantomHandler',out['query_handoff']['callable_evidence'].get('primary',{}).get('symbol'))

    def test_unknown_files_exact_legacy_property_ranges(self):
        from tools.agent_memory_runtime.ecma_callable_ranges import PROPERTY_CALLBACK_RE, MAX_CALLBACK_RANGES, source_range
        from tools.agent_memory_runtime.ecma_braces import block_end
        def legacy(lines):
            result=[]
            for index,line in enumerate(lines):
                match=PROPERTY_CALLBACK_RE.match(line)
                if match:
                    result.append(source_range(match.group(1),index,block_end(lines,index),'ecma_property_callback_window'))
                if len(result)>=MAX_CALLBACK_RANGES: break
            return result
        for prefix in ['const r=/"/;', 'const r=/`/;', 'const n=a/b;', 'const s=`${button()}`;', 'const s=`unterminated']:
            lines=(prefix+'\nexecute: () => {\n run()\n}').splitlines()
            self.assertEqual(legacy(lines),property_callback_ranges(lines))

    def test_comment_and_template_do_not_hide_two_real_ranges(self):
        for wrapper in ['/*\n%s\n*/','const text = `\n%s\n`;']:
            text='execute: () => {\n}\n'+wrapper%('execute: () => {\n}')+'\nexecute: () => {\n}\n'
            found=property_callback_ranges(text.splitlines())
            self.assertEqual([(1,2),(7,8)],[(r['start_line'],r['end_line']) for r in found])
