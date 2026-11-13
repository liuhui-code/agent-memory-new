# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""State-reference lexical filtering, not scope/data-flow certification."""
import re
from .ecma_callback_mask import callback_mask_lines


def state_accesses(body: str, names):
    masked = callback_mask_lines(body.splitlines())
    # Unsupported syntax retains unmasked-body extraction, not an absence proof.
    source = "\n".join(masked) if masked is not None else body
    for name in names:
        if re.search(rf"\bthis\.{re.escape(name)}\s*(?:=(?!=)|\+=|-=|\+\+|--)", source):
            yield name, "writes_state", 0.95, "state assignment"
        if re.search(rf"\bthis\.{re.escape(name)}\b(?!\s*(?:=(?!=)|\+=|-=|\+\+|--))", source):
            yield name, "reads_state", 0.9, "state read"
