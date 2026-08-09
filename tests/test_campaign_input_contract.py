# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.campaign_input_contract import (
    bind_campaign_input,
    require_campaign_input,
)
from tests.test_prospective_cohort_contract import protocol


class CampaignInputContractTests(unittest.TestCase):
    def test_real_protocol_requires_verified_campaign_input(self) -> None:
        with self.assertRaisesRegex(SystemExit, "verified campaign input"):
            require_campaign_input(protocol("prospective_real_tasks"))

    def test_binding_redacts_manifest_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            memory_home = Path(directory) / "memory"
            root.mkdir()
            manifest_path = Path(directory) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest(root, memory_home)), encoding="utf-8")

            bound = bind_campaign_input(
                protocol("prospective_real_tasks"), manifest_path, root, memory_home,
            )

        binding = bound["campaign_input"]
        self.assertEqual("verified", binding["status"])
        self.assertEqual(64, len(binding["manifest_digest"]))
        rendered = json.dumps(bound, sort_keys=True)
        self.assertNotIn(str(root), rendered)
        self.assertNotIn("project-owner-secret", rendered)


def manifest(root: Path, memory_home: Path) -> dict:
    return {
        "schema_version": "campaign-source-manifest/v1",
        "status": "confirmed",
        "campaign_id": "pilot-001",
        "project": {
            "local_path": str(root),
            "project_owner_role": "project-owner-secret",
            "source_revision_policy": "clean_revision_required",
        },
        "task_stream": {
            "source_description": "future issue queue",
            "continuity_owner_role": "queue-owner",
            "starts_at": "2026-08-09T00:00:00Z",
        },
        "memory": {"task_start_memory_home": str(memory_home)},
        "verification": {"allowed_methods": ["test"]},
        "raw_task_custody": {"outside_sqlite_location": "controlled", "retention_days": 30},
        "cohort": {
            "fixed_presented_count": 2,
            "allowed_exclusion_reasons": ["not_diagnosis", "duplicate_task"],
            "optional_stopping": False,
            "dirty_task_policy": "natural_observation_only",
        },
        "paired_replay": {"candidate_policy": "first_eligible_clean_revision_only"},
        "runner": {"frozen_source_context_sharing_authorized": True},
        "claims": {"feasibility_only": True, "no_generalization_or_promotion_claim": True},
    }


if __name__ == "__main__":
    unittest.main()
