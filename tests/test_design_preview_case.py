# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import queue
import json
import threading
import unittest
from dataclasses import FrozenInstanceError, replace

from tests.fixtures.design_preview.preview import PreviewCoordinator
from tests.fixtures.design_preview.renderers import render_json, render_text


def selected(text: str = "before") -> list[dict]:
    return [{"kind": "semantic", "id": 1, "text": text}]


class PreviewCaseTests(unittest.TestCase):
    def test_snapshot_does_not_follow_mutable_caller_input(self) -> None:
        owner = PreviewCoordinator()
        rows = selected()
        job = owner.request(rows)
        rows[0]["text"] = "changed"
        rows.append({"kind": "episode", "id": 2, "text": "extra"})
        self.assertEqual(1, len(job.rows))
        self.assertEqual("before", job.rows[0].text)
        with self.assertRaises(FrozenInstanceError):
            job.rows[0].text = "changed"

    def test_current_completion_publishes_its_rendered_snapshot(self) -> None:
        owner = PreviewCoordinator()
        job = owner.request(selected())
        self.assertTrue(owner.complete(job, render_text(job)))
        self.assertEqual("ready", owner.state.status)
        self.assertEqual("[semantic:1] before", owner.state.result.text)

    def test_late_old_completion_does_not_replace_the_new_result(self) -> None:
        owner = PreviewCoordinator()
        old = owner.request(selected("old"))
        current = owner.request(selected("current"))
        self.assertTrue(owner.complete(current, render_text(current)))
        state = owner.state
        self.assertFalse(owner.complete(old, render_text(old)))
        self.assertIs(state, owner.state)

    def test_cancelled_job_cannot_publish_even_after_a_worker_finishes(self) -> None:
        owner = PreviewCoordinator()
        job = owner.request(selected())
        self.assertTrue(owner.cancel(job))
        self.assertFalse(owner.complete(job, render_text(job)))
        self.assertFalse(owner.cancel(job))
        self.assertEqual("cancelled", owner.state.status)
        self.assertIsNone(owner.state.result)

    def test_duplicate_completion_is_ignored(self) -> None:
        owner = PreviewCoordinator()
        job = owner.request(selected())
        self.assertTrue(owner.complete(job, render_text(job)))
        self.assertFalse(owner.complete(job, render_text(job)))

    def test_another_instance_or_equal_looking_handle_cannot_commit(self) -> None:
        owner, other = PreviewCoordinator(), PreviewCoordinator()
        job, foreign = owner.request(selected()), other.request(selected())
        self.assertEqual(job.sequence, foreign.sequence)
        self.assertFalse(owner.complete(foreign, render_text(foreign)))
        self.assertFalse(owner.complete(replace(job), render_text(job)))
        self.assertTrue(owner.complete(job, render_text(job)))

    def test_current_failure_is_visible_and_a_later_job_can_recover(self) -> None:
        owner = PreviewCoordinator()
        job = owner.request(selected())
        self.assertTrue(owner.fail(job, "renderer failed"))
        self.assertEqual("failed", owner.state.status)
        self.assertEqual("renderer failed", owner.state.error)
        self.assertFalse(owner.complete(job, render_text(job)))
        next_job = owner.request(selected("recovered"))
        self.assertTrue(owner.complete(next_job, render_text(next_job)))
        self.assertIsNone(owner.state.error)

    def test_old_failure_does_not_clear_a_new_job(self) -> None:
        owner = PreviewCoordinator()
        old = owner.request(selected())
        current = owner.request(selected("current"))
        self.assertFalse(owner.fail(old, "late failure"))
        self.assertTrue(owner.complete(current, render_text(current)))

    def test_invalid_input_does_not_invalidate_an_existing_job(self) -> None:
        owner = PreviewCoordinator()
        current = owner.request(selected())
        for rows in ([], [{"kind": "semantic", "id": True, "text": "invalid"}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                owner.request(rows)
        self.assertTrue(owner.complete(current, render_text(current)))

    def test_over_limit_generator_stops_without_replacing_current_job(self) -> None:
        owner = PreviewCoordinator(max_rows=2)
        current = owner.request(selected())
        visited = []

        def rows():
            for number in range(1000):
                visited.append(number)
                yield {"kind": "episode", "id": number + 1, "text": "row"}

        with self.assertRaises(ValueError):
            owner.request(rows())
        self.assertEqual(3, len(visited))
        self.assertTrue(owner.complete(current, render_text(current)))

    def test_slow_render_does_not_block_new_admission_and_late_receipt_is_rejected(self) -> None:
        owner = PreviewCoordinator()
        old = owner.request(selected("old"))
        entered, release = threading.Event(), threading.Event()
        receipts: queue.Queue = queue.Queue()

        def worker():
            entered.set()
            if release.wait(3):
                receipts.put(owner.complete(old, render_text(old)))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            self.assertTrue(entered.wait(3))
            current = owner.request(selected("current"))
            self.assertTrue(owner.complete(current, render_text(current)))
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertFalse(receipts.get_nowait())
        self.assertEqual("[semantic:1] current", owner.state.result.text)

    def test_competing_receipts_accept_exactly_one_completion(self) -> None:
        owner = PreviewCoordinator()
        job = owner.request(selected())
        barrier = threading.Barrier(3, timeout=3)
        results: queue.Queue = queue.Queue()

        def worker():
            try:
                barrier.wait()
                results.put(owner.complete(job, render_text(job)))
            except Exception as error:
                results.put(error)

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(3)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        observed = [results.get_nowait() for _ in threads]
        self.assertEqual([False, True], sorted(observed))
        self.assertEqual("ready", owner.state.status)

    def test_json_format_preserves_unicode_and_composite_record_identity(self) -> None:
        owner = PreviewCoordinator()
        rows = [
            {"kind": "semantic", "id": 1, "text": "事实"},
            {"kind": "reflection", "id": 1, "text": "反思"},
        ]
        job = owner.request(rows)
        self.assertTrue(owner.complete(job, render_json(job)))
        self.assertEqual("application/json", owner.state.result.media_type)
        self.assertEqual(rows, json.loads(owner.state.result.text))

    def test_format_change_reuses_the_same_state_owner(self) -> None:
        owner = PreviewCoordinator()
        first = owner.request(selected())
        self.assertTrue(owner.complete(first, render_text(first)))
        second = owner.request(selected("next"))
        self.assertTrue(owner.complete(second, render_json(second)))
        self.assertEqual("next", json.loads(owner.state.result.text)[0]["text"])


if __name__ == "__main__":
    unittest.main()
