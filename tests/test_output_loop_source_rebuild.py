# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Independent source controls frozen before the output-loop implementation."""
import unittest
from tools.agent_memory_runtime.query_output_loop_source import parse_output_loop_source

SOURCE='''export class PacketCollector {
  collect(feed: PacketFeed): string {
    const pieces: string[] = []
    let item = feed.readLine()
    while (item !== null) {
      pieces.push(item)
      item = feed.readLine()
    }
    return pieces.join(' ')
  }
  label(): string {
    return 'output iteration accumulation'
  }
}
'''
class OutputLoopSourceTests(unittest.TestCase):
    def test_direct_and_renamed(self):
        for source in (SOURCE,SOURCE.replace('pieces','records').replace('item','record').replace('feed','input'),SOURCE.replace('\n','\r\n'),SOURCE.replace('\n','\r')):
            result=parse_output_loop_source(source)
            self.assertEqual(result['owner'],'PacketCollector')
            self.assertEqual([(x['name'],x['start_line'],x['end_line'])for x in result['methods']],[('collect',2,10)])
    def test_nonwitness_or_unknown_stays_unknown(self):
        variants=[
          SOURCE.replace('pieces.push(item)','defer(() => pieces.push(item))'),
          SOURCE.replace('      pieces.push(item)\n','').replace("    return pieces.join",'    pieces.push(item)\n    return pieces.join'),
          SOURCE.replace('item = feed.readLine()\n    }','item = other.readLine()\n    }'),
          SOURCE.replace('pieces.push(item)','other.push(item)'),
          SOURCE.replace('pieces.push(item)','pieces.push(other)'),
          SOURCE.replace('while (item !== null)','if (item !== null)'),
          SOURCE.replace('while (item !== null)','while (other !== null)'),
          SOURCE.replace('item !== null','item != null'),
          SOURCE.replace('      item = feed.readLine()\n',''),
          SOURCE.replace("return pieces.join(' ')","return other.join(' ')"),
          SOURCE.replace('const pieces','let pieces'),
          SOURCE.replace("return pieces.join","return\npieces.join"),
          SOURCE.replace("return pieces.join","return /*\n*/ pieces.join"),
          SOURCE.replace('!==','! = ='),
          SOURCE.replace('let item','let feed'),
          SOURCE.replace('    while', '    audit(item)\n    while'),
          SOURCE.replace("return 'output iteration accumulation'",'return dangerous()'),
          SOURCE+'export function unknown() {}',
          'export class One { read(feed: PacketFeed): string { return feed.readLine() } }',
          'export class Label { label(): string { return "while readLine push join" } }',
        ]
        for source in variants:
            with self.subTest(source=source):self.assertIsNone(parse_output_loop_source(source))
    def test_non_crlf_separators_unknown_everywhere(self):
        for sep in '\v\f\x1c\x1d\x1e\x85\u2028\u2029':
            for source in (SOURCE.replace('return pieces','return /*'+sep+'*/ pieces'),SOURCE.replace("join(' ')","join('"+sep+"')")):
                self.assertIsNone(parse_output_loop_source(source))
    def test_strict_reserved_bindings_unknown(self):
        for name in ('enum','package','eval','arguments'):
            for old in ('feed','pieces','item'):
                self.assertIsNone(parse_output_loop_source(SOURCE.replace(old,name)))
    def test_duplicate_member_unknown(self):
        self.assertIsNone(parse_output_loop_source(SOURCE.replace('label():','collect():')))

if __name__=='__main__':unittest.main()
