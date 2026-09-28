"""Round 27h (Papyrus layer review): an offline upper bound of the native calls one Papyrus handler makes.

The Papyrus review measured ~1000 native calls per tree level-up (ESSBTrees.RefreshTree rebuilt 15 nodes x 5 probes and 60
branch probes every time). This reads the scripts in src/ and bounds a handler's native calls statically:

  * a call to a function of our own scripts (same script, `Controller.` / `akCtl.` -> ESSBController, `Trees.` -> ESSBTrees,
    or `ESSBNodes.` / `ESSBElem3.` ... global scripts) is followed (memoised, cycles cut);
  * any other call (`x.GetValueInt()`, `player.HasPerk(...)`, `Game.GetFormFromFile(...)`, `ESSBNative.X(...)`,
    `CustomSkills.X(...)`, ...) counts 1;
  * an If costs its condition plus its most expensive branch; a While costs its condition plus its body times its bound
    (`i < 15`, `i < TIER_COUNT` from an AutoReadOnly property, `i < X.Length` from LENGTHS, else LOOP_DEFAULT);
  * logging lines (LogEvent, Probe, Debug.Trace) and the lines under `If CachedDebugLevel >= n` are not counted (debug only);
  * InitTables / InitFixState (a one-time set-up behind its own flag) cost nothing after the first call.

build/fix28_verify.py pins the budgets (BUDGETS) and checks that the old RefreshTree body breaks them.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
LENGTHS = {'FormAbilities': 11, 'FormPowers': 11, 'UtilSpells': 40, 'PtsGlobals': 13, 'LvlGlobals': 13, 'pool': 64, 'nearby': 5,
           'allies': 5, 'args': 8, 'parts': 9}
LOOP_DEFAULT = 16
OBJECTS = {'Controller': 'ESSBController', 'akCtl': 'ESSBController', 'ctl': 'ESSBController', 'Trees': 'ESSBTrees',
           'trees': 'ESSBTrees', 'Self': None}
SKIP = re.compile(r'^\s*(?:Controller\.|akCtl\.)?(?:LogEvent|LogThrottled|Probe|Debug\.Trace|Debug\.TraceStack)\(')
KEYWORDS = {'If', 'ElseIf', 'While', 'Return', 'new', 'as', 'Function', 'Event', 'cast', 'Else'}
# The one-time table set-up every function calls first (guarded by its own "already done" flag): free after the first call.
ONCE = {'InitTables', 'InitFixState'}
PURE = {'Math.LogicalAnd', 'Math.LogicalOr', 'Math.LeftShift', 'Math.RightShift', 'Math.abs', 'Math.Floor', 'Math.Ceiling',
        'StringUtil.GetLength', 'StringUtil.Split', 'StringUtil.Find', 'StringUtil.Substring'}


class Scripts:
    def __init__(self, sources: dict[str, str]):
        self.fns: dict[str, dict[str, list[str]]] = {}
        self.consts: dict[str, dict[str, int]] = {}
        for name, text in sources.items():
            script = name.removesuffix('.psc')
            text = text.replace('\\\r\n', ' ').replace('\\\n', ' ')
            fns = {}
            for m in re.finditer(r'(?ms)^[ \t]*(?:\w+(?:\[\])?[ \t]+)?(?:Function|Event)[ \t]+(\w+)\s*\([^\n]*\)[^\n]*\n(.*?)^[ \t]*End(?:Function|Event)\b',
                                 text):
                fns[m.group(1)] = [self.strip(x) for x in m.group(2).splitlines() if self.strip(x)]
            self.fns[script] = fns
            self.consts[script] = {m.group(1): int(m.group(2)) for m in
                                   re.finditer(r'(?m)^Int Property (\w+) = (\d+) AutoReadOnly', text)}

    @staticmethod
    def strip(line: str) -> str:
        out, quoted = [], False
        for ch in line:
            if ch == '"':
                quoted = not quoted
            if ch == ';' and not quoted:
                break
            out.append(ch)
        return ''.join(out).strip()


class Budget:
    def __init__(self, scripts: Scripts):
        self.s = scripts
        self.memo: dict[tuple[str, str], int] = {}
        self.stack: set[tuple[str, str]] = set()

    def function(self, script: str, fn: str) -> int:
        key = (script, fn)
        if fn in ONCE:
            return 0
        if key in self.memo:
            return self.memo[key]
        if key in self.stack:
            return 0   # a cycle: counted once where it started
        self.stack.add(key)
        body = self.s.fns.get(script, {}).get(fn)
        cost = self.block(script, body, 0, len(body))[0] if body is not None else 1
        self.stack.discard(key)
        self.memo[key] = cost
        return cost

    def calls(self, script: str, text: str) -> int:
        text = re.sub(r'"[^"]*"', '""', text)
        cost = 0
        for m in re.finditer(r'(?:\b([A-Za-z_]\w*)\s*\.\s*)?\b([A-Za-z_]\w*)\s*\(', text):
            owner, name = m.group(1), m.group(2)
            if name in KEYWORDS or (owner and f'{owner}.{name}' in PURE):
                continue
            if owner is None:
                if name in self.s.fns.get(script, {}):
                    cost += self.function(script, name)
                elif name[0].isupper():
                    cost += 1   # a native of the script's own type (GetActorReference, RegisterForSingleUpdate ...)
                continue
            target = OBJECTS.get(owner, owner if owner in self.s.fns else None)
            if target and name in self.s.fns.get(target, {}):
                cost += self.function(target, name)
            else:
                cost += 1
        return cost

    def bound(self, script: str, condition: str) -> int:
        m = re.search(r'<=?\s*([\w.]+)', condition)
        if not m:
            return LOOP_DEFAULT
        token = m.group(1)
        if token.isdigit():
            return int(token) + (1 if '<=' in condition else 0)
        if token.endswith('.Length'):
            return LENGTHS.get(token.removesuffix('.Length').split('.')[-1], LOOP_DEFAULT)
        for consts in (self.s.consts.get(script, {}), *self.s.consts.values()):
            if token in consts:
                return consts[token]
        return LOOP_DEFAULT

    def block(self, script: str, lines: list[str], start: int, end: int) -> tuple[int, int]:
        cost, i = 0, start
        while i < end:
            line = lines[i]
            if line.startswith('If '):
                j, depth, branches, cuts = i + 1, 1, [line[3:]], [i + 1]
                while j < end:
                    t = lines[j]
                    if t.startswith('If '):
                        depth += 1
                    elif t == 'EndIf':
                        depth -= 1
                        if depth == 0:
                            break
                    elif depth == 1 and (t == 'Else' or t.startswith('ElseIf ')):
                        branches.append(t[7:] if t.startswith('ElseIf ') else '')
                        cuts.append(j + 1)
                    j += 1
                debug = re.search(r'CachedDebugLevel\s*>=', line)
                spans = [(cuts[k], (cuts[k + 1] - 1) if k + 1 < len(cuts) else j) for k in range(len(cuts))]
                conds = sum(self.calls(script, c) for c in branches)
                inner = 0 if debug else max(self.block(script, lines, a, b)[0] for a, b in spans)
                cost += conds + inner
                i = j + 1
                continue
            if line.startswith('While '):
                j, depth = i + 1, 1
                while j < end:
                    if lines[j].startswith('While '):
                        depth += 1
                    elif lines[j] == 'EndWhile':
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                n = self.bound(script, line[6:])
                cost += (n + 1) * self.calls(script, line[6:]) + n * self.block(script, lines, i + 1, j)[0]
                i = j + 1
                continue
            if not SKIP.match(line):
                cost += self.calls(script, line)
            i += 1
        return cost, i


def load(sources: dict[str, str] | None = None) -> Budget:
    if sources is None:
        sources = {p.name: p.read_text(encoding='utf-8-sig') for p in SRC.glob('*.psc')}
    return Budget(Scripts(sources))


def handler_cost(script: str, fn: str, sources: dict[str, str] | None = None) -> int:
    return load(sources).function(script, fn)
