# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import http.client
import json
import subprocess
import sys
import threading
import unittest
from pathlib import Path

from tests.test_review_library import ReviewFixture
from tools.agent_memory_runtime.review_server import make_server

REPO = Path(__file__).resolve().parents[1]


class ReviewServerTests(ReviewFixture):
    def setUp(self) -> None:
        super().setUp()
        self.seed()
        self.server = make_server(self.project, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.host = f"127.0.0.1:{self.server.server_port}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, path="/api/session", method="GET", payload=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        try:
            body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            raw = response.read()
            return response.status, dict(response.getheaders()), raw
        finally:
            conn.close()

    def test_only_bundled_assets_are_served_with_security_headers(self) -> None:
        for path in ("/", "/app.js", "/style.css"):
            status, headers, body = self.request(path)
            self.assertEqual(200, status)
            self.assertTrue(body)
            self.assertEqual("no-store", headers["Cache-Control"])
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            self.assertNotIn("Access-Control-Allow-Origin", headers)
        for path in ("/../storage.py", "/%2e%2e/storage.py", "/memory.db", "/api/anything"):
            self.assertEqual(404, self.request(path)[0])

    def test_host_and_cross_origin_reads_are_rejected(self) -> None:
        for headers in ({"Host": "evil.example"}, {"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(403, self.request(headers=headers)[0])

    def test_write_requires_token_json_and_same_origin(self) -> None:
        payload = {"action": "archive", "records": [self.selected()]}
        self.assertEqual(403, self.request("/api/actions", "POST", payload)[0])
        token = json.loads(self.request()[2])["token"]
        headers = {"X-Review-Token": token, "Content-Type": "application/json", "Origin": f"http://{self.host}"}
        self.assertEqual(403, self.request("/api/actions", "POST", payload, {**headers, "Origin": "null"})[0])
        self.assertEqual(415, self.request("/api/actions", "POST", payload, {**headers, "Content-Type": "text/plain"})[0])
        status, _, raw = self.request("/api/actions", "POST", payload, headers)
        self.assertEqual(200, status)
        self.assertEqual(1, json.loads(raw)["changed"])

    def test_list_detail_and_conflict_use_json_responses(self) -> None:
        self.assertEqual(4, json.loads(self.request("/api/records?kind=semantic&limit=1")[2])["total"])
        self.assertEqual("semantic", json.loads(self.request("/api/records/semantic/1")[2])["kind"])
        token = json.loads(self.request()[2])["token"]
        headers = {"X-Review-Token": token, "Content-Type": "application/json"}
        payload = {"action": "archive", "records": [self.selected()]}
        self.assertEqual(200, self.request("/api/actions", "POST", payload, headers)[0])
        self.assertEqual(409, self.request("/api/actions", "POST", payload, headers)[0])

    def test_malformed_and_oversized_requests_fail_closed(self) -> None:
        token = json.loads(self.request()[2])["token"]
        headers = {"X-Review-Token": token, "Content-Type": "application/json"}
        self.assertEqual(400, self.request("/api/actions", "POST", ["bad"], headers)[0])
        self.assertEqual(413, self.request("/api/actions", "POST", {"huge": "x" * 66000}, headers)[0])
        for path in ("/api/records?limit=200", "/api/records?cursor=bad", "/api/records/semantic/not-an-id"):
            self.assertEqual(400, self.request(path)[0])
        self.assertEqual(404, self.request("/api/records/semantic/999999")[0])


class InstalledReviewTests(ReviewFixture):
    def test_normal_search_respects_archive_restore_and_permanent_delete(self) -> None:
        self.seed()
        command = [sys.executable, str(REPO / "tools/agent_memory.py"), "search", "--project", str(self.project.root),
                   "--memory-home", str(self.project.memory_home), "--query", "中文事实", "--json"]

        def found() -> set[int]:
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
            return {row["id"] for row in json.loads(result.stdout)["semantic_facts"]}

        self.assertIn(1, found())
        self.action("archive")
        self.assertNotIn(1, found())
        self.action("restore")
        self.assertIn(1, found())
        self.action("archive")
        self.action("delete", confirmation="永久删除")
        self.assertNotIn(1, found())
        self.assertEqual({2, 3, 4}, found())

    def test_installed_runtime_carries_assets_and_preserves_context_protocol(self) -> None:
        self.seed()
        project, memory = str(self.project.root), str(self.project.memory_home)
        result = subprocess.run([sys.executable, str(REPO / "install.py"), "--project", project,
                                 "--memory-home", memory], capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        runtime = self.project.root / "tools" / "agent_memory.py"
        assets = runtime.parent / "agent_memory_runtime" / "review_web"
        self.assertEqual({"index.html", "style.css", "app.js"}, {path.name for path in assets.iterdir()})
        result = subprocess.run([sys.executable, str(runtime), "review-ui", "--help"],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("--open", result.stdout)
        command = [sys.executable, str(runtime), "context", "--project", project, "--memory-home", memory,
                   "--query", "中文事实", "--compact", "--json"]
        before = json.loads(subprocess.run(command, capture_output=True, text=True, check=True, timeout=30).stdout)
        self.action("archive")
        after = json.loads(subprocess.run(command, capture_output=True, text=True, check=True, timeout=30).stdout)
        self.assertIn("query_handoff", before)
        self.assertEqual(set(before), set(after))
        # Query corpus can change through intentional archival; the handoff contract does not.
        self.assertEqual(set(before["query_handoff"]), set(after["query_handoff"]))


if __name__ == "__main__":
    unittest.main()
