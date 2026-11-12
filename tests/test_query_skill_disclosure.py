# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Keep shared evidence contracts reachable after Query Skill disclosure."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from install import copy_skill_dir


ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / "skills" / "agent-memory-query"


class QuerySkillDisclosureTests(unittest.TestCase):
    def test_entry_explicitly_loads_shared_evidence_sections(self) -> None:
        entry = (QUERY / "SKILL.md").read_text(encoding="utf-8")
        policy = (QUERY / "references" / "evidence-policy.md").read_text(encoding="utf-8")

        self.assertIn("shared evidence-policy requirements below still apply", entry)
        self.assertIn("Before weighing evidence, read and follow [Authority]", entry)
        self.assertIn("stable product behavior or architecture decisions", entry)
        self.assertIn("whenever either query facade returns `normative_context`", entry)
        for heading in ("Normative Context", "Authority"):
            anchor = heading.lower().replace(" ", "-")
            with self.subTest(heading=heading):
                self.assertIn(f"(references/evidence-policy.md#{anchor})", entry)
                self.assertIn(f"## {heading}\n", policy)

    def test_shared_policy_retains_normative_review_contract(self) -> None:
        policy = (QUERY / "references" / "evidence-policy.md").read_text(encoding="utf-8")
        normative = policy.split("## Normative Context\n", 1)[1].split("\n## ", 1)[0]

        for marker in (
            "query_handoff.normative_context", "project_context.normative_context",
            "examined_document_count", "candidate_limit_exceeded",
            "omitted_document_count", "omitted_evidence_gap_count", "truncated",
            "source.digest", "source.observed_digest", "allowed_use",
            "scope_basis: document_source_root", "source.matches_query_project",
            "source_root_requires_agent_confirmation", "expected_contract_candidate",
            "replacement_lookup", "not_indexed", "ambiguous", "unique",
            "approval evidence", "drafts", "superseded/withdrawn/rejected",
            "fresh digest or a Git commit alone never proves approval",
            "Target-source and approval flags", "--compact",
            "Report expected behavior and observed implementation separately",
            "do not synthesize\nan approved Feature Spec",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, normative)

    def test_shared_authority_retains_order_and_limits(self) -> None:
        policy = (QUERY / "references" / "evidence-policy.md").read_text(encoding="utf-8")
        authority = policy.split("## Authority\n", 1)[1].split("\n## ", 1)[0]
        order = authority.split("```text\n", 1)[1].split("```", 1)[0]

        self.assertEqual(
            [
                "explicit user constraints",
                "current source and current configuration",
                "active typed graph edges and current code logs",
                "observed runtime/incident evidence",
                "anchored semantic corrections",
                "verified experience",
                "advisory experience and episodes",
            ],
            [line.strip().removeprefix("-> ") for line in order.splitlines()],
        )
        self.assertIn("Current source can invalidate memory", authority)
        self.assertIn("Recency cannot override intent, status, confidence, counter-evidence", authority)
        self.assertIn("An absent graph edge is an evidence gap", authority)

    def test_install_preserves_every_direct_reference_and_section(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / ".agents" / "skills" / "agent-memory-query"
            with contextlib.redirect_stdout(io.StringIO()):
                copy_skill_dir(QUERY, installed, force=False)
            entry = (installed / "SKILL.md").read_text(encoding="utf-8")

            for original in sorted((QUERY / "references").glob("*.md")):
                relative = original.relative_to(QUERY)
                with self.subTest(reference=relative.as_posix()):
                    self.assertIn(relative.as_posix(), entry)
                    self.assertEqual(original.read_bytes(), (installed / relative).read_bytes())
            self.assertEqual((QUERY / "SKILL.md").read_bytes(), (installed / "SKILL.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
