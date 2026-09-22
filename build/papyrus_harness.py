"""Small source-level Papyrus harness. Native calls are explicit mocks, NOT Skyrim runtime.

Executes the actual selected function bodies (If/While/assignments/calls), rather than
restating their formulas in tests. Unsupported syntax fails closed.
"""
import re
import ast
from pathlib import Path


class Array(list):
    @property
    def Length(self):
        return len(self)


def strip_comment(line):
    # A semicolon inside a Papyrus string is part of the message.
    return re.split(r';(?=(?:[^"\\]*(?:\\.[^"\\]*)*"[^"\\]*(?:\\.[^"\\]*)*")*[^"\\]*(?:\\.[^"\\]*)*$)', line, maxsplit=1)[0]


def papyrus_add(left, right):
    if isinstance(left, str) or isinstance(right, str):
        return str(left) + str(right)
    return left + right


class PapyrusConcat(ast.NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Add):
            return ast.copy_location(ast.Call(func=ast.Name(id='_papyrus_add', ctx=ast.Load()),
                                             args=[node.left, node.right], keywords=[]), node)
        return node


class Returned(Exception):
    def __init__(self, value):
        self.value = value


def default(t):
    return {'Int': 0, 'Float': 0.0, 'Bool': False, 'String': ''}.get(t)


def cast(v, t):
    if t == 'Int':
        return int(v or 0)
    if t == 'Float':
        return float(v or 0)
    if t == 'Bool':
        return bool(v)
    return v


def expression(s):
    s = s.replace('&&', ' and ').replace('||', ' or ')
    s = re.sub(r'!(?!=)', ' not ', s)
    s = re.sub(r'new (\w+)\[(\d+)\]', lambda m: f'Array([{default(m[1])!r}] * {m[2]})', s)
    # Casts used by the exercised source bodies. Unsupported casts remain syntax errors.
    pat = r'(\([^()]*\)|[\w.]+(?:\([^()]*\))?(?:\.\w+(?:\([^()]*\))?)*(?:\[[^\]]+\])?) as (Int|Float|Bool|Actor|Spell|Weapon|Ammo|Projectile|ESSBController|ESSBGuard|ESSBInput|ESSBTrees|Quest|Perk|GlobalVariable|Message|Form)'
    s = re.sub(pat, lambda m: f'cast({m[1]}, {m[2]!r})', s)
    return s.strip()


class Scope(dict):
    def __init__(self, vm):
        super().__init__()
        self.vm = vm
        self.types = {}

    def __missing__(self, name):
        if name == 'Self':
            return self.vm
        if name in self.vm.env:
            return self.vm.env[name]
        if name in ('Array', 'cast'):
            return globals()[name]
        return getattr(self.vm, name)


class Script:
    def __init__(self, path, env=None):
        self.path = Path(path)
        self.env = env or {}
        self.fields = {}
        self.types = {}
        self.overrides = {}
        self.functions = {}
        source = self.path.read_text(encoding='utf8').replace('\\\n', '')
        source = re.sub(r'(?m)^Event ', 'Function ', source)
        source = re.sub(r'(?m)^EndEvent$', 'EndFunction', source)
        for line in source.splitlines():
            m = re.match(r'^(\w+(?:\[\])?) (?:Property )?(\w+)(?: = (.*?))?(?: Auto.*)?$', strip_comment(line).strip('\r'))
            if m and m[1] not in ('Scriptname', 'Function', 'Event', 'Return', 'ElseIf', 'If', 'While'):
                t, name, value = m.groups()
                self.types[name] = t
                self.fields[name] = eval(value, {}, {}) if value else default(t)
        for m in re.finditer(r'(?m)^(?:(\w+(?:\[\])?) )?Function (\w+)\(([^\n]*)\)(?: Global)?\s*\n(.*?)^EndFunction', source, re.S):
            rt, name, args, body = m.groups()
            params = []
            for arg in args.split(',') if args.strip() else []:
                bits = re.fullmatch(r'\s*(\w+(?:\[\])?)\s+(\w+)(?:\s*=\s*(.*))?', arg)
                assert bits, (name, arg)
                params.append(bits.groups())
            lines = [strip_comment(x).strip() for x in body.splitlines()]
            lines = [x for x in lines if x]
            self.functions[name] = rt, params, lines

    def __getattr__(self, name):
        if name in self.overrides:
            return self.overrides[name]
        if name in self.fields:
            return self.fields[name]
        if name in self.functions:
            return lambda *args: self.call(name, *args)
        raise AttributeError(f'{self.path.name}: unmocked {name}')

    def evaluate(self, text, scope):
        code = expression(text)
        if self.env.get('__papyrus_concat__', False):
            code = compile(ast.fix_missing_locations(PapyrusConcat().visit(ast.parse(code, mode='eval'))),
                           str(self.path), 'eval')
            scope['_papyrus_add'] = papyrus_add
        return eval(code, {'__builtins__': {}}, scope)

    def call(self, name, *args):
        if name in self.overrides:
            return self.overrides[name](*args)
        rt, params, lines = self.functions[name]
        scope = Scope(self)
        for index, (t, key, d) in enumerate(params):
            scope.types[key] = t
            scope[key] = cast(args[index] if index < len(args) else self.evaluate(d, scope), t)
        try:
            self.run(lines, scope)
        except Returned as result:
            return cast(result.value, rt)
        return None

    def run(self, lines, scope):
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.startswith('If '):
                depth = 1
                end = index + 1
                branches = [(line[3:], end)]
                while end < len(lines):
                    text = lines[end]
                    if text.startswith('If '):
                        depth += 1
                    elif text == 'EndIf':
                        depth -= 1
                    if depth == 0:
                        break
                    if depth == 1 and (text == 'Else' or text.startswith('ElseIf ')):
                        branches.append((text[7:] if text.startswith('ElseIf ') else 'True', end + 1))
                    end += 1
                assert depth == 0, line
                for n, (condition, start) in enumerate(branches):
                    stop = branches[n + 1][1] - 1 if n + 1 < len(branches) else end
                    if self.evaluate(condition, scope):
                        self.run(lines[start:stop], scope)
                        break
                index = end + 1
                continue
            if line.startswith('While '):
                depth, end = 1, index + 1
                while end < len(lines):
                    if lines[end].startswith('While '):
                        depth += 1
                    elif lines[end] == 'EndWhile':
                        depth -= 1
                    if not depth:
                        break
                    end += 1
                assert depth == 0, line
                count = 0
                while self.evaluate(line[6:], scope):
                    count += 1
                    assert count < 10000, 'unbounded loop'
                    self.run(lines[index + 1:end], scope)
                index = end + 1
                continue
            if line == 'Return' or line.startswith('Return '):
                raise Returned(self.evaluate(line[7:], scope) if len(line) > 6 else None)
            # Logs have no gameplay effects; Papyrus concatenates unlike Python.
            if re.match(r'(?:\w+\.)?(?:LogThrottled|LogRejectedHit|LogEvent|Log|Trace|Notification)\(', line) and not self.env.get('__execute_logs__', False):
                index += 1
                continue
            declaration = re.fullmatch(r'(\w+(?:\[\])?) (\w+)(?: = (.*))?', line)
            if declaration and declaration[1] in ('Int', 'Float', 'Bool', 'String', 'Actor', 'ActorBase', 'Actor[]', 'Int[]', 'Float[]', 'Bool[]', 'ESSBStatus', 'ESSBMark', 'Spell', 'ObjectReference', 'Race', 'Weapon', 'Ammo', 'Projectile', 'ESSBGuard', 'ESSBInput', 'ESSBController', 'Quest', 'String[]', 'GlobalVariable', 'Perk', 'ESSBTrees', 'Message', 'Form'):
                t, name, value = declaration.groups()
                scope.types[name] = t
                scope[name] = cast(self.evaluate(value, scope) if value else default(t), t)
            else:
                assignment = re.fullmatch(r'([\w.]+)(?:\[(.+)\])?\s*(=|\+=|-=|\*=)\s*(.*)', line)
                if assignment:
                    name, subscript, op, rhs = assignment.groups()
                    value = self.evaluate(rhs, scope)
                    dest = scope if name in scope.types else self.fields
                    t = scope.types.get(name, self.types.get(name))
                    if '.' in name:
                        owner_name,name=name.rsplit('.',1)
                        owner=self.evaluate(owner_name,scope)
                        dest=owner.fields if isinstance(owner,Script) else vars(owner)
                        t=owner.types.get(name) if isinstance(owner,Script) else None
                    if subscript is not None:
                        dest = scope[name]
                        name = int(self.evaluate(subscript, scope))
                        t = t[:-2] if t and t.endswith('[]') else t
                    if op != '=':
                        old = dest[name]
                        value = old + value if op == '+=' else old - value if op == '-=' else old * value
                    dest[name] = cast(value, t)
                else:
                    self.evaluate(line, scope)
            index += 1
