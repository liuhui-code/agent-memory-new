# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.ecma_callable_headers import (
    MAX_HEADER_LINES,
    function_header,
    method_header,
)
from tools.agent_memory_runtime.ecma_callable_ranges import named_callable_ranges


class EcmaCallableHeaderTests(unittest.TestCase):
    def test_multiline_method_preserves_modifiers_params_and_return_type(self) -> None:
        lines = [
            "  private static async decodeEnvelope(",
            "    notice: Notice,",
            "    channel: string",
            "  ): Promise<Result<void>> {",
            "    return await this.decoder.decode(notice)",
            "  }",
        ]

        header = method_header(lines, 0)

        self.assertIsNotNone(header)
        assert header is not None
        self.assertEqual("decodeEnvelope", header.name)
        self.assertEqual("notice: Notice, channel: string", header.params)
        self.assertEqual("Promise<Result<void>>", header.return_type)
        self.assertTrue(header.async_value)
        self.assertEqual("private", header.visibility)

    def test_multiline_top_level_function_uses_same_range_contract(self) -> None:
        lines = [
            "export async function persistEnvelope(",
            "  payload: Uint8Array",
            "): Promise<void> {",
            "  await storage.write(payload)",
            "}",
        ]

        header = function_header(lines, 0)
        ranges = named_callable_ranges(lines)

        self.assertIsNotNone(header)
        assert header is not None
        self.assertTrue(header.exported)
        self.assertEqual("persistEnvelope", header.name)
        self.assertEqual(5, ranges[0]["end_line"])

    def test_interface_signature_without_body_is_not_callable_range(self) -> None:
        lines = [
            "  decodeEnvelope(",
            "    notice: Notice",
            "  ): Promise<void>;",
        ]

        self.assertIsNone(method_header(lines, 0))
        self.assertEqual([], named_callable_ranges(lines))

    def test_header_scan_is_bounded(self) -> None:
        lines = ["  decodeEnvelope("] + ["    value: string,"] * MAX_HEADER_LINES + [
            "  ): void {",
            "  }",
        ]

        self.assertIsNone(method_header(lines, 0))

    def test_arkui_chained_callback_is_not_a_named_method(self) -> None:
        lines = [
            "    Button(",
            "      'Save'",
            "    ).onClick(() => {",
            "      this.persist()",
            "    })",
        ]

        self.assertIsNone(method_header(lines, 0))

    def test_inline_arkui_decorator_preserves_callable_range(self) -> None:
        lines = [
            "  @Builder renderActiveDocument() {",
            "    Column() {",
            "      Text(this.activeDocument)",
            "    }",
            "  }",
        ]

        header = method_header(lines, 0)
        ranges = named_callable_ranges(lines)

        self.assertIsNotNone(header)
        assert header is not None
        self.assertEqual("renderActiveDocument", header.name)
        self.assertEqual((1, 5), (ranges[0]["start_line"], ranges[0]["end_line"]))

    def test_inline_arkui_styles_uses_same_generic_decorator_contract(self) -> None:
        lines = [
            "  @Styles warningSurface() {",
            "    .backgroundColor(Color.Red)",
            "  }",
        ]

        header = method_header(lines, 0)

        self.assertIsNotNone(header)
        assert header is not None
        self.assertEqual("warningSurface", header.name)

    def test_inline_decorators_with_arguments_share_the_bounded_prefix_scan(self) -> None:
        lines = [
            "  @Monitor('active.value') @Trace onActiveChanged(value: string): void {",
            "    this.refresh(value)",
            "  }",
        ]

        header = method_header(lines, 0)

        self.assertIsNotNone(header)
        assert header is not None
        self.assertEqual("onActiveChanged", header.name)
        self.assertEqual("value: string", header.params)
        self.assertEqual("void", header.return_type)


if __name__ == "__main__":
    unittest.main()
