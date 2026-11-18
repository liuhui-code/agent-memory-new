# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite per-terminal read transaction helpers; never a capture issuer."""
import hashlib
import os
from pathlib import Path, PurePosixPath
import sqlite3
import stat
from .query_validation_log_capture import bounded_metadata

MAX_SOURCE = 2 * 1024 * 1024
SYMBOL = ('id','project_id','file_path','symbol','symbol_type','symbol_key','qualified_name',
          'signature','start_line','end_line','semantic_adapter','source_digest','evidence_class',
          'owner_name','owner_kind','index_generation')
FILE = ('id','project_id','file_path','language','source_digest','index_generation')
LOG = ('id','project_id','file_path','line','function','level','logger','message_template',
       'raw_statement','business_summary','business_terms','business_event','trigger_stage',
       'symptom_terms','likely_causes','process_hint','neighbor_terms','source_digest',
       'index_generation','updated_at')
INDEX = ('project_id','generation','source_revision','extractor_version','status',
         'indexed_file_count','retired_file_count','updated_at')
COLUMNS = {'code_symbols': SYMBOL, 'code_files': FILE,
           'code_log_statements': LOG, 'code_index_state': INDEX}


def path_ok(value):
    return (type(value) is str and bool(value) and '\\' not in value and '#' not in value
            and not PurePosixPath(value).is_absolute()
            and all(x not in ('', '.', '..') for x in value.split('/')))


def same(a, b, fields):
    return all(k in a and k in b and type(a[k]) is type(b[k]) and a[k] == b[k] for k in fields)


class Round:
    def __init__(self, db, project, paths, base):
        if not bounded_metadata(base):
            raise ValueError('input metadata')
        self.db, self.project, self.paths, self.base = db, project, set(paths), base
        self.rows, self.cache, self.sources, self.parts = [], {}, {}, []
        self.source_reads = 0
        self.source_bytes = 0

    def bounded(self, value):
        return bounded_metadata([self.base, self.rows, self.parts, value])

    def find(self, table, clause, args):
        key = (table, clause, args)
        if key in self.cache:
            return self.cache[key]
        columns = COLUMNS[table]
        # SQLite truncation is NOT accepted: oversized fields become a bytes
        # sentinel that bounded_metadata rejects before a detached dict exists.
        fields = ','.join("CASE WHEN typeof("+c+") IN ('text','blob') AND length(CAST("
                          +c+" AS BLOB))>16384 THEN zeroblob(0) ELSE "+c+" END AS "+c
                          for c in columns)
        cursor = self.db.execute('SELECT '+fields+' FROM '+table+' WHERE '+clause+' LIMIT 65', args)
        found = []
        for row in cursor:
            if len(found) >= 64 or type(row) is not sqlite3.Row or len(row) > 128:
                raise ValueError('DB probe limit')
            keys = row.keys()
            if keys != list(columns) or any(len(k.encode('utf-8')) > 128 for k in keys):
                raise ValueError('DB columns')
            values = [row[k] for k in keys]
            if not self.bounded([found, values]):
                raise ValueError('joint DB metadata')
            record = dict(zip(keys, values))
            if not self.bounded([found, record]):
                raise ValueError('joint row metadata')
            found.append(record)
        if not self.bounded(found):
            raise ValueError('DB certificate')
        self.rows.extend(found)
        self.cache[key] = found
        return found

    def one(self, table, clause, args):
        found = self.find(table, clause, args)
        if len(found) != 1:
            raise ValueError('missing or ambiguous '+table)
        return found[0]

    def read(self, path, digest):
        if path in self.sources:
            cached = self.sources[path]
            if cached['digest'] != digest:
                raise ValueError('conflicting same-path digest')
            return cached['text']
        if not path_ok(path) or path not in self.paths or len(self.sources) >= 12:
            raise ValueError('outside source scope')
        root = Path(self.project.root).resolve()
        lexical = root / path
        if any(p.is_symlink() for p in (lexical, *lexical.parents)):
            raise ValueError('symlink source')
        if not lexical.resolve().is_relative_to(root):
            raise ValueError('outside root')
        # Walk every directory descriptor with NOFOLLOW so an ancestor cannot
        # be swapped for a symlink between the lexical check and the leaf open.
        if not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
            raise ValueError('unsupported secure source open')
        dir_fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in (*root.parts[1:], *PurePosixPath(path).parts[:-1]):
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)
                os.close(dir_fd)
                dir_fd = next_fd
            fd = os.open(PurePosixPath(path).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
        finally:
            os.close(dir_fd)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('nonregular source')
            stream = os.fdopen(fd, 'rb')
        except BaseException:
            try:
                os.close(fd)
            except OSError:
                pass  # Preserve the fstat/type/wrapper failure if the fd was already closed.
            raise
        with stream:
            data = stream.read(MAX_SOURCE + 1)
            self.source_reads += 1
            self.source_bytes += len(data)
            after = os.fstat(stream.fileno())
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                or len(data) > MAX_SOURCE or hashlib.sha256(data).hexdigest() != digest):
            raise ValueError('source race/size/digest')
        text = data.decode('utf-8')
        # No source-string exemption from the fixed scalar budget. This bounds
        # the existing lexer's token-buffer input before token allocation.
        if not bounded_metadata(text):
            raise ValueError('source parse scalar budget')
        self.sources[path] = {'digest': digest, 'text': text}
        return text
