# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.arkts_behavior_markers import (
    extract_arkts_behavior_markers,
)
from tools.agent_memory_runtime.code_wiki_extractors import summarize_file


class ArktsBehaviorMarkerTests(unittest.TestCase):
    def test_fallback_repository_selection_is_normalized(self) -> None:
        source = """
export class TransportRegistry {
  private repository: DeviceRepository = new RemoteDeviceRepository()

  selectRepository(online: boolean): void {
    if (online) {
      this.repository = new RemoteDeviceRepository()
    } else {
      this.repository = new DemoDeviceRepository()
    }
  }
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertIn("fallbackbranch", markers)
        self.assertIn("repositoryboundary", markers)
        self.assertIn("statewrite", markers)

    def test_callback_deserialization_boundary_is_normalized(self) -> None:
        source = """
export class TelemetryGateway {
  async attach(): Promise<void> {
    this.client.onPayload((raw: string) => {
      const event = JSON.parse(raw)
      this.accept(event)
    })
  }
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertTrue(
            {"asyncboundary", "callbackboundary", "deserialization"}
            <= set(markers)
        )

    def test_action_and_refresh_state_owners_are_normalized(self) -> None:
        source = """
export class LightingStore {
  @State current: LightState = new LightState()
  private repository: LightingRepository

  async runCommand(command: LightCommand): Promise<void> {
    await this.repository.executeAction(command)
  }

  async refreshState(): Promise<void> {
    this.current = await this.repository.loadCurrent()
  }
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertTrue(
            {"actiondispatch", "lifecyclesync", "repositoryboundary", "statewrite"}
            <= set(markers)
        )

    def test_event_state_handoff_is_normalized(self) -> None:
        source = """
export class WorkspaceSelectionController {
  private selectedId: string = ''
  private selectedSchema: string = ''

  onEditRequested(row: WorkspaceRow): void {
    this.selectedId = row.id
    this.selectedSchema = row.schema
    this.openEditPanel()
  }
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertTrue(
            {"eventboundary", "statehandoff", "statewrite"} <= set(markers)
        )

    def test_validation_exit_is_normalized_without_plain_branch_noise(self) -> None:
        guarded = """
saveAccount(): void {
  if (this.displayName.trim().length === 0) {
    promptAction.showToast({ message: 'Required name' })
    return
  }
  this.dispatchUpdate()
}
"""
        plain_branch = """
chooseTheme(dark: boolean): string {
  if (dark) {
    return 'black'
  }
  return 'white'
}
"""

        self.assertIn("validationguard", extract_arkts_behavior_markers(guarded))
        self.assertNotIn("validationguard", extract_arkts_behavior_markers(plain_branch))

    def test_persistence_write_is_normalized_at_storage_boundary(self) -> None:
        source = """
async recordSuccessfulUse(session: SessionRecord): Promise<void> {
  session.usageCount += 1
  session.lastUsedAt = Date.now()
  await this.sessionStore.save(session)
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertIn("persistencewrite", markers)
        self.assertIn("countertimestampwrite", markers)

    def test_gesture_callback_is_normalized_without_inventing_state_write(self) -> None:
        source = """
build() {
  Stack() {}
    .gesture(
      PanGesture().onActionUpdate((event: GestureEvent) => {
        this.boardEngine.shift(event.offsetX, event.offsetY)
      })
    )
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertIn("gestureboundary", markers)
        self.assertNotIn("statewrite", markers)

    def test_event_indexed_collection_write_is_normalized(self) -> None:
        source = """
onSeatTapped(index: number): void {
  this.seats[index].selected = !this.seats[index].selected
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertTrue(
            {"eventboundary", "collectionwrite"} <= set(markers)
        )

    def test_restore_state_and_persistence_form_complete_lifecycle_owner(self) -> None:
        source = """
aboutToAppear(): void {
  this.restoreDraft()
}

async restoreDraft(): Promise<void> {
  this.draftText = await this.draftPreferences.load()
}

async saveDraft(): Promise<void> {
  await this.draftPreferences.save(this.draftText)
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertTrue(
            {"lifecyclesync", "statewrite", "persistencewrite"} <= set(markers)
        )

    def test_touch_index_access_is_normalized_inside_dsl_callback(self) -> None:
        source = """
build() {
  Stack() {}
    .onTouch((event: TouchEvent) => {
      const pointer = event.touches[0]
      this.lastX = pointer.x
    })
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertTrue({"touchboundary", "indexedread"} <= set(markers))

    def test_list_axis_values_remain_distinguishable(self) -> None:
        horizontal = "List() {}.listDirection(Axis.Horizontal)"
        vertical = "List() {}.listDirection(Axis.Vertical)"

        self.assertIn(
            "horizontalaxis", extract_arkts_behavior_markers(horizontal)
        )
        self.assertIn("verticalaxis", extract_arkts_behavior_markers(vertical))

    def test_async_request_identity_guard_is_normalized(self) -> None:
        source = """
async openEntry(entry: number): Promise<void> {
  this.requestedEntry = entry
  const value = await this.loader.load(entry)
  if (entry !== this.requestedEntry) {
    return
  }
  this.visibleValue = value
}
"""

        self.assertIn("orderingguard", extract_arkts_behavior_markers(source))

    def test_conditional_data_source_and_lifecycle_cleanup_are_normalized(self) -> None:
        conditional = """
async loadCollection(folderId: string): Promise<void> {
  if (folderId.length > 0) {
    this.items = await this.mediaSource.getAssets(folderId)
  }
}
"""
        cleanup = """
onWindowStageDestroy(): void {
  this.windowRegistry.unregisterWindowCallback(this.callback)
}
"""

        self.assertTrue(
            {"conditionalbranch", "datasourceboundary"}
            <= set(extract_arkts_behavior_markers(conditional))
        )
        self.assertTrue(
            {"lifecycleboundary", "callbackcleanup"}
            <= set(extract_arkts_behavior_markers(cleanup))
        )

    def test_arkts_file_summary_persists_bounded_behavior_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "TelemetryGateway.ets"
            path.write_text(
                "export class TelemetryGateway {\n"
                "  async attach() {\n"
                "    this.socket.onPayload((raw: string) => JSON.parse(raw))\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            summary = summarize_file(path, "ArkTS")

        self.assertIn("behavior: ", summary)
        self.assertIn("callbackboundary", summary)
        self.assertIn("deserialization", summary)

    def test_arkts_file_summary_persists_component_identifier_terms(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MessageRow.ets"
            path.write_text(
                "@Component\nexport struct MessageRow { build() {} }\n",
                encoding="utf-8",
            )

            summary = summarize_file(path, "ArkTS")

        self.assertIn("component terms: message, row", summary)

    def test_page_component_does_not_add_broad_identifier_terms(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "NotificationDetailsPage.ets"
            path.write_text(
                "@Component\nstruct NotificationDetailsPage { build() {} }\n",
                encoding="utf-8",
            )

            summary = summarize_file(path, "ArkTS")

        self.assertNotIn("component terms:", summary)

    def test_reusable_toolbar_role_is_normalized_from_component_identity(self) -> None:
        source = """
@Component
export struct NavigationToolbar {
  build() { Row() {} }
}
"""

        self.assertIn("toolbarrole", extract_arkts_behavior_markers(source))
        self.assertNotIn(
            "toolbarrole",
            extract_arkts_behavior_markers(
                "@Component\nexport struct MessageActionBar { build() {} }"
            ),
        )

    def test_media_resource_acquire_and_release_are_normalized(self) -> None:
        source = """
export class VoiceCaptureCoordinator {
  private audioCapturer: AudioCapturer

  async startCapture(): Promise<void> {
    await this.audioCapturer.start()
  }

  async stopCapture(): Promise<void> {
    await this.audioCapturer.stop()
    await this.audioCapturer.release()
  }
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertTrue(
            {"resourceacquire", "resourcerelease", "asyncboundary"}
            <= set(markers)
        )

    def test_key_event_and_back_guard_are_normalized_in_dsl_callback(self) -> None:
        source = """
TextInput()
  .onKeyEvent((event: KeyEvent) => {
    if (event.keyCode === KeyCode.KEYCODE_BACK) {
      return true
    }
    return false
  })
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertTrue({"keyboundary", "backkeyguard"} <= set(markers))

    def test_archive_write_and_extract_form_io_boundary(self) -> None:
        source = """
async installBundle(context: UIContext): Promise<void> {
  const data = context.resourceManager.getRawFileContentSync('bundle.zip')
  const archive = fs.openSync(context.tempDir + '/bundle.zip', fs.OpenMode.CREATE)
  fs.writeSync(archive.fd, data.buffer)
  fs.closeSync(archive)
  await unzip(archive.path, context.filesDir)
}
"""

        self.assertIn("archiveioboundary", extract_arkts_behavior_markers(source))

    def test_collection_fold_requires_iteration_and_scalar_assignment(self) -> None:
        owner = """
collect(records: Record[]): string {
  let output = ''
  for (const record of records) {
    output = this.format(record)
  }
  return output
}
"""
        consumer = "render(value: string): void { this.preview = value }"

        self.assertIn("collectionfold", extract_arkts_behavior_markers(owner))
        self.assertNotIn("collectionfold", extract_arkts_behavior_markers(consumer))

    def test_keyboard_visibility_and_focus_state_are_distinguishable(self) -> None:
        source = """
attach(stage: WindowStage): void {
  stage.on('keyboardHeightChange', (height: number) => {
    this.editorFocusable = height > 0
  })
}
"""

        markers = extract_arkts_behavior_markers(source)

        self.assertTrue({"keyboardvisibility", "focusstate"} <= set(markers))

    def test_color_parser_requires_conversion_operations(self) -> None:
        parser = """
parseNativeColor(color: string): string {
  const values = color.trim().split(',').map(value => parseInt(value, 10))
  return '#' + values[0].toString(16)
}
"""
        setter = "setStatusBarColor(color: string): void { this.color = color }"

        self.assertIn("colorparser", extract_arkts_behavior_markers(parser))
        self.assertNotIn("colorparser", extract_arkts_behavior_markers(setter))

    def test_clipboard_record_extraction_requires_runtime_api_calls(self) -> None:
        owner = """
async readPlainText(): Promise<string> {
  const board = pasteboard.getSystemPasteboard()
  const data = await board.getData()
  return data.getRecordAt(0).plainText ?? ''
}
"""
        metadata = 'requestPermissions: ["ohos.permission.READ_PASTEBOARD"]'

        self.assertIn("clipboardread", extract_arkts_behavior_markers(owner))
        self.assertNotIn("clipboardread", extract_arkts_behavior_markers(metadata))

    def test_permission_sequence_requires_request_and_result_guard(self) -> None:
        owner = """
async startSession(): Promise<void> {
  const result = await this.accessManager.requestPermissionsFromUser(
    this.context, ['ohos.permission.MICROPHONE'])
  if (result.authResults.some(value => value !== 0)) {
    return
  }
  await this.sessionService.start()
}
"""
        request_only = "await manager.requestPermissionsFromUser(context, permissions)"

        markers = extract_arkts_behavior_markers(owner)
        self.assertTrue({"permissionrequest", "permissionguard"} <= set(markers))
        self.assertNotIn(
            "permissionguard", extract_arkts_behavior_markers(request_only)
        )

    def test_output_read_loop_requires_iteration_and_reader_call(self) -> None:
        owner = """
readOutput(reader: LineReader): string {
  const lines: string[] = []
  let line = reader.readLine()
  while (line !== null) {
    lines.push(line)
    line = reader.readLine()
  }
  return lines.join('\\n')
}
"""
        label = "Text('Output reader loop')"

        self.assertIn("outputreadloop", extract_arkts_behavior_markers(owner))
        self.assertNotIn("outputreadloop", extract_arkts_behavior_markers(label))

    def test_runtime_capability_probe_excludes_manifest_declarations(self) -> None:
        owner = """
async supportsShareExtension(): Promise<boolean> {
  const info = await bundleManager.getBundleInfoForSelf(
    bundleManager.BundleFlag.GET_BUNDLE_INFO_WITH_EXTENSION_ABILITY)
  return info.extensionAbilityInfo.length > 0
}
"""
        manifest = '{ "extensionAbilities": [{ "name": "ShareExtension" }] }'

        self.assertIn("runtimecapability", extract_arkts_behavior_markers(owner))
        self.assertNotIn("runtimecapability", extract_arkts_behavior_markers(manifest))


if __name__ == "__main__":
    unittest.main()
