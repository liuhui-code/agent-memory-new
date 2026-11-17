"""Closed lexical declaration inventory for SQL slot source witnesses."""
import hashlib
import re
from dataclasses import dataclass


# Closed binding-name subset. This is not a claim that these words cannot be
# property names in JavaScript; member syntax is handled separately below.
RESERVED_BINDINGS = set("await break case catch class const continue debugger default delete do else enum export extends false finally for function if import in instanceof new null return super switch this throw true try typeof var void while with yield implements interface let package private protected public static struct async readonly".split())


def legal_binding(name):
    return bool(re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', name)) and name not in RESERVED_BINDINGS


class Unknown(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    value: str
    kind: str
    start: int
    end: int


def lex(s):
    if any(c in s for c in ('\u2028', '\u2029', '\x85', '\x0b', '\x0c')):
        raise Unknown('unsupported_line_separator')
    if re.search(r'\r(?!\n)', s):
        raise Unknown('bare_cr')
    out = []
    i = 0
    while i < len(s):
        if s[i].isspace():
            i += 1
            continue
        if s.startswith('//', i):
            j = s.find('\n', i); i = len(s) if j < 0 else j
            continue
        if s.startswith('/*', i):
            j = s.find('*/', i + 2)
            if j < 0:
                raise Unknown('comment')
            i = j + 2
            continue
        a = i
        if s[i] in "'\"":
            q = s[i]; i += 1
            while i < len(s) and s[i] != q:
                if s[i] in '\r\n':
                    raise Unknown('string_newline')
                if s[i] == '\\':
                    i += 1
                    if i >= len(s) or s[i] not in "\\'\"nrt":
                        raise Unknown('escape')
                i += 1
            if i == len(s):
                raise Unknown('string')
            i += 1; kind = 'string'
        else:
            m = re.match(r'[A-Za-z_$][A-Za-z0-9_$]*|[0-9]+|=>|===|!==|==|!=|&&|\|\||\?\?|[{}\[\]().,:;@=<>!?+*-]', s[i:])
            if not m:
                raise Unknown('lexical_token')
            i += len(m[0]); kind = 'ident' if re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', m[0]) else 'punct'
        out.append(Token(s[a:i], kind, a, i))
    return out


def pairs(ts):
    stack = []; result = {}
    for i, t in enumerate(ts):
        if t.value in ('(', '[', '{'):
            stack.append((t.value, i))
        elif t.value in (')', ']', '}'):
            if not stack or stack[-1][0] != {')': '(', ']': '[', '}': '{'}[t.value]:
                raise Unknown('unbalanced')
            _, a = stack.pop(); result[a] = i
    if stack:
        raise Unknown('unbalanced')
    return result


def span(s, ts):
    if not ts:
        raise Unknown('empty_span')
    a, b = ts[0].start, ts[-1].end
    return dict(start_offset=a, end_offset=b, start_line=s.count('\n', 0, a)+1,
                end_line=s.count('\n', 0, b)+1)


def compact(ts):
    return ''.join((' ' if i and ts[i-1].kind == 'ident' and t.kind == 'ident' else '') + t.value for i, t in enumerate(ts))


class Owner(dict):
    """Private inventory-produced identity, revalidated against source on use."""
    pass


def inventory_source(source):
    try:
        return _inventory(source)
    except (Unknown, IndexError, TypeError, AttributeError) as e:
        return {'status': 'unknown', 'reason': str(e), 'declarations': [], 'imports': []}


def _inventory(s):
    ts = lex(s); ps = pairs(ts); i = 0; imports = []; owners = []; names = set(); locals_ = set()
    digest = hashlib.sha256(s.encode()).hexdigest()
    def decorators(i, allowed):
        ds = []
        while i < len(ts) and ts[i].value == '@':
            name = ts[i+1].value
            if name not in allowed:
                raise Unknown('decorator')
            a = i; i += 2
            if i < len(ts) and ts[i].value == '(':
                end = ps[i]
                if name != 'Consumer' or end != i+2 or ts[i+1].kind != 'string':
                    raise Unknown('decorator_arguments')
                i = end+1
            elif name == 'Consumer':
                raise Unknown('consumer_arguments')
            ds.append({'name': name, 'span': span(s, ts[a:i])})
        if len({x['name'] for x in ds}) != len(ds):
            raise Unknown('duplicate_decorator')
        return ds, i
    while i < len(ts):
        a = i
        if ts[i].value == 'import':
            if ts[i+1].value != '{': raise Unknown('import_form')
            end = ps[i+1]; j = i+2; bindings = []
            while j < end:
                imported = ts[j].value; local = imported; j += 1
                if ts[j].value == 'as': local = ts[j+1].value; j += 2
                if not re.fullmatch(r'[A-Za-z_$][\w$]*', imported) or not legal_binding(local) or local in locals_:
                    raise Unknown('import_binding')
                locals_.add(local); bindings.append((imported, local))
                if j < end:
                    if ts[j].value != ',': raise Unknown('import_separator')
                    j += 1
            if ts[end+1].value != 'from' or ts[end+2].kind != 'string': raise Unknown('import_module')
            i = end+3
            if i < len(ts) and ts[i].value == ';': i += 1
            imports.extend(dict(imported=x, local=y, module=ts[end+2].value[1:-1], span=span(s, ts[a:i])) for x,y in bindings)
            continue
        dec, i = decorators(i, {'Component', 'ComponentV2', 'Entry'})
        declaration_start = i
        mods = []
        if ts[i].value == 'export': mods.append('export'); i += 1
        kind = ts[i].value; name = ts[i+1].value; i += 2
        if kind not in ('class', 'struct') or not legal_binding(name) or name in names or ts[i].value != '{': raise Unknown('owner')
        names.add(name); end = ps[i]; i += 1; fields = []; methods = []; members = set()
        while i < end:
            start = i; fd, i = decorators(i, {'State', 'Local', 'Consumer'})
            fm = []
            while ts[i].value in ('private', 'public', 'readonly', 'async'):
                fm.append(ts[i].value); i += 1
            member = ts[i].value; i += 1
            if ts[i-1].kind != 'ident' or member in members or len(fm)!=len(set(fm)) or {'private','public'}.issubset(fm):
                raise Unknown('member_identity')
            if member == 'constructor': raise Unknown('unsupported_constructor_member')
            members.add(member)
            if ts[i].value == '(':
                if fd or 'readonly' in fm: raise Unknown('method_modifiers')
                pend = ps[i]; params = ts[i+1:pend]; i = pend+1; rt = []
                parameter_names=set()
                if params:
                    for part in compact(params).split(','):
                        binding, colon, annotation = part.partition(':')
                        if not colon or not legal_binding(binding) or binding in parameter_names or not annotation:
                            raise Unknown('parameter_binding')
                        parameter_names.add(binding)
                if ts[i].value == ':':
                    i += 1
                    while ts[i].value != '{': rt.append(ts[i]); i += 1
                if ts[i].value != '{': raise Unknown('method_body')
                bend = ps[i]; body = ts[i+1:bend]
                methods.append(dict(name=member, modifiers=fm, parameters=compact(params), return_type=compact(rt), span=span(s,ts[start:bend+1]), body_span=span(s,ts[i:bend+1]), _body=body))
                i = bend+1
            else:
                if 'async' in fm or ts[i].value != ':': raise Unknown('field_type')
                i += 1; typ = []
                while ts[i].value != '=': typ.append(ts[i]); i += 1
                if not re.fullmatch(r'[A-Za-z_$][\w$]*(?:\[\])?',compact(typ)): raise Unknown('field_type')
                i += 1; init = i
                while i < end:
                    if ts[i].value == ';': break
                    if i > init and '\n' in s[ts[i-1].end:ts[i].start]: break
                    if ts[i].value in ('(', '[', '{'): i = ps[i]+1
                    else: i += 1
                if i == init: raise Unknown('field_initializer')
                value = ts[init:i]
                if i < end and ts[i].value == ';': i += 1
                fields.append(dict(name=member, type=compact(typ), modifiers=fm, decorators=fd, initializer=compact(value), _initializer=value, initializer_span=span(s,value), span=span(s,ts[start:i])))
        i = end+1
        owner=Owner(kind=kind,name=name,decorators=dec,modifiers=mods,span=span(s,ts[declaration_start:i]),decorated_span=span(s,ts[a:i]),fields=fields,methods=methods)
        owner._digest=digest; owner._source=s; owner._imports=imports; owners.append(owner)
    return dict(status='known', declarations=owners, imports=imports, source_sha256=digest)


def authenticated(source, owner):
    if type(owner) is not Owner or owner._source != source or owner._digest != hashlib.sha256(source.encode()).hexdigest():
        raise Unknown('owner_authentication')
    fresh = inventory_source(source)
    if fresh['status'] != 'known' or owner._imports != fresh['imports'] or not any(dict(x)==dict(owner) for x in fresh['declarations']):
        raise Unknown('owner_changed')
