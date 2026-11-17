# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Unconnected typed-derived resource predicate; never receipt/source authority."""
import math
import re
from .query_validation_log_capture import (
    bounded_metadata, MAX_DEPTH, MAX_NODES, MAX_SCALAR_BYTES, MAX_BYTES)

_DIGEST = re.compile(r'[0-9a-f]{64}')


def _reserve(budget, nodes=0, byte_count=0):
    budget[0] += nodes
    budget[1] += byte_count
    return budget[0] <= MAX_NODES and budget[1] <= MAX_BYTES


def _text_size(value):
    # Check character length first; encoding is bounded by 4*scalar ceiling.
    if type(value) is not str or len(value) > MAX_SCALAR_BYTES:
        return None
    try:
        size = len(value.encode('utf-8'))
    except UnicodeError:
        return None
    return size if size <= MAX_SCALAR_BYTES else None


def _metadata(value, budget):
    """Measure the original object at R depth1, without recursive copying."""
    if not _reserve(budget, nodes=1):
        return False
    stack = [(value, 1, False)]
    active = set()
    while stack:
        item, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(item))
            continue
        if depth > MAX_DEPTH:
            return False
        kind = type(item)
        if kind in (dict, list):
            if id(item) in active or not _reserve(budget, nodes=len(item)):
                return False
            active.add(id(item))
            stack.append((item, depth, True))
            if kind is dict:
                for key, child in item.items():
                    size = _text_size(key)
                    if size is None or not _reserve(budget, byte_count=size):
                        return False
                    stack.append((child, depth + 1, False))
            else:
                for child in item:
                    stack.append((child, depth + 1, False))
        elif kind is str:
            size = _text_size(item)
            if size is None or not _reserve(budget, byte_count=size):
                return False
        elif item is None or kind is bool:
            pass
        elif kind is int:
            if item.bit_length() > 64:
                return False
        elif kind is float:
            if not math.isfinite(item):
                return False
        else:
            return False
    return True


def _files(files, budget):
    if type(files) is not tuple or len(files) > 12:
        return False
    if not _reserve(budget, nodes=1):  # files list at R depth1
        return False
    seen = set()
    for pair in files:
        if type(pair) is not tuple or len(pair) != 2:
            return False
        path, digest = pair
        size = _text_size(path)
        if (size is None or not path or path.startswith('/') or '\\' in path
                or '#' in path or '\x00' in path):
            return False
        # Split only the already scalar-bounded exact string, never custom path.
        if any(part in ('', '.', '..') for part in path.split('/')) or path in seen:
            return False
        if type(digest) is not str or len(digest) != 64 or _DIGEST.fullmatch(digest) is None:
            return False
        seen.add(path)
        # Pair list + its two scalar children, at R depths2 and3 respectively.
        if not _reserve(budget, nodes=3, byte_count=size + 64):
            return False
    return True


def _derived(value, budget):
    """Measure chunks in one joint budget without allocating chunk strings."""
    if type(value) is not str or len(value) > MAX_BYTES:
        return False
    if not _reserve(budget, nodes=1):  # chunks list, even when empty
        return False
    current = 0
    try:
        for character in value:
            size = len(character.encode('utf-8'))
            if current == 0 or current + size > MAX_SCALAR_BYTES:
                if not _reserve(budget, nodes=1):
                    return False
                current = 0
            if not _reserve(budget, byte_count=size):
                return False
            current += size
    except UnicodeError:
        return False
    return True


def _chunks(value):
    """Construct maximal codepoint-safe slices only after joint measurement."""
    chunks = []
    start = 0
    current = 0
    for index, character in enumerate(value):
        size = len(character.encode('utf-8'))
        if current + size > MAX_SCALAR_BYTES:
            chunks.append(value[start:index])
            start = index
            current = 0
        current += size
    if value:
        chunks.append(value[start:])
    return chunks


def bounded_binding_parts(metadata, files, state, proof):
    """Check exact R=[metadata,files-as-lists,chunks(state),chunks(proof)].

    Trusted typed arguments are not accepted through similarly named raw keys.
    Original state/proof remain original strings for caller seals. Nothing here
    checks provenance or grants authority: short forged strings may pass.
    """
    budget = [1, 0]  # R itself; no materialized R or chunks yet
    if not _metadata(metadata, budget) or not _files(files, budget):
        return False
    if not _derived(state, budget) or not _derived(proof, budget):
        return False
    # Entire combined representation is now within all ceilings. Metadata is
    # referenced, never copied. Tuple/list conversion is limited to <=12 pairs.
    representation = [metadata, [[path, digest] for path, digest in files],
                      _chunks(state), _chunks(proof)]
    return bounded_metadata(representation)
