# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Execute schema scripts without sqlite3.executescript's implicit COMMIT."""
from __future__ import annotations
import sqlite3


def execute_schema(conn: sqlite3.Connection, script: str) -> None:
    statement = ""
    for char in script:
        statement += char
        if char == ";" and sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement = ""
    if statement.strip():
        # All static callers use terminated statements. Never partially execute
        # an unknown trailing fragment as if a full schema had succeeded.
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
        else:
            raise ValueError("Incomplete schema statement")
