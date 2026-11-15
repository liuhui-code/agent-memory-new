"""Known-code input for the file statewrite hint, not scope certification."""
from .ecma_callback_mask import callback_mask_lines


def state_write_source(source: str) -> str:
    masked = callback_mask_lines(source.splitlines())
    # Unknown lexical input preserves the complete legacy marker behavior.
    return '\n'.join(masked) if masked is not None else source
