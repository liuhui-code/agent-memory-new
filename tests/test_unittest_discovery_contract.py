# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import ast
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent


class UnittestDiscoveryContractTests(unittest.TestCase):
    def test_test_modules_do_not_define_uncollected_top_level_test_functions(self) -> None:
        offenders: list[str] = []
        for path in sorted(TESTS_DIR.glob("test_*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            offenders.extend(
                f"{path.name}:{node.lineno}:{node.name}"
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            )
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
