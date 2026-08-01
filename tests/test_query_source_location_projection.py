# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.query_code_focus import attach_file_source_locations


class QuerySourceLocationProjectionTests(unittest.TestCase):
    def test_file_inherits_callable_location_without_overwriting_semantic_symbol(self) -> None:
        resource = {
            "kind": "symbol",
            "file_path": "pages/Index.ets",
            "symbol": "app.media.logo",
            "symbol_type": "resource",
        }
        file_item = {
            "kind": "file",
            "file_path": "pages/Index.ets",
        }
        callable_item = {
            "kind": "symbol",
            "file_path": "pages/Index.ets",
            "symbol": "build",
            "symbol_type": "function",
            "start_line": 5,
            "end_line": 7,
        }

        attach_file_source_locations([resource, file_item, callable_item])

        self.assertEqual("app.media.logo", resource["symbol"])
        self.assertEqual("resource", resource["symbol_type"])
        self.assertNotIn("start_line", resource)
        self.assertEqual("build", file_item["symbol"])
        self.assertEqual((5, 7), (file_item["start_line"], file_item["end_line"]))


if __name__ == "__main__":
    unittest.main()
