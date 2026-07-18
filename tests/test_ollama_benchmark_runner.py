# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from examples.ollama_benchmark_runner import run_request, validate_ollama_host


class OllamaBenchmarkRunnerTests(unittest.TestCase):
    def test_loopback_runner_keeps_excerpts_and_executes_source_tools(self) -> None:
        with tempfile.TemporaryDirectory() as directory, fake_ollama() as server:
            root = Path(directory)
            workspace = root / "workspace"
            source = workspace / "src" / "Cause.ets"
            source.parent.mkdir(parents=True)
            source.write_text("export function cause() { return 'broken' }\n", encoding="utf-8")
            query = root / "memory-query"
            query.write_text(memory_query_script(), encoding="utf-8")
            query.chmod(0o755)

            result = run_request(
                benchmark_request(workspace, query),
                host=server.url,
                model="qwen3-coder:local",
                timeout=5,
            )

            self.assertEqual("agent-benchmark-response/v1", result["schema_version"])
            self.assertEqual(["src/Cause.ets"], result["predicted_files"])
            self.assertEqual(
                ["src/Cause.ets", "src/Unopened.ets"],
                result["investigated_files"],
            )
            self.assertEqual(1, result["source_read_count"])
            self.assertEqual(1, result["source_file_count"])
            self.assertEqual(1, result["command_count"])
            self.assertEqual(30, result["model_input_tokens"])
            self.assertEqual(15, result["model_output_tokens"])
            self.assertTrue(result["cost_metrics_reported"])
            self.assertGreater(result["memory_context_bytes"], 0)
            self.assertEqual("local_process", result["runner_metadata"]["source_boundary"])
            self.assertEqual("full", result["runner_metadata"]["source_excerpt_delivery"])
            self.assertTrue(any("local-only-source-body" in value for value in server.prompts))
            self.assertTrue(any(message.get("role") == "tool" for message in server.messages))
            self.assertTrue(all(request.get("think") is False for request in server.requests))
            self.assertEqual(
                [256, 256, 512],
                [request["options"]["num_predict"] for request in server.requests],
            )

    def test_runner_rejects_non_loopback_hosts(self) -> None:
        with self.assertRaisesRegex(SystemExit, "loopback"):
            validate_ollama_host("https://models.example.com")

    def test_runner_requires_installed_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory, fake_ollama() as server:
            workspace = Path(directory)
            with self.assertRaisesRegex(SystemExit, "not installed"):
                run_request(
                    benchmark_request(workspace, None, variant="baseline"),
                    host=server.url,
                    model="missing:latest",
                    timeout=5,
                )


def benchmark_request(
    workspace: Path,
    query: Path | None,
    variant: str = "memory",
) -> dict:
    request = {
        "schema_version": "agent-benchmark-request/v1",
        "case_id": "local-case",
        "variant": variant,
        "trial_index": 1,
        "workspace": str(workspace),
        "case": {
            "id": "local-case",
            "task_type": "diagnosis",
            "task": {"description": "Find the broken cause.", "constraints": []},
        },
        "instructions": ["Inspect only the supplied workspace."],
        "response_schema": {},
    }
    if query is not None:
        request["memory_access"] = {
            "query_command": [str(query), "<task-description>"],
        }
    return request


def memory_query_script() -> str:
    return """#!/usr/bin/env python3
import json
print(json.dumps({
    "query_handoff": {
        "source_excerpt_policy": {"source": "current_worktree"},
        "source_exploration": {"limits": {}},
        "code_anchors": [{
            "file_path": "src/Cause.ets",
            "role": "primary",
            "source_excerpts": [{
                "symbol": "cause",
                "start_line": 1,
                "end_line": 1,
                "content": "local-only-source-body",
                "source": "current_worktree",
                "truncated": False
            }]
        }]
    }
}))
"""


class FakeOllamaHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_GET(self) -> None:
        if self.path == "/api/version":
            self.respond({"version": "0.test"})
            return
        if self.path == "/api/tags":
            self.respond({"models": [{"name": "qwen3-coder:local"}]})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        self.requests.append(request)
        index = len(self.requests)
        if index == 1:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "read_source",
                        "arguments": {"path": "src/Cause.ets", "start_line": 1, "end_line": 1},
                    }
                }],
            }
        elif index == 2:
            message = {"role": "assistant", "content": "Evidence collected."}
        else:
            message = {"role": "assistant", "content": json.dumps(final_result())}
        self.respond({
            "model": "qwen3-coder:local",
            "message": message,
            "done": True,
            "prompt_eval_count": 10,
            "eval_count": 5,
        })

    def log_message(self, *_args) -> None:
        return

    def respond(self, value: dict) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def final_result() -> dict:
    return {
        "schema_version": "agent-benchmark-response/v1",
        "case_id": "local-case",
        "variant": "memory",
        "trial_index": 1,
        "root_cause_category": "state",
        "predicted_files": ["src/Cause.ets"],
        "supporting_files": ["src/Unopened.ets"],
        "investigated_files": ["src/Cause.ets"],
        "causal_level": "supported",
        "verification_status": "unknown",
        "query_rounds": 1,
        "source_search_count": 0,
        "expansion_trace": [],
        "stop_reason": "supported_cause_found",
        "evidence_basis": "direct_source_mechanism",
        "mechanism_evidence_files": ["src/Cause.ets"],
        "token_estimate": 0,
        "elapsed_ms": 0,
        "summary": "The source branch returns the broken value.",
    }


class FakeOllama:
    def __enter__(self):
        FakeOllamaHandler.requests = []
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllamaHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        return self

    @property
    def prompts(self) -> list[str]:
        return [
            str(message.get("content") or "")
            for request in FakeOllamaHandler.requests
            for message in request.get("messages") or []
            if message.get("role") == "user"
        ]

    @property
    def messages(self) -> list[dict]:
        return [
            message
            for request in FakeOllamaHandler.requests
            for message in request.get("messages") or []
        ]

    @property
    def requests(self) -> list[dict]:
        return FakeOllamaHandler.requests

    def __exit__(self, *_args) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


def fake_ollama() -> FakeOllama:
    return FakeOllama()
