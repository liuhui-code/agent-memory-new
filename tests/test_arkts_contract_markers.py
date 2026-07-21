# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.arkts_behavior_markers import (
    extract_arkts_behavior_markers,
)
from tools.agent_memory_runtime.query_behavior_concepts import behavior_marker_terms


class ArkTSContractMarkerTests(unittest.TestCase):
    def test_command_binding_requires_executable_callback_property(self) -> None:
        source = """const entries = [{
  title: 'Restore',
  invoke: async (): Promise<void> => { await this.archive.restoreSnapshot() }
}]"""
        self.assertIn("commandbinding", extract_arkts_behavior_markers(source))
        self.assertNotIn(
            "commandbinding",
            extract_arkts_behavior_markers("@Event invoke: () => Promise<void>"),
        )

    def test_disclosure_state_requires_rotation_and_same_state_toggle(self) -> None:
        source = """SymbolGlyph($r('sys.symbol.chevron_down'))
  .rotate({ angle: this.expanded ? 180 : 0 })
  .onClick(() => { this.expanded = !this.expanded })"""
        self.assertIn("disclosurestate", extract_arkts_behavior_markers(source))
        self.assertNotIn(
            "disclosurestate",
            extract_arkts_behavior_markers("SymbolGlyph($r('sys.symbol.chevron_down'))"),
        )

    def test_error_contract_marks_returning_catch_and_presenting_consumer(self) -> None:
        producer = """try { await socket.send(data) } catch (error) {
  Logger.error(`${error}`)
  return `${error}`
}"""
        consumer = """const result = await service.submit()
if (typeof result === 'string') { this.showBanner(`Failed: ${result}`) }"""
        self.assertIn("errorreturnboundary", extract_arkts_behavior_markers(producer))
        self.assertIn("errorpresentationboundary", extract_arkts_behavior_markers(consumer))

    def test_queries_expand_only_to_the_corresponding_contract_markers(self) -> None:
        self.assertEqual(
            ["commandbinding"],
            behavior_marker_terms("The menu command invokes the wrong method"),
        )
        self.assertEqual(
            ["disclosurestate"],
            behavior_marker_terms("Expanded details indicator points the wrong way"),
        )
        self.assertEqual(
            ["errorreturnboundary", "errorpresentationboundary"],
            behavior_marker_terms("The page shows a raw error value"),
        )


if __name__ == "__main__":
    unittest.main()
