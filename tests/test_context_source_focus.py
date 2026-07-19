# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from tools.agent_memory_runtime.context_source_excerpt import selected_ranges


class ContextSourceFocusTests(unittest.TestCase):
    def test_mechanism_complete_method_precedes_short_partial_methods(self) -> None:
        source = """class DocumentNavigationCoordinator {
  async warmCache(): Promise<void> {
    await this.cache.prepare()
  }

  updateLabel(label: string): void {
    this.label = label
  }

  resetIndicator(): void {
    this.loading = false
  }

  async navigateToEntry(entry: number): Promise<void> {
    this.requestedEntry = entry
    const content = await this.loader.load(entry)
    if (entry !== this.requestedEntry) {
      return
    }
    this.visibleContent = content
  }
}
"""
        ranges = [
            source_range("warmCache", 2, 4),
            source_range("updateLabel", 6, 8),
            source_range("resetIndicator", 10, 12),
            source_range("navigateToEntry", 14, 21),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "DocumentNavigationCoordinator.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": ranges},
                path,
                "Rapid document navigation renders stale content after repeated taps.",
            )

        self.assertEqual("navigateToEntry", selected[0]["symbol"])
        self.assertLessEqual(selected[0]["start_line"], 14)
        self.assertGreaterEqual(selected[0]["end_line"], 20)

    def test_file_anchor_descends_to_mechanism_complete_method(self) -> None:
        source = """export class FeedNavigationCoordinator {
  async prepare(): Promise<void> {
    await this.cache.load()
  }

  async openEntry(entry: number): Promise<void> {
    this.requestedEntry = entry
    const value = await this.loader.load(entry)
    this.visibleValue = value
  }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "FeedNavigationCoordinator.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": []},
                path,
                "连续快速跳转后出现陈旧内容，需要定位异步状态提交。",
            )

        self.assertEqual("openEntry", selected[0]["symbol"])
        self.assertGreaterEqual(selected[0]["end_line"], 9)

    def test_nested_arkui_callback_beats_outer_build_range(self) -> None:
        source = """@Entry
@Component
struct PlaybackSurface {
  @State lastX: number = 0

  build() {
    Stack() {}
      .onTouch((event: TouchEvent) => {
        const pointer = event.touches[0]
        this.lastX = pointer.x
      })
  }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PlaybackSurface.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": []},
                path,
                "The first finger is missing from an empty touch event.",
            )

        self.assertEqual("onTouch", selected[0]["symbol"])
        self.assertEqual(8, selected[0]["start_line"])
        self.assertEqual(11, selected[0]["end_line"])

    def test_builder_layout_range_is_selected_from_file_anchor(self) -> None:
        source = """@Entry
@Component
struct LibraryPage {
  build() {
    Column() {
      this.renderHeader()
      this.renderWorkStrip()
    }
  }

  @Builder
  renderWorkStrip() {
    List() {
      ForEach(this.works, (item: Work) => {
        ListItem() { WorkCard({ item: item }) }
      })
    }
    .listDirection(Axis.Horizontal)
    .height(160)
  }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "LibraryPage.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": []},
                path,
                "A horizontal list clips cards in its viewport.",
            )

        self.assertEqual("renderWorkStrip", selected[0]["symbol"])
        self.assertEqual(12, selected[0]["start_line"])
        self.assertGreaterEqual(selected[0]["end_line"], 20)

    def test_key_back_callback_beats_generic_build_range(self) -> None:
        source = """@Entry
@Component
struct ShortcutSearchPage {
  build() {
    Column() {
      TextInput()
        .onKeyEvent((event: KeyEvent) => {
          if (event.keyCode === KeyCode.KEYCODE_BACK) {
            return true
          }
          return false
        })
    }
  }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ShortcutSearchPage.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": []},
                path,
                "The physical keyboard back key conflicts with search input.",
            )

        self.assertEqual("onKeyEvent", selected[0]["symbol"])
        self.assertEqual(7, selected[0]["start_line"])
        self.assertGreaterEqual(selected[0]["end_line"], 12)

    def test_media_release_method_is_selected_for_intermittent_stop(self) -> None:
        source = """export class VoiceCaptureCoordinator {
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
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "VoiceCaptureCoordinator.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": []},
                path,
                "Voice recording intermittently stops after repeated capture sessions.",
            )

        self.assertEqual("stopCapture", selected[0]["symbol"])
        self.assertEqual(8, selected[0]["start_line"])
        self.assertGreaterEqual(selected[0]["end_line"], 11)

    def test_archive_method_can_replace_stale_anchor_range(self) -> None:
        source = """export class AssetArchiveInstaller {
  showUpgradeMessage(): void {
    this.status = 'upgrading'
  }

  async installBundle(context: UIContext): Promise<void> {
    const data = context.resourceManager.getRawFileContentSync('bundle.zip')
    const archive = fs.openSync(context.tempDir + '/bundle.zip', fs.OpenMode.CREATE)
    fs.writeSync(archive.fd, data.buffer)
    fs.closeSync(archive)
    await unzip(archive.path, context.filesDir)
  }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AssetArchiveInstaller.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": [source_range("showUpgradeMessage", 2, 4)]},
                path,
                "An existing temporary archive is reused during asset extraction.",
            )

        self.assertEqual("installBundle", selected[0]["symbol"])
        self.assertLessEqual(selected[0]["start_line"], 6)
        self.assertGreaterEqual(selected[0]["end_line"], 12)

    def test_collection_fold_method_is_selected(self) -> None:
        source = """export class SharedRecordCollector {
  collect(records: Record[]): string {
    let output = ''
    for (const record of records) {
      output = this.format(record)
    }
    return output
  }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SharedRecordCollector.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": []},
                path,
                "Combining multiple shared records preserves only the final item.",
            )

        self.assertEqual("collect", selected[0]["symbol"])
        self.assertGreaterEqual(selected[0]["end_line"], 8)

    def test_keyboard_focus_callback_method_is_selected(self) -> None:
        source = """export class DesktopEditorFocusController {
  attach(stage: WindowStage): void {
    stage.on('keyboardHeightChange', (height: number) => {
      this.editorFocusable = height > 0
    })
  }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "DesktopEditorFocusController.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": []},
                path,
                "Dismissing the software keyboard prevents the editor regaining focus.",
            )

        self.assertEqual("on", selected[0]["symbol"])
        self.assertGreaterEqual(selected[0]["end_line"], 5)

    def test_color_conversion_method_is_selected(self) -> None:
        source = """export class SystemBarColorAdapter {
  parseNativeColor(color: string): string {
    const values = color.trim().split(',').map(value => parseInt(value, 10))
    return '#' + values[0].toString(16)
  }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SystemBarColorAdapter.ets"
            path.write_text(source, encoding="utf-8")

            selected = selected_ranges(
                {"source_ranges": []},
                path,
                "Status bar color conversion returns an invalid opaque value.",
            )

        self.assertEqual("parseNativeColor", selected[0]["symbol"])
        self.assertGreaterEqual(selected[0]["end_line"], 5)

    def test_clipboard_extraction_method_is_selected(self) -> None:
        source = """export class ClipboardContentReader {
  async readPlainText(): Promise<string> {
    const board = pasteboard.getSystemPasteboard()
    const data = await board.getData()
    return data.getRecordAt(0).plainText ?? ''
  }
}
"""
        selected = select_from_source(
            "ClipboardContentReader.ets", source,
            "Pasting plain text returns empty despite clipboard content.",
        )

        self.assertEqual("readPlainText", selected[0]["symbol"])
        self.assertGreaterEqual(selected[0]["end_line"], 6)

    def test_permission_sequence_method_is_selected(self) -> None:
        source = """export class PermissionStartupCoordinator {
  async startSession(): Promise<void> {
    const result = await this.manager.requestPermissionsFromUser(this.context, [])
    if (result.authResults.some(value => value !== 0)) {
      return
    }
    await this.sessionService.start()
  }
}
"""
        selected = select_from_source(
            "PermissionStartupCoordinator.ets", source,
            "Startup begins before the permission request result is checked.",
        )

        self.assertEqual("startSession", selected[0]["symbol"])
        self.assertGreaterEqual(selected[0]["end_line"], 8)

    def test_output_reader_loop_method_is_selected(self) -> None:
        source = """export class ProcessOutputReader {
  readOutput(reader: LineReader): string {
    const lines: string[] = []
    let line = reader.readLine()
    while (line !== null) {
      lines.push(line)
      line = reader.readLine()
    }
    return lines.join('\\n')
  }
}
"""
        selected = select_from_source(
            "ProcessOutputReader.ets", source,
            "Command output is empty although the line reader has data.",
        )

        self.assertEqual("readOutput", selected[0]["symbol"])
        self.assertGreaterEqual(selected[0]["end_line"], 10)


def source_range(symbol: str, start: int, end: int) -> dict[str, object]:
    return {"symbol": symbol, "start_line": start, "end_line": end}


def select_from_source(name: str, source: str, query: str) -> list[dict[str, object]]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / name
        path.write_text(source, encoding="utf-8")
        return selected_ranges({"source_ranges": []}, path, query)


if __name__ == "__main__":
    unittest.main()
