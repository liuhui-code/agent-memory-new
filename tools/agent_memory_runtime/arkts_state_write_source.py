"""Known-code input for the file statewrite hint, not scope certification."""
import re
from .ecma_callback_mask import callback_mask_lines

_FILE_STATE_WRITE_RE = re.compile(
    r"\bthis\.[A-Za-z_$][A-Za-z0-9_$]*\s*(?:=(?![=>])|\+=|-=|\+\+|--)"
)


def state_write_source(source: str) -> str:
    masked = callback_mask_lines(source.splitlines())
    # Unknown lexical input preserves the complete legacy marker behavior.
    return '\n'.join(masked) if masked is not None else source


def has_file_state_write(source: str) -> bool:
    return _FILE_STATE_WRITE_RE.search(state_write_source(source)) is not None
