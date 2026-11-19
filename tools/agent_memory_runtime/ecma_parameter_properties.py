"""Conservative TypeScript constructor parameter-property receiver bindings."""
import re
from collections import Counter
from .ecma_callable_headers import method_header
from .ecma_callback_mask import callback_mask_lines
from .ecma_field_scope import verified_depth_lines

NAME = r"[A-Za-z_$][\w$]*"
CONSTRUCTOR = re.compile(r"\s*(?:(?:public|private|protected)\s+)?constructor\s*\(")
PARAM = re.compile(
    rf"(?P<mod>(?:(?:public|private|protected|readonly)\s+)*)"
    rf"(?P<name>{NAME})\s*:\s*(?P<type>{NAME})"
)
MEMBER = re.compile(
    rf"\s*(?:(?:public|private|protected|readonly|static|declare|abstract|override|get|set)\s+)*"
    rf"(?P<name>{NAME})(?=\s*(?:[!?:(=;]|$))"
)
SCOPE_DECLARATION = re.compile(rf"\b(?:class|interface|type|enum|namespace|module)\s+({NAME})")


def constructor_receivers(lines, owners, imports, named_imports):
    if not named_imports or not any("constructor" in line for line in lines):
        return {}
    masked = callback_mask_lines(lines)
    if masked is None:
        return {}
    top_level = set(verified_depth_lines(masked, ()) or ())
    counts = Counter(owner.name for owner in owners)
    import_counts = Counter(alias for _, alias, _ in imports)
    imported_targets = {alias: (name, path) for name, alias, path in imports
                        if name == alias and alias in named_imports and path and import_counts[alias] == 1}
    local_types = set(SCOPE_DECLARATION.findall("\n".join(masked)))
    result = {}
    for owner in owners:
        if owner.kind != "class" or counts[owner.name] != 1 or owner.start not in top_level:
            continue
        owner_lines = masked[owner.start:owner.end + 1]
        fields = direct_constructor_fields(owner_lines, lines[owner.start:owner.end + 1])
        owner_header = "\n".join(owner_lines).partition("{")[0]
        bindings = {
            field: imported_targets[type_name]
            for field, type_name in fields.items()
            if type_name in imported_targets and type_name not in local_types
            and not re.search(r"\b" + re.escape(type_name) + r"\b", owner_header)
        }
        if bindings:
            result[owner.name] = bindings
    return result


def direct_constructor_fields(masked, originals):
    direct = verified_depth_lines(masked, ("{",))
    if not direct:
        return {}
    constructors = [index for index in direct if CONSTRUCTOR.match(masked[index])]
    if len(constructors) != 1:
        return {}
    index = constructors[0]
    header = method_header(masked, index)
    if (not header or header.name != "constructor" or header.return_type
            or not header.body_start or ")" in header.params):
        return {}
    members = set()
    for n in direct:
        if n == index:
            continue
        # A string-named or computed member cannot safely be compared after masking.
        if re.match(r"""\s*(?:(?:public|private|protected|readonly|static|get|set)\s+)*['"\[]""", originals[n]):
            return {}
        match = MEMBER.match(masked[n])
        if match:
            members.add(match.group("name"))
    fields = {}
    seen = set()
    owner_code = "\n".join(masked)
    if re.search(r"\bthis\s*\[", owner_code):
        return {}
    for value in header.params.removesuffix(",").split(","):
        param = PARAM.fullmatch(value.strip())
        if not param:
            return {}
        field, kind = param.group("name", "type")
        mods = param.group("mod").split()
        if field in seen or len(mods) != len(set(mods)) or len(set(mods) - {"readonly"}) > 1:
            return {}
        seen.add(field)
        if "readonly" in mods and field not in members and not written_receiver(field, owner_code):
            fields[field] = kind
    return fields


def written_receiver(field, owner_code):
    receiver = r"\bthis\s*\.\s*" + re.escape(field) + r"(?![\w$])"
    # The implicit constructor write is not present in source; explicit writes
    # leave the chosen narrow static receiver contract.
    write = r"(?:=(?!=|>)|(?:\*\*|>>?>?|<<|[+*/%&|^?\-]+)=|\+\+|--)"
    return re.search(rf"{receiver}\s*{write}|(?:\+\+|--)\s*{receiver}", owner_code)
