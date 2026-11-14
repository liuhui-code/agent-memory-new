# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite same-owner lifecycle source syntax, never runtime persistence proof."""
import re
from .query_recovery_source import RecoveryParser, span, Unknown


class LifecycleParser(RecoveryParser):
    def field(self):
        first = self.tokens[self.pos]
        state = self.optional('@')
        if state:
            self.take('State')
        else:
            self.take('private')
        name = self.identifier().value
        self.declare(name); self.take(':')
        if self.optional('string'):
            self.take('=')
            if self.take(kind='string').value != '':
                raise Unknown()
            kind, type_name, constructor = 'state' if state else 'text', 'string', None
        else:
            if state:
                raise Unknown()
            type_name = self.identifier().value
            constructor = self.new_constructor() if self.optional('=') else None
            kind = 'receiver'
        self.statement_end()
        self.fields.append(dict(name=name, kind=kind, type=type_name,
                                constructor=constructor, **span(first, self.tokens[self.pos - 1])))

    def receiver(self):
        if self.optional('this'):
            self.take('.')
            return 'this.' + self.identifier().value
        return self.identifier().value

    def method(self):
        first = self.tokens[self.pos]
        asynchronous = self.optional('async')
        name_token = self.identifier()
        name = name_token.value
        if asynchronous and name_token.line != first.line:
            raise Unknown()
        self.declare(name)
        self.take('('); self.take(')'); self.take(':')
        if asynchronous:
            self.take('Promise'); self.take('<'); self.take('void'); self.take('>')
        else:
            self.take('void')
        self.take('{')
        extra = {}
        if not asynchronous:
            if name not in {'onMount', 'aboutToAppear'}:
                raise Unknown()
            call = self.take('this'); self.take('.')
            target = self.identifier().value
            self.take('('); self.take(')')
            kind = 'hook'
            extra = dict(target=target, call_line=call.line,
                         call_start_offset=call.start, call_end_offset=self.tokens[self.pos - 1].end)
        elif self.optional('this'):
            self.take('.'); field = self.identifier().value
            self.take('='); self.take('await')
            receiver = self.receiver()
            self.take('.'); self.take('load'); self.take('('); self.take(')')
            kind = 'restore'
            extra = dict(text=field, receiver=receiver)
        else:
            self.take('await')
            receiver = self.receiver()
            self.take('.'); self.take('save'); self.take('(')
            self.take('this'); self.take('.'); field = self.identifier().value
            self.take(')')
            kind = 'commit'
            extra = dict(text=field, receiver=receiver)
        self.statement_end(); end = self.take('}')
        if end.end - first.start > 32768:
            raise Unknown()
        self.methods.append(dict(name=name, kind=kind, **span(first, end), **extra))

    def parse(self):
        while self.optional('import'):
            self.take('{')
            name = self.identifier().value
            self.declare(name); self.imports.add(name)
            while self.optional(','):
                name = self.identifier().value
                self.declare(name); self.imports.add(name)
            self.take('}'); self.take('from')
            path = self.take(kind='string').value
            if not re.fullmatch(r'\.{1,2}/[A-Za-z0-9_./-]+', path):
                raise Unknown()
            self.statement_end(closing_allowed=False)
        first = self.tokens[self.pos]
        self.optional('export'); self.take('class')
        owner = self.identifier().value
        self.declare(owner); self.take('{')
        while not self.peek('}'):
            if self.peek('private') or self.peek('@'):
                self.field()
            else:
                self.method()
            if len(self.fields) > 2 or len(self.methods) > 3:
                raise Unknown()
        end = self.take('}')
        if self.tokens[self.pos].kind != 'eof' or len(self.methods) != 3:
            raise Unknown()
        methods = {m['kind']: m for m in self.methods}
        if set(methods) != {'hook', 'restore', 'commit'}:
            raise Unknown()
        texts = [f for f in self.fields if f['kind'] in {'text', 'state'}]
        receivers = [f for f in self.fields if f['kind'] == 'receiver']
        if len(texts) != 1 or len(receivers) > 1:
            raise Unknown()
        hook, restore, commit = (methods[k] for k in ('hook', 'restore', 'commit'))
        if (hook['target'] != restore['name'] or restore['text'] != texts[0]['name']
                or commit['text'] != texts[0]['name'] or restore['receiver'] != commit['receiver']):
            raise Unknown()
        receiver = restore['receiver']
        if receiver.startswith('this.'):
            if len(receivers) != 1 or receivers[0]['name'] != receiver[5:]:
                raise Unknown()
        elif receiver in self.names - self.imports:
            # A bare external receiver may be unresolved or imported, not silently
            # resolve to a same-owner field/method/class with a different scope.
            raise Unknown()
        names = {m['name'] for m in self.methods} | {f['name'] for f in self.fields}
        if any(f['constructor'] in names for f in receivers):
            raise Unknown()
        return dict(owner=owner, class_start=first.line, class_end=end.line,
                    class_start_offset=first.start, class_end_offset=end.end,
                    fields=self.fields, methods=self.methods, text=texts[0]['name'],
                    hook=hook['name'], restore=restore['name'], commit=commit['name'],
                    hook_call_line=hook['call_line'], receiver=receiver)


def parse_lifecycle_source(source):
    """Return exact declarations and direct syntax on this source string only."""
    if not isinstance(source, str) or '\u2028' in source or '\u2029' in source:
        return None
    try:
        if len(source.encode('utf-8')) > 2 * 1024 * 1024:
            return None
        return LifecycleParser(source).parse()
    except (Unknown, IndexError, UnicodeError):
        return None
