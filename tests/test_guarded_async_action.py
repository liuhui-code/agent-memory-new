# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.arkts_behavior_markers import (
    extract_arkts_behavior_markers,
)
from tools.agent_memory_runtime.query_behavior_concepts import (
    behavior_marker_terms,
)


class GuardedAsyncActionTests(unittest.TestCase):
    def test_repeat_submission_query_requests_complete_action_mechanisms(self) -> None:
        self.assertEqual(
            ["conditionalbranch", "statewrite", "asyncboundary"],
            behavior_marker_terms(
                "The action can be submitted twice; locate the pending state guard."
            ),
        )

    def test_ui_owner_exposes_complete_mechanism_while_service_does_not(self) -> None:
        page = """async retry(): Promise<void> {
  if (this.pending) {
    return
  }
  this.pending = true
  try {
    await RetryService.run()
  } finally {
    this.pending = false
  }
}
"""
        service = """async run(): Promise<void> {
  await Repository.save()
}
"""

        self.assertEqual(
            {"conditionalbranch", "statewrite", "asyncboundary"},
            set(extract_arkts_behavior_markers(page))
            & {"conditionalbranch", "statewrite", "asyncboundary"},
        )
        self.assertEqual(
            {"asyncboundary"},
            set(extract_arkts_behavior_markers(service))
            & {"conditionalbranch", "statewrite", "asyncboundary"},
        )


if __name__ == "__main__":
    unittest.main()
