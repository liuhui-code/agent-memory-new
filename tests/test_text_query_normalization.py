# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.text import (
    bounded_query_tokens,
    matching_code_path_segments,
    query_tokens,
    score_identifier_identity,
    score_weighted_fields,
)


class TextQueryNormalizationTests(unittest.TestCase):
    def test_camel_case_identifier_keeps_whole_and_component_parts(self) -> None:
        tokens = query_tokens("ReplyToPreview.ets")

        self.assertIn("replytopreview", tokens)
        self.assertIn("reply", tokens)
        self.assertIn("preview", tokens)

    def test_query_variants_normalize_replied_and_plural_preview(self) -> None:
        tokens = query_tokens("replied-message previews")

        self.assertIn("reply", tokens)
        self.assertIn("preview", tokens)
        self.assertIn(
            "preview",
            matching_code_path_segments(
                "replied-message previews",
                "src/views/Message/ReplyToPreview.ets",
            ),
        )
        self.assertGreater(
            score_identifier_identity("replied-message previews", "ReplyToPreview"),
            0.0,
        )

    def test_non_plural_words_are_not_aggressively_stemmed(self) -> None:
        tokens = query_tokens("status media")

        self.assertIn("status", tokens)
        self.assertNotIn("statu", tokens)

    def test_bounded_retrieval_terms_keep_late_explicit_identifiers(self) -> None:
        tokens = bounded_query_tokens(
            "消息列表 MessageRow 和引用消息预览 QuotedMessagePreview 的文字大小不一致",
            12,
        )

        self.assertIn("messagerow", tokens)
        self.assertIn("quotedmessagepreview", tokens)

    def test_generic_layer_terms_do_not_receive_path_identity_bonus(self) -> None:
        self.assertEqual(
            [],
            matching_code_path_segments(
                "media path rendering failed",
                "src/views/Chat/ChatDetailBottomMediaSheet.ets",
            ),
        )
        self.assertEqual(
            ["login"],
            matching_code_path_segments(
                "login action failed",
                "src/pages/Login/Password.ets",
            ),
        )

    def test_short_ascii_query_term_does_not_match_inside_identifier(self) -> None:
        score, _reasons = score_weighted_fields(
            "log",
            ["log"],
            set(),
            [("summary", "Catalog filter component", 1.0)],
            [],
        )

        self.assertEqual(0.0, score)


if __name__ == "__main__":
    unittest.main()
