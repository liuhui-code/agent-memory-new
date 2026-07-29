# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_behavior_concepts import behavior_marker_terms


class CallableBehaviorHintTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()
        self.source = self.root / "src" / "WorkflowPage.ets"
        self.source.parent.mkdir()
        self.source.write_text(SOURCE, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_lifecycle_activation_beats_lexical_event_name(self) -> None:
        payload = self.context(
            "The busy overlay opens but the spinner is not rotating. "
            "Locate the component lifecycle expression that starts the animation."
        )
        anchor = payload["query_handoff"]["code_anchors"][0]

        self.assertEqual("aboutToAppear", anchor["symbol"])
        self.assertEqual(5, anchor["source_ranges"][0]["start_line"])

    def test_state_branch_beats_renderer_call_site(self) -> None:
        payload = self.context(
            "After switching sections, the view renders a reused selection. "
            "Locate the page owner that chooses which section content appears."
        )
        anchor = payload["query_handoff"]["code_anchors"][0]

        self.assertEqual("renderSection", anchor["symbol"])
        self.assertEqual(26, anchor["source_ranges"][0]["start_line"])

    def test_guarded_recurring_work_beats_status_only_match(self) -> None:
        expected = {"deferredexecution", "statebranch", "stateread"}
        self.assertTrue(expected <= set(behavior_marker_terms(
            "A recurring job schedules a second timer after recovery."
        )))

        payload = self.context(
            "A recurring job schedules another timer after recovery. Locate the "
            "routine that prevents the second schedule before publishing its snapshot."
        )
        anchors = payload["query_handoff"]["code_anchors"]

        self.assertEqual("scheduleRefresh", anchors[0]["symbol"])
        self.assertEqual(1, len(anchors))

    def test_guarded_state_selection_beats_summary_click(self) -> None:
        expected = {"statebranch", "stateread", "statewrite", "persistencewrite"}
        self.assertTrue(expected <= set(behavior_marker_terms(
            "Choosing an active workspace should update it only when it changes."
        )))

        payload = self.context(
            "Choosing a workspace should update the active workspace only when "
            "it changes, then persist that selection."
        )
        anchors = payload["query_handoff"]["code_anchors"]

        self.assertEqual("chooseWorkspace", anchors[0]["symbol"])
        self.assertEqual(1, len(anchors))

    def test_guarded_async_persistence_beats_storage_description(self) -> None:
        expected = {"asyncboundary", "guardreturn", "stateread", "persistencewrite"}
        self.assertTrue(expected <= set(behavior_marker_terms(
            "Blank input is ignored; persist a trimmed profile draft name."
        )))

        payload = self.context(
            "Blank input is ignored; persist the trimmed profile draft name. "
            "Locate the asynchronous callable that guards and writes it."
        )
        anchors = payload["query_handoff"]["code_anchors"]

        self.assertEqual("commitDraft", anchors[0]["symbol"])
        self.assertEqual(1, len(anchors))

    def context(self, query: str) -> dict:
        self.run_memory(self.root, "init")
        self.run_memory(self.root, "wiki-index")
        return json.loads(self.run_memory(
            self.root, "context", "--compact", "--query", query, "--json"
        ).stdout)


SOURCE = """@CustomDialog
struct DeferredSpinnerDialog {
  @State rotateAngle: number = 0

  aboutToAppear(): void {
    setTimeout(() => {
      this.rotateAngle = 360
    }, 80)
  }
}

export const BusyOverlayEvent = 'busy overlay loading dialog'

function openBusyOverlay(): string {
  return BusyOverlayEvent
}

@Component
struct WorkflowPage {
  @State activeSection: string = 'saved'

  build() {
    this.renderSection()
  }

  renderSection() {
    if (this.activeSection === 'saved') {
      Text('Saved collection')
    } else {
      Text('Recent collection')
    }
  }
}

class RefreshCoordinator {
  private refreshTimer?: number

  scheduleRefresh() {
    if (this.refreshTimer !== undefined) {
      return
    }
    this.refreshTimer = setInterval(() => this.publishSnapshot(), 1000)
  }

  publishSnapshot() {}
}

function renderRefreshStatus() {
  return 'refresh status rendered'
}

class WorkspaceController {
  private activeWorkspace: string = 'overview'

  chooseWorkspace(nextWorkspace: string) {
    if (this.activeWorkspace === nextWorkspace) {
      return
    }
    this.activeWorkspace = nextWorkspace
    WorkspaceStore.saveActive(nextWorkspace)
  }
}

function showWorkspaceSummary() {
  return 'workspace selected'
}

class ProfileDraftViewModel {
  private draftName: string = ''

  async commitDraft() {
    const name = this.draftName.trim()
    if (!name) {
      return
    }
    this.store.saveDraft(name)
  }
}

function describeDraftStorage() {
  return 'draft storage information'
}
"""
