# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Optional lexical navigation of already selected rows; never an identity alias."""
import hashlib
import os
from pathlib import PurePosixPath
import stat

from .required_source_reads import source_expectation, source_read_failed, RequiredSourceReadError

def read_literal_source(project, name):
    """Bounded, nonblocking, no-follow walk, including directory ancestors."""
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(p in {'.', '..'} for p in path.parts):
        return None
    if not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_NONBLOCK'):
        return None
    target = project.root.joinpath(*path.parts)
    expected = source_expectation(target)
    fd = None
    try:
        fd = os.open(project.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in path.parts[:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        leaf = os.open(path.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        os.close(fd)
        fd = leaf
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 65536:
            return None
        data = bytearray()
        while len(data) <= 65536:
            chunk = os.read(fd, min(8192, 65537 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(fd)
        if len(data) > 65536 or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            return None
        digest = hashlib.sha256(data).hexdigest()
        source_expectation(target)
        if expected is not None and digest != expected[0]:
            raise RequiredSourceReadError(f"required rebuild source changed outside declared refresh: {target}")
        return bytes(data)
    except OSError as error:
        source_read_failed(target, error)
        return None
    finally:
        if fd is not None:
            os.close(fd)

