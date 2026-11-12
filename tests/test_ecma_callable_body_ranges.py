# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Development regressions for callable boundaries, not external evaluation cases."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
from tools.agent_memory_runtime.ecma_callable_ranges import callable_line_ranges
from tools.agent_memory_runtime.semantic_ecma import parse_containers, parse_container_members


class CallableBodyRangeTests(unittest.TestCase):
    def assert_span(self, text, name, expected):
        variants = [text.splitlines(), text.splitlines(keepends=True),
                    text.replace('\n', '\r\n').splitlines(keepends=True)]
        for lines in variants:
            ranges = [r for r in callable_line_ranges(lines) if r['symbol'] == name]
            self.assertEqual([(r['start_line'], r['end_line']) for r in ranges], [expected])
            if lines[0].startswith('export class'):
                container = parse_containers(lines, 'TypeScript', 'example.ts')[0]
                methods, _ = parse_container_members(lines, 'TypeScript', 'example.ts', container, False)
                method = next(m for m in methods if m.entity.name == name)
                self.assertEqual((method.entity.start_line, method.entity.end_line), expected)

    def test_multiline_destructuring_and_default_callback(self):
        self.assert_span('''export class DispatchRouter {
  routePacket(
    packet: string,
    { before = () => {}, cache = false }: {
      before?: () => void
      cache?: boolean
    } = {},
  ): string {
    before()
    return this.deliverPacket(packet)
  }
  clearRoutes(): void {
    this.routes.clear()
  }
}''', 'routePacket', (2, 11))

    def test_default_object_with_body_on_next_line(self):
        self.assert_span('''export function choose(options = {})
{
  return options
}
function next() {
  return 2
}''', 'choose', (1, 4))

    def test_inline_return_object_type(self):
        self.assert_span('''export class Factory {
  create(): {
    value: string
  } {
    return { value: 'ok' }
  }
  next() {
    return 2
  }
}''', 'create', (2, 6))

    def test_decorator_object_and_parameter_comments(self):
        self.assert_span('''export class Router {
  @Trace({ label: 'route' }) send(
    value: string, // ) { misleading comment
    options = { nested: { value: ')' } }
  ): string {
    return value
  }
  next() { return 2 }
}''', 'send', (2, 7))

    def test_top_level_arrow_destructured_parameters(self):
        self.assert_span('''export const choose = (
  { option = { enabled: true } } = {},
): string => {
  return option.enabled ? 'yes' : 'no'
}
const next = () => {
  return 2
}''', 'choose', (1, 5))

    def test_expression_arrow_does_not_claim_following_block(self):
        self.assert_span('''const choose = ({ enabled = true } = {}) => enabled
function next() {
  return 2
}''', 'choose', (1, 1))

    def test_simple_body_literals_comments_and_adjacent_method(self):
        text = '''export class Stable {
  first(): string {
    // } {
    const literal = `unbalanced } {`
    /* } */
    if (literal) { return literal }
    return '}'
  }
  second(): string {
    return 'second'
  }
}'''
        self.assert_span(text, 'first', (2, 8))
        self.assert_span(text, 'second', (9, 11))

    def test_return_type_combinations(self):
        for return_type in ["{ value: string }", "Promise<{ value: string }>",
                            "{ value: string } | null", "'ready'", "() => { value: string }"]:
            with self.subTest(return_type=return_type):
                self.assert_span(f'''export function make(): {return_type}
{{
  return result
}}
function next() {{ return 2 }}''', 'make', (1, 4))

    def test_comments_between_signature_and_body(self):
        self.assert_span("""function make(options = {}) /* { comment } */
{
  return options
}""", 'make', (1, 4))
        self.assert_span("""const make = (options = {}) => // { comment }
{
  return options
}""", 'make', (1, 4))

    def test_literal_expression_arrow_stays_on_its_own_line(self):
        self.assert_span("""const make = () => 'ready'
function next() {
  return 2
}""", 'make', (1, 1))

    def test_multiline_expression_arrows_stop_before_next_callable(self):
        expressions = [
            "({\n  value: 1,\n})",
            "[\n  'one',\n  'two',\n]",
            "build(\n  { value: ')' },\n  options,\n)",
            "`first\n  second`",
            "load()\n  .then(value => ({ value }))",
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                text = f"const make = () => {expression};\nfunction next() {{\n  return 2\n}}"
                self.assert_span(text, 'make', (1, expression.count('\n') + 1))
                self.assert_span(text, 'next', (expression.count('\n') + 2,
                                               expression.count('\n') + 4))

    def test_arrow_returning_function_type_uses_implementation_arrow(self):
        for return_type in ['() => string', '(value: string) => string', '(() => string)']:
            with self.subTest(return_type=return_type):
                self.assert_span(f"""const make = (): {return_type} => {{
  return () => 'ok'
}}
function next() {{ return 2 }}""", 'make', (1, 3))

    def test_bodyless_signatures_do_not_claim_adjacent_implementation(self):
        text = """interface Sink {
  info(message: string): void
  error(message: string): void
}
function emit() {
  return 2
}
"""
        for lines in [text.splitlines(), text.splitlines(keepends=True)]:
            self.assertEqual([r['symbol'] for r in callable_line_ranges(lines)], ['emit'])
        text = """export class Sink {
  send(message: string): string
  send(message: unknown): string {
    return String(message)
  }
}"""
        for lines in [text.splitlines(), text.splitlines(keepends=True)]:
            ranges = callable_line_ranges(lines)
            self.assertEqual([(r['symbol'], r['start_line'], r['end_line']) for r in ranges],
                             [('send', 3, 5)])

    def test_header_limits_and_overload_remain_bounded(self):
        self.assertEqual(callable_line_ranges(['function missing(', *['  arg,'] * 12, ') {', '}']), [])
        self.assertEqual(callable_line_ranges(['function declared(value: string): void;']), [])


class CallableBodyHandoffTests(unittest.TestCase):
    def test_actual_cli_handoff_retains_complete_method(self):
        source = '''export class DispatchRouter {
  routePacket(
    packet: string,
    { before = () => {} }: {
      before?: () => void
    } = {},
  ): string {
    before()
    return packet
  }
  clearRoutes(): void {
    this.routes.clear()
  }
}
'''
        self.assert_handoff(source, 'DispatchRouter.routePacket', 'routePacket', (2, 10))

    def test_actual_cli_handoff_retains_multiline_arrow(self):
        for signature, expression in [
            ('() =>', '({\n  value: 1,\n})'),
            ('(): () => string =>', "{\n  return () => 'ready'\n}"),
        ]:
            with self.subTest(signature=signature):
                source = f"export const createPacket = {signature} {expression};\n"
                source += "export function nextPacket() {\n  return 2\n}\n"
                self.assert_handoff(source, 'createPacket', 'createPacket', (1, 3))

    def assert_handoff(self, source, query, name, expected):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / 'source'
            project.mkdir()
            (project / 'router.ts').write_text(source, encoding='utf-8')
            base = [sys.executable, str(ROOT / 'tools/agent_memory.py')]
            common = ['--project', str(project), '--memory-home', str(root / 'memory')]
            for command in [['init'], ['learn-path', '--path', '.', '--json']]:
                result = subprocess.run(base + command + common, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run(base + ['context', '--query', query,
                                            '--compact', '--json'] + common, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            handoff = json.loads(result.stdout)['query_handoff']
            primary = handoff['callable_evidence']['primary']
            self.assertEqual(primary['symbol'], name)
            self.assertEqual(primary['source_range']['start_line'], expected[0])
            self.assertEqual(primary['source_range']['end_line'], expected[1])
            spans = [r for a in handoff['code_anchors'] for r in a['source_ranges']
                     if r['symbol'] == name]
            self.assertEqual([(r['start_line'], r['end_line']) for r in spans], [expected])


if __name__ == '__main__':
    unittest.main()
