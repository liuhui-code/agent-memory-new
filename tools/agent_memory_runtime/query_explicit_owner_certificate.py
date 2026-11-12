# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Narrow, read-only indexed-snapshot certificates; not source completeness proofs."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path

REQUEST = re.compile(
    r"(?:Return|Locate|Find|Identify) ([A-Z][A-Za-z0-9_$]*) "
    r"([a-z][A-Za-z0-9_$]*) and ([A-Z][A-Za-z0-9_$]*) "
    r"([a-z][A-Za-z0-9_$]*)\.?"
)
FIELDS = ("id", "project_id", "file_path", "symbol", "symbol_type", "symbol_key",
          "qualified_name", "owner_name", "owner_kind", "start_line", "end_line",
          "source_digest", "index_generation")
IDENTITY_FIELDS = ("file_path", "symbol", "owner_name", "owner_kind",
                   "qualified_name", "start_line", "end_line")


def request_targets(query):
    match = REQUEST.fullmatch(query.strip())
    if not match:
        return None
    a, am, b, bm = match.groups()
    if a == b:
        return None
    return ((a, am), (b, bm))


def valid_bounds(row):
    return (type(row.get("start_line")) is int and type(row.get("end_line")) is int
            and 0 < row["start_line"] <= row["end_line"])


def versioned(row):
    return (type(row.get("id")) is int and row["id"] > 0 and valid_bounds(row)
            and type(row.get("index_generation")) is int and row["index_generation"] > 0
            and isinstance(row.get("source_digest"), str)
            and re.fullmatch(r"[0-9a-f]{64}", row["source_digest"]) is not None
            and all(isinstance(row.get(k), str) and row[k] for k in
                    ("project_id", "file_path", "symbol", "symbol_key", "qualified_name")))


def signature(row):
    source = row.get("source_range") or {}
    return (row.get("file_path"), row.get("symbol"), row.get("owner_name"),
            source.get("start_line"), source.get("end_line"), source.get("selection_reason"))


class CertifiedPortfolio(dict):
    """Private attributes are not serialized into the public JSON schema."""
    def bind(self, primary):
        self._binding = (signature(primary), tuple(signature(x) for x in self["members"]))
        return self

    def valid_for(self, primary):
        return getattr(self, "_binding", None) == (
            signature(primary), tuple(signature(x) for x in self.get("members", [])))


def certificate_members(query, primary, candidates, ranges, eligible, project, receipts):
    targets = request_targets(query)
    if targets is None or project is None:
        return None
    selected = []
    for owner, method in targets:
        matches = [x for x in candidates if x.get("owner_name") == owner and x.get("symbol") == method]
        if len(matches) != 1 or matches[0] not in eligible:
            return None
        item = matches[0]
        if type(item.get("symbol_id")) is not int or item["symbol_id"] <= 0 or not valid_bounds(item):
            return None
        windows = [x for x in ranges if x.get("symbol_id") == item["symbol_id"]]
        if len(windows) != 1:
            return None
        window = windows[0]
        if (any(window.get(k) != item.get(k) for k in ("file_path", "symbol"))
                or not valid_bounds(window)
                or window.get("callable_start_line") != item["start_line"]
                or window.get("callable_end_line") != item["end_line"]
                or not item["start_line"] <= window["start_line"] <= window["end_line"] <= item["end_line"]):
            return None
        original = [x for x in receipts if x.get("kind") == "symbol" and x.get("id") == item["symbol_id"]]
        if not original or any(any(x.get(k) != original[0].get(k) for k in FIELDS) for x in original):
            return None
        row = original[0]
        if (not versioned(row) or row["project_id"] != project.project_id
                or any(row.get(k) != item.get(k) for k in IDENTITY_FIELDS)):
            return None
        selected.append((item, window, row))
    if len({x[0]["file_path"] for x in selected}) != 2:
        return None
    if not any(signature(primary) == signature({**x, "source_range": w}) for x, w, _ in selected):
        return None
    try:
        snapshots = snapshot(project, targets, selected)
    except (sqlite3.Error, OSError, ValueError):
        return None
    if snapshots is None:
        return None
    # Do not hold a DB transaction during source I/O. This is a point-in-time
    # check; later edits remain subject to existing excerpt freshness handling.
    try:
        root = Path(project.root).resolve()
        for row in snapshots:
            path = (root / row["file_path"]).resolve()
            if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != row["source_digest"]:
                return None
    except OSError:
        return None
    return [{"file_path": x["file_path"], "symbol": x["symbol"],
             "owner_name": x["owner_name"],
             "source_range": {k: w[k] for k in ("start_line", "end_line", "selection_reason") if k in w},
             "support_reasons": ["exact_requested_owner_method"]} for x, w, _ in selected]


def snapshot(project, targets, selected):
    conn = sqlite3.connect(Path(project.db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN")
        declarations = []
        for owner, _ in targets:
            # Count ALL exact-name symbols, a conservative superset of every
            # competing declaration kind (including unknown future kinds).
            params = (project.project_id, owner)
            where = " FROM code_symbols INDEXED BY idx_code_symbols_project_symbol WHERE project_id=? AND symbol=?"
            if conn.execute("SELECT COUNT(*)" + where, params).fetchone()[0] != 1:
                return None
            declaration = dict(conn.execute("SELECT *" + where, params).fetchone())
            if not versioned(declaration) or declaration.get("symbol_type") != "class":
                return None
            declarations.append(declaration)
        for declaration, (item, _window, receipt) in zip(declarations, selected):
            row = conn.execute("SELECT * FROM code_symbols WHERE project_id=? AND id=?",
                               (project.project_id, item["symbol_id"])).fetchone()
            if row is None:
                return None
            row = dict(row)
            if (any(row.get(k) != receipt.get(k) for k in FIELDS)
                    or row.get("symbol_type") not in {"function", "method"}
                    or declaration["file_path"] != row["file_path"]
                    or row["owner_name"] != declaration["symbol"]
                    or row["qualified_name"] != declaration["qualified_name"] + "." + row["symbol"]
                    or not declaration["start_line"] < row["start_line"] <= row["end_line"] <= declaration["end_line"]):
                return None
            files = conn.execute("SELECT source_digest,index_generation FROM code_files INDEXED BY idx_code_files_project_file WHERE project_id=? AND file_path=?",
                                 (project.project_id, row["file_path"])).fetchall()
            if len(files) != 1 or any(row.get(k) != declaration.get(k) or row.get(k) != files[0][k]
                                      for k in ("source_digest", "index_generation")):
                return None
        return declarations
    finally:
        conn.close()
