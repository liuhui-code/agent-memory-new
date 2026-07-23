# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.arkts_context_contracts import (
    extract_arkts_context_contracts,
)


class ArkTSContextContractTests(unittest.TestCase):
    def test_extracts_ui_persistence_and_platform_contracts(self) -> None:
        ui = "Button('Done').onClick(() => { this.finish(); })"
        persistence = "profilePreferences.getSync('profiles', '[]')"
        platform = "TabSegmentButtonV2({}); app.setColorMode(ConfigurationConstant.ColorMode.COLOR_MODE_DARK)"

        self.assertEqual(["uicallbackbinding"], extract_arkts_context_contracts(ui))
        self.assertEqual(["persistenceread"], extract_arkts_context_contracts(persistence))
        self.assertEqual(["platformsensitiveui"], extract_arkts_context_contracts(platform))

    def test_ignores_comments_and_unrelated_collections(self) -> None:
        source = "// Button('Done').onClick(() => {})\ncache.get('profiles')"
        self.assertEqual([], extract_arkts_context_contracts(source))


if __name__ == "__main__":
    unittest.main()
