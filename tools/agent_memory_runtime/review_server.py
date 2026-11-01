# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Foreground, loopback-only human review UI under the existing Runtime entry."""

from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .models import Project
from .review_actions import apply_action
from .review_library import ReviewError, browse, detail, overview
from .storage import resolve_project

ASSETS = Path(__file__).with_name("review_web")
MAX_BODY = 65536


def make_server(project: Project, port: int) -> ThreadingHTTPServer:
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "AgentMemoryReview/1"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, format: str, *args: object) -> None:
            # Do not persist searches, record contents or session credentials in access logs.
            pass

        def send(self, status: int, data: bytes, content_type: str = "application/json; charset=utf-8") -> None:
            self.send_response(status)
            for key, value in {
                "Content-Type": content_type, "Content-Length": str(len(data)), "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY", "Cross-Origin-Resource-Policy": "same-origin",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; "
                    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            }.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def json_response(self, status: int, value: object) -> None:
            self.send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"))

        def guard(self, *, write: bool = False) -> None:
            expected_host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != expected_host:
                raise ReviewError("仅允许当前本机地址访问。", 403)
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{expected_host}":
                raise ReviewError("拒绝跨站请求。", 403)
            if self.headers.get("Sec-Fetch-Site") not in {None, "same-origin", "none"}:
                raise ReviewError("拒绝跨站请求。", 403)
            if write and not secrets.compare_digest(self.headers.get("X-Review-Token", ""), token):
                raise ReviewError("会话已失效，请刷新页面。", 403)

        def dispatch(self, *, write: bool = False) -> None:
            try:
                self.guard(write=write)
                parsed = urlsplit(self.path)
                if write:
                    if parsed.path != "/api/actions" or parsed.query:
                        raise ReviewError("接口不存在。", 404)
                    if self.headers.get_content_type() != "application/json" or self.headers.get("Transfer-Encoding"):
                        raise ReviewError("请求必须为 JSON。", 415)
                    try:
                        size = int(self.headers.get("Content-Length", "0"))
                    except ValueError:
                        raise ReviewError("无效的请求长度。") from None
                    if not 0 < size <= MAX_BODY:
                        raise ReviewError("请求内容过大或为空。", 413)
                    payload = json.loads(self.rfile.read(size))
                    if not isinstance(payload, dict):
                        raise ReviewError("请求必须为 JSON 对象。")
                    self.json_response(200, apply_action(project, payload))
                    return
                if parsed.path == "/api/session":
                    self.json_response(200, {"token": token, **overview(project)})
                elif parsed.path == "/api/records":
                    params = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=12)
                    self.json_response(200, browse(project, {key: values[-1] for key, values in params.items()}))
                elif parsed.path.startswith("/api/records/"):
                    parts = parsed.path.split("/")
                    if len(parts) != 5:
                        raise ReviewError("接口不存在。", 404)
                    self.json_response(200, detail(project, parts[3], int(parts[4])))
                else:
                    assets = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                              "/style.css": ("style.css", "text/css")}
                    if parsed.path not in assets:
                        raise ReviewError("页面不存在。", 404)
                    name, mime = assets[parsed.path]
                    self.send(200, (ASSETS / name).read_bytes(), mime + "; charset=utf-8")
            except ReviewError as error:
                self.json_response(error.status, {"error": str(error)})
            except (ValueError, TypeError, UnicodeError):
                self.json_response(400, {"error": "请求格式不正确。"})
            except sqlite3.Error:
                self.json_response(503, {"error": "记忆库正忙或结构不兼容。请稍后刷新，必要时运行 doctor。"})
            except OSError:
                self.json_response(503, {"error": "无法读取界面或保存备份，本次操作未完成。请检查磁盘与权限。"})

        def do_GET(self) -> None:
            self.dispatch()

        def do_POST(self) -> None:
            self.dispatch(write=True)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def review_ui(args: argparse.Namespace) -> None:
    if not 0 <= args.port <= 65535:
        raise SystemExit("--port must be between 0 and 65535")
    project = resolve_project(args.project, args.memory_home)
    try:
        overview(project)  # No initialization, migrations or data writes on launch.
        server = make_server(project, args.port)
    except (ReviewError, sqlite3.Error, OSError) as error:
        raise SystemExit(f"Cannot open review UI: {error}") from None
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Memory review: {url}\nProject: {project.root}\nDatabase: {project.db_path}\nStop: Ctrl+C", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nMemory review stopped.", file=sys.stderr)
    finally:
        server.server_close()
