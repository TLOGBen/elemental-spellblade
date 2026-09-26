"""Round 21: one name-to-position identity table for every skill-tree read (outcome 2).

The identity table is build/plan-tree-nodes.json (plan_trees.py, parsed from 元素魔戰士規劃-v0.4.md, slots from
tree_v04.py). Every place that reads a player's node by position is checked against it BY v0.4 NAME, so a read of
slot X that means node A while slot X now holds node B fails the build ("buying A activates B"):

  PAPYRUS  every Rank / Br / GetBranch / HasBranch / GetMainRank / GetMainPerk call in src/*.psc carries a
           `; @node 名稱` annotation on its (logical) line, one name per call in call order. A literal call
           (tree, route, tier[, slot]) must name the node that sits there; a call with a variable tree and literal
           route / tier / slot (the element skeleton) names it as `名稱{樹 樹 ...}` / `名稱{elements}` (`*` = the
           element's one-character name, ` / ` separates alternatives), and the listed trees must be exactly the
           element trees whose node at that position has that name. Calls with a
           variable route / tier / slot are only allowed in the tree infrastructure (INFRA below).
  DLL      build/fix19_native.NODE_IDENTITY maps every node:: constant the DLL reads to a v0.4 name; the slot the
           header gets is looked up by that name (fix20_reference.NODES is derived from it), and no C++ file may
           spell a NodeId / BranchId literal itself.
  ESP      build_v03.MAIN_ENTRY_NODES / BRANCH_ENTRY_NODES key every PERK entry point by v0.4 name; the readback
           must show entry points on exactly the perks those names resolve to.

and against the node status table (plan_coverage.NODES, keyed by (tree, v0.4 name)):
  * a node whose status is LATER-* (its slice is not live) must have no reader anywhere;
  * a node whose status says it works (DONE / KEPT-* / PARTIAL-*) must have at least one reader;
  * retired slots (v0.3 branches v0.4 removed) have no node, so reading one fails.

`self_test()` injects faults into copies of the sources and requires each one to be caught.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'build')]

READERS = ('Rank', 'Br', 'GetBranch', 'HasBranch', 'GetMainRank', 'GetMainPerk')
MAIN_READERS = {'Rank', 'GetMainRank', 'GetMainPerk'}
CANON = {r.lower(): r for r in READERS}   # Papyrus is case-insensitive: `rank(` and `ESSBNodes.BR(` are reads too
# Every other ESSBTrees function that takes a tree cell (tree, route, tier[, slot]) or touches the rank cache.
# Only the tree layer itself may call them (review round 21: a call like CachedBranch(3, 0, 0, 0) outside
# ESSBTrees would read a node by position with no annotation at all).
TREE_LAYER_FUNCS = ('CachedMainRank', 'CachedBranch', 'MainRankInternal', 'BranchInternal', 'NodeIndex', 'MainBase',
                    'BranchBase', 'ValidCell', 'CacheSlotOf', 'SlotFor', 'Bit')
TREE_LAYER_FIELDS = ('RankCacheA', 'RankCacheB', 'BranchCacheA', 'BranchCacheB', 'AllRankA', 'AllRankB',
                     'AllBranchA', 'AllBranchB')
# The only places outside ESSBTrees that may touch the cache: the two Controller wrappers and its declarations.
CACHE_OWNERS = {('ESSBController.psc', 'rank'), ('ESSBController.psc', 'br')}
# Tree arguments a skeleton read may use: the element's own tree, straight from the aiElement parameter.
SKELETON_TREE = re.compile(r'^(?:aiElement\s*-\s*1|(?:ESSBNodes\.)?TreeOf\(\s*aiElement\s*\))$', re.I)
# Perk FormIDs (branch block 0x2000.., main-line block 0x4000..) are derived only in ESSBTrees.
PERK_RANGE = (0x2000, 0x4000 + 195 * 15)
# Tree infrastructure: rank cache, respec, reconcile, the Rank/Br wrappers. Variable route / tier / slot is
# allowed only here (these functions touch every node, not one node).
INFRA = {
    'ESSBTrees.psc': None,   # the whole script is the tree layer (cache, respec, reconcile, CSF bridge)
    'ESSBNodes.psc': {'rank', 'br'},
    'ESSBController.psc': {'rank', 'br'},
}
ELEMENTS_TAG = 'elements'
WORKING = ('DONE', 'KEPT', 'PARTIAL')
STATUS_RE = re.compile(r'^(DONE|KEPT-(N[3-6]|待決)|PARTIAL-(N[3-6]|基礎|待決)|LATER-(N[3-6]|待決))$')


# ---------------------------------------------------------------- identity table


def load_plan():
    import plan_trees
    return plan_trees.apply_balance_text(plan_trees.parse())


def index(plan):
    """(tree index, route, tier, None) -> main node, (tree index, route, tier, slot) -> branch node,
    and (tree id, name) -> node. A node is a dict: tree, tree_index, route, tier, slot, name, kind, owner."""
    by_pos, by_name = {}, {}
    for tree in plan['trees']:
        for route in tree['routes']:
            for tier in route['tiers']:
                main = dict(tree=tree['id'], tree_index=tree['index'], route=route['index'], tier=tier['index'],
                            slot=None, name=tier['main_label'], kind='main', owner=tier['main_owner'],
                            text=tier['main_original'])
                by_pos[(tree['index'], route['index'], tier['index'], None)] = main
                by_name[(tree['id'], main['name'])] = main
                for b in tier['branches']:
                    node = dict(tree=tree['id'], tree_index=tree['index'], route=route['index'], tier=tier['index'],
                                slot=b['slot'], name=b['name'], kind='branch', owner=b['owner'],
                                text=b['description_original'])
                    by_pos[(tree['index'], route['index'], tier['index'], b['slot'])] = node
                    by_name[(tree['id'], b['name'])] = node
    return by_pos, by_name


def statuses(by_name):
    import plan_coverage
    table = plan_coverage.NODES
    missing = sorted(set(by_name) - set(table))
    extra = sorted(set(table) - set(by_name))
    errors = [f'plan_coverage.NODES has no row for {k}' for k in missing]
    errors += [f'plan_coverage.NODES row {k} is not a v0.4 node' for k in extra]
    for key, row in table.items():
        status = row[0]
        if not STATUS_RE.match(status):
            errors.append(f'plan_coverage.NODES {key}: bad status {status!r}')
        if len(row) != 3 or not row[1] or not row[2]:
            errors.append(f'plan_coverage.NODES {key}: needs (status, where, note)')
    return table, errors


def working(status):
    return status.split('-')[0] in WORKING


# ---------------------------------------------------------------- Papyrus scan


def strip_strings(line):
    return re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: '"' + ' ' * (len(m[0]) - 2) + '"', line)


def split_comment(line):
    """(code, comment) of a logical line; a ';' inside a string is not a comment."""
    masked = strip_strings(line)
    pos = masked.find(';')
    if pos < 0:
        return line, ''
    return line[:pos], line[pos + 1:]


def logical_lines(text):
    """Join Papyrus `\\` continuations. Yields (first physical line number, logical line)."""
    physical = text.splitlines()
    out, start, buf = [], None, []
    for number, raw in enumerate(physical, 1):
        code, _ = split_comment(raw)
        if start is None:
            start = number
        if code.rstrip().endswith('\\'):
            buf.append(code.rstrip()[:-1])
            continue
        buf.append(raw)
        out.append((start, ' '.join(buf)))
        start, buf = None, []
    if buf:
        out.append((start, ' '.join(buf)))
    return out


def call_args(code, open_paren):
    """Top-level comma split of the argument list starting at code[open_paren] == '('."""
    depth, args, current = 0, [], ''
    for pos in range(open_paren, len(code)):
        ch = code[pos]
        if ch == '(':
            depth += 1
            if depth == 1:
                continue
        elif ch == ')':
            depth -= 1
            if depth == 0:
                args.append(current.strip())
                return [a for a in args if a != ''] if args != [''] else [], pos
        elif ch == ',' and depth == 1:
            args.append(current.strip())
            current = ''
            continue
        current += ch
    raise ValueError(f'unbalanced call: {code[open_paren:]!r}')


CALL_RE = re.compile(r'(?<![A-Za-z0-9_])(' + '|'.join(READERS) + r')\s*\(', re.I)
LAYER_RE = re.compile(r'(?<![A-Za-z0-9_])(' + '|'.join(TREE_LAYER_FUNCS) + r')\s*\(', re.I)
FIELD_RE = re.compile(r'(?<![A-Za-z0-9_])(' + '|'.join(TREE_LAYER_FIELDS) + r')(?![A-Za-z0-9_])', re.I)
FUNC_RE = re.compile(r'^\s*(?:\w+(?:\[\])?\s+)?(?:Function|Event)\s+(\w+)\s*\(', re.I)
ANNOT_RE = re.compile(r'@node\s+(.+?)\s*$')
ITEM_RE = re.compile(r'^(.+?)(?:\{([^{}]*)\})?$')


def strip_docs(text):
    """Blank Papyrus `{...}` documentation blocks (they may span lines), keeping line numbers.
    A `{` inside a `;` comment (the `名稱{樹 ...}` annotations) or a string is not a doc block."""
    out, i, n = [], 0, len(text)
    in_comment = in_string = in_doc = False
    while i < n:
        ch = text[i]
        if in_doc:
            out.append('\n' if ch == '\n' else ' ')
            in_doc = ch != '}'
        elif ch == '\n':
            in_comment = in_string = False
            out.append(ch)
        elif in_comment:
            out.append(ch)
        elif in_string:
            out.append(ch)
            if ch == '\\' and i + 1 < n:
                out.append(text[i + 1])
                i += 1
            elif ch == '"':
                in_string = False
        elif ch == ';':
            in_comment = True
            out.append(ch)
        elif ch == '"':
            in_string = True
            out.append(ch)
        elif ch == '{':
            in_doc = True
            out.append(' ')
        else:
            out.append(ch)
        i += 1
    return ''.join(out)


def reads_in(name, text):
    """Every node read in one script: dicts with file, line, function, reader, args, annotation item."""
    text = strip_docs(text)
    reads, errors = [], []
    function, start = '', 0
    for number, line in logical_lines(text):
        code, comment = split_comment(line)
        m = FUNC_RE.match(code)
        if m:
            function, start = m.group(1), number
            if m.group(1).lower() in CANON:
                continue   # the definition of a reader, not a read
        masked = strip_strings(code)
        if name != 'ESSBTrees.psc':
            for lm in LAYER_RE.finditer(masked):
                errors.append(f'{name}:{number} ({function}): {lm.group(1)}( is a tree-layer function; only ESSBTrees '
                              'may call it (read nodes through ESSBNodes.Rank / Br with an @node name)')
            if (name, function.lower()) not in CACHE_OWNERS and not re.match(r'\s*Int\[\]\s+Property\b', code, re.I):
                for fm in FIELD_RE.finditer(masked):
                    errors.append(f'{name}:{number} ({function}): {fm.group(1)} is the tree layer\'s rank cache; '
                                  'only ESSBTrees and the Controller Rank / Br wrappers may touch it')
        calls = []
        for m in CALL_RE.finditer(masked):
            reader = CANON[m.group(1).lower()]
            args, _ = call_args(code, m.end() - 1)
            calls.append((reader, args))
        if not calls:
            continue
        annotation = ANNOT_RE.search(comment)
        items = [x.strip() for x in annotation.group(1).split(',')] if annotation else []
        where = f'{name}:{number} ({function})'
        need = []
        for reader, args in calls:
            parsed = classify_call(reader, args)
            if parsed is None:
                errors.append(f'{where}: cannot read the call {reader}({", ".join(args)})')
                continue
            if parsed['kind'] == 'infra':
                infra = INFRA.get(name, set())
                if infra is not None and function.lower() not in infra:
                    errors.append(f'{where}: {reader}({", ".join(args)}) has a variable route/tier/slot '
                                  'outside the tree infrastructure')
                continue
            need.append(parsed)
        if not need:
            continue
        if len(items) != len(need):
            errors.append(f'{where}: {len(need)} node read(s) but {len(items)} @node name(s): {line.strip()}')
            continue
        for parsed, item in zip(need, items):
            parsed.update(file=name, line=number, function=function, item=item, start=start, code=code)
            reads.append(parsed)
    return reads, errors


def literal(arg):
    return int(arg) if re.fullmatch(r'\d+', arg) else None


def classify_call(reader, args):
    """{kind: 'literal'|'skeleton'|'infra', main, tree, route, tier, slot}; None if the shape is unknown."""
    if reader in ('Rank', 'GetMainRank'):
        if len(args) == 4:
            args = args[1:]            # ESSBNodes.Rank(ctl, t, r, k)
        if len(args) != 3:
            return None
        t, r, k, n = args[0], args[1], args[2], None
    elif reader == 'GetMainPerk':
        if len(args) != 4:
            return None
        t, r, k, n = args[0], args[1], args[2], None
    else:  # Br / GetBranch / HasBranch
        if reader == 'Br' and len(args) == 5:
            args = args[1:]            # ESSBNodes.Br(ctl, t, r, k, n)
        if len(args) != 4:
            return None
        t, r, k, n = args
    main = reader in MAIN_READERS
    fixed = [literal(x) for x in (r, k)] + ([] if main else [literal(n)])
    if any(v is None for v in fixed):
        return dict(kind='infra')
    route, tier = fixed[0], fixed[1]
    slot = None if main else fixed[2]
    tree = literal(t)
    return dict(kind='literal' if tree is not None else 'skeleton', main=main, tree=tree, tree_expr=t,
                route=route, tier=tier, slot=slot, reader=reader)


ELEMENT_SHORT = ['火', '冰', '雷', '土', '風', '血', '聖', '毒', '水', '暗', '星']


def parse_item(item, element_ids):
    """An annotation item: a literal name, or for a skeleton read one or more alternatives
    `名稱{樹 樹 ...}` separated by ' / '. In a skeleton name `*` stands for the element's one-character name
    (火冰雷土風血聖毒水暗星), so `*印記持續{elements}` is 火印記持續 on fire, 冰印記持續 on frost ...
    Returns [(pattern, [tree ids] or None)]."""
    out = []
    for part in item.split(' / '):
        m = ITEM_RE.match(part.strip())
        label, scope = m.group(1).strip(), m.group(2)
        trees = None if scope is None else (element_ids if scope.strip() == ELEMENTS_TAG else scope.split())
        out.append((label, trees))
    return out


def expand(pattern, tree_index):
    return pattern.replace('*', ELEMENT_SHORT[tree_index]) if tree_index < 11 else pattern


class Unknown:
    pass


def tri(node, env):
    """Three-valued value of a condition AST: True / False / None (depends on something other than the element)."""
    import ast
    if isinstance(node, ast.BoolOp):
        vals = [tri(v, env) for v in node.values]
        if isinstance(node.op, ast.And):
            return False if False in vals else (True if all(v is True for v in vals) else None)
        return True if True in vals else (False if all(v is False for v in vals) else None)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        v = tri(node.operand, env)
        return None if v is None else not v
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        a, b = node.left, node.comparators[0]
        def val(x):
            if isinstance(x, ast.Constant) and isinstance(x.value, (int, float)):
                return x.value
            if isinstance(x, ast.Name) and x.id.lower() in env:
                return env[x.id.lower()]
            return Unknown
        va, vb = val(a), val(b)
        if va is Unknown or vb is Unknown:
            return None
        op = type(node.ops[0]).__name__
        return {'Eq': va == vb, 'NotEq': va != vb, 'Lt': va < vb, 'LtE': va <= vb, 'Gt': va > vb,
                'GtE': va >= vb}.get(op)
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return None


def condition(text, env):
    import ast
    code = re.sub(r'!(?!=)', ' not ', text.replace('&&', ' and ').replace('||', ' or '))
    code = re.sub(r'\b(True|False)\b', lambda m: m.group(1), code, flags=re.I)
    try:
        tree = ast.parse(code.strip(), mode='eval').body
    except SyntaxError:
        return None
    return tri(tree, env)


def conjunct_prefix(cond, call_at):
    """The top-level && terms of `cond` that come before the one containing position call_at (None if || at top)."""
    depth, terms, cur, pos0 = 0, [], '', 0
    i = 0
    while i < len(cond):
        ch = cond[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if depth == 0 and cond.startswith('||', i):
            return None
        if depth == 0 and cond.startswith('&&', i):
            terms.append((pos0, cur))
            cur, pos0 = '', i + 2
            i += 2
            continue
        cur += ch
        i += 1
    terms.append((pos0, cur))
    return [c for start, c in terms if start + len(c) < call_at]


def skeleton_reach(text, read, element_count=11):
    """Elements (1..11) for which the skeleton read can execute, from the If / ElseIf / Else / Return structure of
    its function (conditions on aiElement, and on the local tree variable, are decided; anything else is 'maybe').
    Returns (set, error or None)."""
    lines = logical_lines(strip_docs(text))
    body = [(n, split_comment(l)[0].strip()) for n, l in lines if read['start'] <= n <= read['line']]
    header = body[0][1]
    # The whole function (not only up to the read): an assignment after the read inside a loop still changes it.
    whole = []
    for n, l in lines:
        if n < read['start']:
            continue
        c = split_comment(l)[0].strip()
        whole.append(c)
        if re.match(r'End(?:Function|Event)\b', c, re.I):
            break
    ASSIGN = r'\s*(?:[-+*/]?=)(?!=)'   # plain and compound assignment (review round 21: `t += 1`)
    if not re.search(r'\bInt\s+aiElement\b', header, re.I):
        return set(), f'skeleton read in {read["function"]} but the function has no Int aiElement parameter'
    tree_var = None
    expr = read['tree_expr'].strip()
    if not SKELETON_TREE.match(expr):
        assigns = [c for c in whole[1:] if re.match(r'(?:Int\s+)?' + re.escape(expr) + ASSIGN, c, re.I)]
        plain = len(assigns) == 1 and re.match(r'(?:Int\s+)?' + re.escape(expr) + r'\s*=(?!=)', assigns[0], re.I)
        if not plain or not SKELETON_TREE.match(assigns[0].split('=', 1)[1].strip()):
            return set(), (f'skeleton read tree argument {expr!r} must be aiElement - 1 / TreeOf(aiElement), or a local '
                           'assigned exactly once from one of them')
        tree_var = expr.lower()
    if any(re.match(r'aiElement' + ASSIGN, c, re.I) for c in whole[1:]):
        return set(), 'skeleton read in a function that reassigns aiElement'
    reach = set()
    for e in range(1, element_count + 1):
        env = {'aielement': e}
        if tree_var:
            env[tree_var] = e - 1
        frames, dead = [], False
        for number, c in body[1:]:
            if number == read['line']:
                break
            low = c.lower()
            if low.startswith('if '):
                frames.append(dict(prev=[], cur=condition(c[3:], env)))
            elif low.startswith('elseif '):
                f = frames[-1]
                f['prev'].append(f['cur'])
                f['cur'] = False if True in f['prev'] else condition(c[7:], env)
            elif low == 'else':
                f = frames[-1]
                f['prev'].append(f['cur'])
                f['cur'] = False if True in f['prev'] else None
            elif low in ('endif', 'endwhile'):
                frames.pop()
            elif low.startswith('while '):
                frames.append(dict(prev=[], cur=condition(c[6:], env)))
            elif low.startswith('return') and all(f['cur'] is True for f in frames):
                dead = True
                break
        if dead or any(f['cur'] is False for f in frames):
            continue
        code = read['code'].strip()
        m = re.match(r'(?:If|ElseIf|While)\s+(.*)$', code, re.I)
        if m:
            at = CALL_RE.search(strip_strings(m.group(1)))
            terms = conjunct_prefix(m.group(1), at.start() if at else len(m.group(1)))
            if terms and any(condition(x, env) is False for x in terms):
                continue
        reach.add(e)
    return reach, None


def check_papyrus(sources, by_pos, by_name, table, tree_ids):
    """sources: {script file name: text}. Returns (reads, errors); each read resolved to node keys."""
    element_ids = tree_ids[:11]
    reads, errors = [], []
    for name, text in sorted(sources.items()):
        found, errs = reads_in(name, text)
        errors += errs
        for read in found:
            where = f'{read["file"]}:{read["line"]} ({read["function"]})'
            what = f'{"main" if read["main"] else "branch"} ({read["tree_expr"]}, {read["route"]}, {read["tier"]}'                    + ('' if read['main'] else f', {read["slot"]}') + ')'
            alternatives = parse_item(read['item'], element_ids)
            wanted = []   # (tree index, expected name)
            if read['kind'] == 'literal':
                if len(alternatives) != 1 or alternatives[0][1] is not None or '*' in alternatives[0][0]:
                    errors.append(f'{where}: literal {what} takes one plain name, got {read["item"]!r}')
                    continue
                wanted = [(read['tree'], alternatives[0][0])]
            else:
                if any(trees is None for _, trees in alternatives):
                    errors.append(f'{where}: skeleton read {what} needs `名稱{{樹 ...}}`: {read["item"]!r}')
                    continue
                reach, why = skeleton_reach(sources[read['file']], read)
                if why:
                    errors.append(f'{where}: {why}')
                    continue
                listed_idx = {tree_ids.index(t) + 1 for _, trees in alternatives for t in trees if t in tree_ids}
                if reach - listed_idx:
                    errors.append(f'{where}: skeleton read {what} can run for element(s) '
                                  f'{sorted(tree_ids[e - 1] for e in reach - listed_idx)} that its @node list does not '
                                  f'name (no aiElement guard excludes them)')
                listed = [t for _, trees in alternatives for t in trees]
                unknown = [t for t in listed if t not in element_ids]
                if unknown or len(set(listed)) != len(listed):
                    errors.append(f'{where}: unknown or repeated element tree(s) in {read["item"]!r}')
                    continue
                for pattern, trees in alternatives:
                    wanted += [(tree_ids.index(t), expand(pattern, tree_ids.index(t))) for t in trees]
                    # Exact list: every element tree whose node here matches this pattern is listed.
                    for t in range(11):
                        node = by_pos.get((t, read['route'], read['tier'], read['slot']))
                        if node is not None and node['name'] == expand(pattern, t) and tree_ids[t] not in listed:
                            errors.append(f'{where}: {tree_ids[t]} also has {node["name"]!r} at {what} but is not listed')
            resolved = []
            for t, label in wanted:
                node = by_pos.get((t, read['route'], read['tier'], read['slot']))
                if node is None:
                    errors.append(f'{where}: {tree_ids[t]} (tree {t}) {what} is not a v0.4 node (retired or empty '
                                  f'slot); annotation says {label!r}')
                    continue
                if node['name'] != label:
                    errors.append(f'{where}: {tree_ids[t]} (tree {t}) {what} is {node["name"]!r} in v0.4, '
                                  f'annotation says {label!r}')
                    continue
                if read['main'] != (node['kind'] == 'main'):
                    errors.append(f'{where}: {label!r} is a {node["kind"]}, read as {what}')
                    continue
                status = table.get((node['tree'], node['name']), ('?',))[0]
                if not working(status):
                    errors.append(f'{where}: reads {node["tree"]} {label!r} whose status is {status} '
                                  '(a later slice owns it; the old effect must be gone)')
                    continue
                resolved.append((node['tree'], node['name']))
            read['nodes'] = resolved
            reads.append(read)
    return reads, errors


def check_bases(sources):
    """Perk FormIDs are derived only inside the tree layer: outside ESSBTrees no hex literal anywhere, and no
    integer literal inside a GetFormFromFile call, may fall in the perk blocks (0x2000 .. 0x4B6D)."""
    errors = []
    lo, hi = PERK_RANGE
    for name, text in sources.items():
        if name == 'ESSBTrees.psc':
            continue
        for number, line in logical_lines(strip_docs(text)):
            code = strip_strings(split_comment(line)[0])
            bad = re.search(r'\b(MAIN_BASE|BRANCH_BASE)\b', code, re.I) is not None
            for m in re.finditer(r'\b0x([0-9A-Fa-f]+)\b', code):
                bad |= lo <= (int(m.group(1), 16) & 0xFFFFFF) < hi
            for m in re.finditer(r'GetFormFromFile\s*\(', code, re.I):
                args, _ = call_args(code, m.end() - 1)
                for lit in re.finditer(r'(?<![\w.])(\d+)(?![\w.])', args[0] if args else ''):
                    bad |= lo <= int(lit.group(1)) < hi
            if bad:
                errors.append(f'{name}:{number}: perk FormID arithmetic outside ESSBTrees: {line.strip()}')
    return errors


# ---------------------------------------------------------------- DLL


ELEMENT_CONSTANTS = {name: i for i, name in enumerate(
    ['kFire', 'kFrost', 'kLightning', 'kEarth', 'kWind', 'kBlood', 'kDivine', 'kPoison', 'kWater', 'kDarkness', 'kAstral'],
    1)}


def check_dll(identity, by_name, table, tree_ids, native_sources, arrays=None):
    """identity: {constant: (tree id, v0.4 name)} (fix19_native.NODE_IDENTITY); arrays: {table: [element] (tree id,
    v0.4 name) or None} (fix19_native.ARRAY_IDENTITY, round 22). A C++ read node::kTable[kElement] registers that
    element's node; node::kTable[anything else] registers every element's. Returns (slots, readers, errors)."""
    errors, slots, readers = [], {}, collections.defaultdict(list)
    arrays = arrays or {}
    for table_name, cells in arrays.items():
        for cell in cells:
            if cell is not None and by_name.get(cell) is None:
                errors.append(f'DLL node::{table_name}: {cell[0]} has no v0.4 node {cell[1]!r}')
    for constant, (tree, name) in identity.items():
        node = by_name.get((tree, name))
        if node is None:
            errors.append(f'DLL node::{constant}: {tree} has no v0.4 node {name!r}')
            continue
        status = table.get((tree, name), ('?',))[0]
        if not working(status):
            errors.append(f'DLL node::{constant} reads {tree} {name!r} whose status is {status}')
        pos = (node['tree_index'], node['route'], node['tier']) + (() if node['slot'] is None else (node['slot'],))
        slots[constant] = pos
        readers[(tree, name)].append(f'DLL node::{constant}')
    for path, text in native_sources.items():
        if path.endswith('ManifestData.h'):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            code = re.sub(r'//.*', '', line).strip()
            if not code:
                continue
            allowed = CPP_ALLOWED.get((path.rsplit('/', 1)[-1], code))
            if allowed:
                continue
            if CPP_NODE_BUILD.search(code):
                errors.append(f'{path}:{number}: a node slot built in C++ instead of generated by name: {line.strip()}')
            if CPP_POSITION.search(code):
                errors.append(f'{path}:{number}: node position / perk array indexed in C++ outside the reviewed sites: '
                              f'{line.strip()}')
        for m in re.finditer(r'node::(k\w+)', text):
            if m.group(1) not in identity and m.group(1) not in arrays and m.group(1) != 'kNoNode':
                errors.append(f'{path}: node::{m.group(1)} is not in NODE_IDENTITY or ARRAY_IDENTITY')
        for m in re.finditer(r'node::(k\w+)\[\s*(?:essb::)?(\w+)\s*\]', text):
            cells = arrays.get(m.group(1))
            if cells is None:
                continue
            element = ELEMENT_CONSTANTS.get(m.group(2))
            hit = [cells[element]] if element is not None else cells
            for cell in hit:
                if cell is None:
                    if element is not None:
                        errors.append(f'{path}: node::{m.group(1)}[{m.group(2)}] reads a tree without that line')
                    continue
                status = table.get(cell, ('?',))[0]
                if not working(status):
                    errors.append(f'DLL node::{m.group(1)}[{m.group(2)}] reads {cell[0]} {cell[1]!r} whose status is '
                                  f'{status}')
                where = f'DLL node::{m.group(1)}[{m.group(2)}]'
                if where not in readers[cell]:
                    readers[cell].append(where)
    return slots, readers, errors


# NodeId / BranchId may be constructed or initialised only in the generated ManifestData.h; positions and the perk
# arrays are indexed only at the reviewed sites below (exact line text -> why).
CPP_NODE_BUILD = re.compile(r'\b(?:NodeId|BranchId)\s*[{(]|\b(?:NodeId|BranchId)\s+\w+\s*[{=]'
                            r'|^(?:static\s+|inline\s+|constexpr\s+)*(?:essb::)?(?:NodeId|BranchId)\s+\w+\s*\(')
CPP_POSITION = re.compile(r'\bNodeIndex\s*\(|\b(?:mainPerks|branchPerks)\s*\[|\b(?:main|branch)\s*\[\s*localId')
CPP_ALLOWED = {
    ('NodeIds.h', 'inline constexpr NodeId kNoNode{ -1, -1, -1 };'): 'the "no node" sentinel',
    ('NodeIds.h', 'struct NodeId {'): 'the type', ('NodeIds.h', 'struct BranchId {'): 'the type',
    ('EngineFacts.h', 'constexpr int NodeIndex(int tree, int route, int tier) noexcept'): 'the definition',
    ('EngineFacts.h', 'inline constexpr int kNodeCount = NodeIndex(kTreeCount - 1, 2, 4) + 1;'): 'array size (195)',
    ('EngineFacts.h', 'return kMainPerkBase + static_cast<std::uint32_t>(NodeIndex(id.tree, id.route, id.tier) * kMainMaxRank + rank - 1);'): 'FormID of a generated NodeId',
    ('EngineFacts.h', 'return kBranchPerkBase + static_cast<std::uint32_t>(NodeIndex(id.tree, id.route, id.tier) * kBranchSlots + id.index);'): 'FormID of a generated BranchId',
    ('EngineFacts.h', 'auto& cached = ranks_[NodeIndex(id.tree, id.route, id.tier)];'): 'per-hit cache of a generated NodeId',
    ('EngineFacts.h', 'auto& cached = branches_[NodeIndex(id.tree, id.route, id.tier) * kBranchSlots + id.index];'): 'per-hit cache of a generated BranchId',
    ('Plugin.cpp', 'f.mainPerks[i] = Resolve<RE::BGSPerk>(data, essb::kMainPerkBase + static_cast<std::uint32_t>(i), kPlugin, "main-line perk");'): 'load-time resolve of every main-line perk',
    ('Plugin.cpp', 'f.branchPerks[i] = data.LookupForm<RE::BGSPerk>(essb::kBranchPerkBase + static_cast<std::uint32_t>(i), kPlugin);'): 'load-time resolve of every branch perk',
    ('Plugin.cpp', 'perk = main[localId - essb::kMainPerkBase];'): 'HasPerk by a FormID computed from a generated id',
    ('Plugin.cpp', 'perk = branch[localId - essb::kBranchPerkBase];'): 'HasPerk by a FormID computed from a generated id',
    ('hit_pipeline_test.cpp', 'essb::NodeId NodeOf(const json& slot)'): 'test: slot read from the generated wiring json',
    ('hit_pipeline_test.cpp', 'essb::BranchId BranchOf(const json& slot)'): 'test: slot read from the generated wiring json',
    ('hit_pipeline_test.cpp', 'const essb::NodeId id = NodeOf(wiring.at("slots").at(name));'): 'test: generated slot',
    ('hit_pipeline_test.cpp', 'const essb::BranchId id = BranchOf(wiring.at("slots").at(name));'): 'test: generated slot',
}


# ---------------------------------------------------------------- ESP


def check_esp(main_nodes, branch_nodes, by_name, table):
    """main_nodes / branch_nodes: iterables of (tree id, v0.4 name) that carry PERK entry points."""
    errors, readers = [], collections.defaultdict(list)
    for kind, keys in (('main', main_nodes), ('branch', branch_nodes)):
        for tree, name in keys:
            node = by_name.get((tree, name))
            if node is None:
                errors.append(f'ESP {kind} entry points keyed {tree} {name!r}: not a v0.4 node')
                continue
            if node['kind'] != kind:
                errors.append(f'ESP {kind} entry points keyed {tree} {name!r}: that node is a {node["kind"]}')
                continue
            status = table.get((tree, name), ('?',))[0]
            if not working(status):
                errors.append(f'ESP entry points on {tree} {name!r} whose status is {status}')
            readers[(tree, name)].append('ESP PERK entry point')
    return readers, errors


# ---------------------------------------------------------------- whole check


def scripts():
    return {p.name: p.read_text(encoding='utf-8') for p in sorted((ROOT / 'src').glob('*.psc'))}


def native_sources():
    out = {}
    for part in ('include', 'src', 'tests'):
        for p in sorted((ROOT / 'native' / part).rglob('*')):
            if p.suffix in ('.h', '.hpp', '.cpp'):
                out[p.relative_to(ROOT).as_posix()] = p.read_text(encoding='utf-8')
    return out


def run_checks(plan, sources, identity, esp_main, esp_branch, native, arrays=None, **_helpers):
    """_helpers: lookup tables self_test carries next to the inputs; not inputs of the check."""
    tree_ids = [t['id'] for t in plan['trees']]
    by_pos, by_name = index(plan)
    table, errors = statuses(by_name)
    # round 24: after N5 no -N5 / LATER branch is left, so the self test marks one node LATER itself (never in production)
    if _helpers.get('status_override'):
        table = dict(table)   # a copy: the production table (plan_coverage.NODES) is never touched
        for key, status in _helpers['status_override'].items():
            table[key] = (status,) + tuple(table[key])[1:]
    reads, errs = check_papyrus(sources, by_pos, by_name, table, tree_ids)
    errors += errs
    errors += check_bases(sources)
    _slots, dll_readers, errs = check_dll(identity, by_name, table, tree_ids, native, arrays)
    errors += errs
    esp_readers, errs = check_esp(esp_main, esp_branch, by_name, table)
    errors += errs
    readers = collections.defaultdict(list)
    for read in reads:
        for key in read['nodes']:
            readers[key].append(f'{read["file"]}:{read["line"]} {read["function"]}')
    for key, where in list(dll_readers.items()) + list(esp_readers.items()):
        readers[key] += where
    for key, row in table.items():
        if key in by_name and working(row[0]) and not readers.get(key):
            errors.append(f'{key[0]} {key[1]!r} is {row[0]} but nothing reads it (Papyrus, DLL or ESP)')
    return dict(reads=reads, readers=readers, table=table, by_name=by_name, by_pos=by_pos), errors


def current(b=None):
    """The production inputs (build_v03 module b supplies the ESP keys; fix19_native the DLL identity)."""
    import fix19_native
    if b is None:
        import build_v03 as b
    return dict(plan=load_plan(), sources=scripts(), identity=fix19_native.NODE_IDENTITY,
                esp_main=list(b.MAIN_ENTRY_NODES), esp_branch=list(b.BRANCH_ENTRY_NODES), native=native_sources(),
                arrays=fix19_native.ARRAY_IDENTITY)


def self_test(inputs):
    """Injected faults; each must produce an error that names it."""
    import copy
    cases = []

    def expect(label, mutate, needle):
        data = copy.deepcopy(inputs)
        mutate(data)
        _, errors = run_checks(**data)
        hit = [e for e in errors if needle in e]
        assert hit, (label, 'fault not caught', errors[:5])
        cases.append(label)

    def later_key(data, branch=True, element=True):
        """A node whose slice is not live: a real LATER one if any is left, else (round 24: every N5 node landed) a
        working node marked LATER for this injected fault only."""
        def fits(k):
            return (not branch or data['kinds'][k] == 'branch') and (not element or data['trees'].index(k[0]) < 11)
        key = next((k for k, v in data['plan_status'].items() if v.startswith('LATER') and fits(k)), None)
        if key is None:
            key = next(k for k in data['plan_status'] if fits(k))
            data['status_override'] = {key: 'LATER-N6'}
            data['plan_status'] = {**data['plan_status'], key: 'LATER-N6'}
        return key

    def first_read(data, script):
        text = data['sources'][script]
        m = re.search(r'ESSBNodes\.Br\(akCtl, (\d+), (\d+), (\d+), (\d+)\)[^\n]*; @node ([^\n,]+)', text)
        return text, m

    # round 24: the fire / frost / lightning branch reads left ESSBElem.psc with the reaction bodies (native/include/
    # Reactions.h); the same faults are injected into the first branch read left in Papyrus (ESSBElem2.psc).
    def swap_name(data):   # annotation names a different node of the same tree
        text, m = first_read(data, 'ESSBElem2.psc')
        data['sources']['ESSBElem2.psc'] = text[:m.start(5)] + '溫血' + text[m.end(5):]
    expect('annotation names another node', swap_name, "annotation says '溫血'")

    def slot_shift(data):  # the call reads the neighbouring slot, annotation unchanged
        text, m = first_read(data, 'ESSBElem2.psc')
        data['sources']['ESSBElem2.psc'] = text[:m.start(4)] + str(int(m.group(4)) + 1) + text[m.end(4):]
    expect('read shifted to another slot', slot_shift, 'annotation says')

    def unannotated(data):
        text = data['sources']['ESSBElem2.psc']
        data['sources']['ESSBElem2.psc'] = re.sub(r'\s*; @node [^\n]+', '', text, count=1)
    expect('read without annotation', unannotated, '@node name(s)')

    def retired(data):     # a read of a retired v0.3 slot (fire 關閉新手 slot 1, 洩壓)
        data['sources']['ESSBElem.psc'] += '\nFunction Probe21(ESSBController akCtl) Global\n\tBool x = ESSBNodes.Br(akCtl, 0, 2, 0, 1) ; @node 洩壓\nEndFunction\n'
    expect('read of a retired slot', retired, 'not a v0.4 node')

    def later(data):       # a read of a node whose slice is not live
        key = later_key(data)
        node = data['nodes'][key]
        data['sources']['ESSBElem.psc'] += (f'\nFunction Probe21(ESSBController akCtl) Global\n\tBool x = ESSBNodes.Br(akCtl, '
                                           f'{node["tree_index"]}, {node["route"]}, {node["tier"]}, {node["slot"]}) ; @node {key[1]}\nEndFunction\n')
    expect('read of a LATER node', later, 'a later slice owns it')

    def skeleton_list(data):   # skeleton read claims a tree that has another node there
        text = data['sources']['ESSBElem.psc']
        # round 22: the takeover line moved to the DLL; round 24: the signature list went with the end bodies -- the
        # advent radius is the Papyrus skeleton read left (fire's slot there is 火臨, not 地臨)
        m = re.search(r'/ 地臨\{([^}]*)\}', text)
        text = text[:m.start(1)] + m.group(1) + ' fire' + text[m.end(1):]
        data['sources']['ESSBElem.psc'] = text.replace('*臨{fire ', '*臨{', 1)   # fire moves to the 地臨 list
    expect('skeleton tree list includes a tree with a different node', skeleton_list, "fire (tree")

    def skeleton_missing(data):   # skeleton list omits a tree that has the node
        text = data['sources']['ESSBElem.psc']
        m = re.search(r'@node \*臨\{([^}]*)\}', text)
        data['sources']['ESSBElem.psc'] = text[:m.start(1)] + m.group(1).replace('frost ', '').strip() + text[m.end(1):]
    expect('skeleton tree list omits a tree', skeleton_missing, 'but is not listed')

    def dll_wrong(data):
        name = next(iter(data['identity']))
        data['identity'][name] = (data['identity'][name][0], '不存在的節點')
        return name
    expect('DLL constant names a node that does not exist', dll_wrong, 'has no v0.4 node')

    def dll_literal(data):
        path = next(p for p in data['native'] if p.endswith('HitMath.h'))
        data['native'][path] += '\ninline constexpr NodeId kSneaky{11, 1, 0};\n'
    expect('C++ spells a slot literal', dll_literal, 'built in C++')

    def dll_array_later(data):   # round 22: a per-element table read reaches a node whose slice is not live
        key = later_key(data, branch=False)
        data['arrays'] = dict(data['arrays'] or {}, kProbe22=[None, key] + [None] * 10)
        path = next(p for p in data['native'] if p.endswith('HitMath.h'))
        data['native'][path] += '\nconst auto probe22 = node::kProbe22[kFire];\n'
    expect('DLL table read of a LATER node', dll_array_later, 'node::kProbe22[kFire] reads')

    def esp_later(data):
        key = later_key(data, element=False)
        data['esp_branch'].append(key)
    expect('ESP entry point on a LATER node', esp_later, 'ESP entry points on')

    def unread(data):      # a working node loses its only reader
        key = next(k for k in data['esp_branch'] if len(data['readers'].get(k, [])) == 1)
        data['esp_branch'].remove(key)
    expect('working node with no reader', unread, 'nothing reads it')

    def perk_math(data):
        # round 24: ESSBGuard.psc is deleted; any script but ESSBTrees carries the fault
        data['sources']['ESSBInput.psc'] += '\n; x\nFunction Probe21()\n\tForm f = Game.GetFormFromFile(0x2034, "x")\nEndFunction\n'
    expect('perk FormID arithmetic outside ESSBTrees', perk_math, 'outside ESSBTrees')

    # ---- review round 21: the reviewer's escapes, each one must now be caught
    def add(data, script, body):
        data['sources'][script] += '\nFunction Probe21(ESSBController akCtl, Int aiElement) Global\n' + body + '\nEndFunction\n'

    def lowercase(data):   # Papyrus is case-insensitive: a lower-case read of a LATER node
        key = later_key(data, element=False)
        node = data['nodes'][key]
        add(data, 'ESSBElem.psc', f'\tBool x = essbnodes.br(akCtl, {node["tree_index"]}, {node["route"]}, {node["tier"]}, {node["slot"]})')
    expect('lower-case reader call', lowercase, '@node name(s)')

    def layer_call(data):  # a tree-layer function called outside ESSBTrees
        add(data, 'ESSBElem.psc', '\tBool x = akCtl.Trees.CachedBranch(0, 2, 0, 1)')
    expect('ESSBTrees.CachedBranch called outside the tree layer', layer_call, 'is a tree-layer function')

    def internal_call(data):
        add(data, 'ESSBInput.psc', '\tInt x = akCtl.Trees.mainrankinternal(3, 0, 2)')
    expect('ESSBTrees.MainRankInternal (lower case) outside the tree layer', internal_call, 'is a tree-layer function')

    def cache_read(data):  # the rank cache read directly
        add(data, 'ESSBElem2.psc', '\tInt x = akCtl.RankCacheA[47]')
    expect('rank cache read outside the wrappers', cache_read, "rank cache")

    def hex_sum(data):     # perk FormID built from a hex base plus an offset
        add(data, 'ESSBInput.psc', '\tForm f = Game.GetFormFromFile(0x002000 + 52, "Elements Spellblade.esp")')
    expect('perk FormID from hex base + offset', hex_sum, 'outside ESSBTrees')

    def decimal_id(data):  # perk FormID as a decimal literal
        add(data, 'ESSBInput.psc', '\tForm f = Game.GetFormFromFile(8244, "Elements Spellblade.esp")')
    expect('perk FormID as a decimal literal', decimal_id, 'outside ESSBTrees')

    def skeleton_expr(data):   # skeleton read with a tree argument that is not the element's own tree
        add(data, 'ESSBElem.psc', '\tInt x = ESSBNodes.Rank(akCtl, aiElement, 1, 4) ; @node 開印效果{elements}')
    expect('skeleton read on aiElement instead of aiElement - 1', skeleton_expr, 'must be aiElement - 1')

    def skeleton_var(data):    # variable tree with a literal-looking annotation
        add(data, 'ESSBElem.psc', '\tInt t = 3\n\tInt x = ESSBNodes.Rank(akCtl, t, 0, 2) ; @node 命中削減目標耐力')
    expect('variable tree argument with a plain @node name', skeleton_var, 'needs `名稱{樹 ...}`')

    def skeleton_array(data):  # array element as tree argument, annotated as a skeleton
        add(data, 'ESSBElem.psc', '\tInt[] ts = new Int[2]\n\tInt x = ESSBNodes.Rank(akCtl, ts[1], 1, 4) ; @node 開印效果{elements}')
    expect('array tree argument', skeleton_array, 'must be aiElement - 1')

    # Round 22 moved the guarded skeleton reads these three cases mutated (印記持續 / 開印效果) into the DLL, so they
    # now inject a probe that has the same shape as the production reads (a subset list behind an aiElement guard,
    # the tree from ESSBNodes.TreeOf) and break it the same way.
    probe_guard = 'If aiElement == 2 || aiElement == 3'
    probe = ('\nFloat Function Probe22(ESSBController akCtl, Int aiElement) Global\n'
             '\tIf aiElement == 2 || aiElement == 3\n'
             '\t\tReturn ESSBNodes.Rank(akCtl, aiElement - 1, 2, 4) ; @node 碎冰{frost} / 放電{lightning}\n'
             '\tEndIf\n\tReturn 0.0\nEndFunction\n')
    probe_tree = ('\nFloat Function Probe22Tree(ESSBController akCtl, Int aiElement) Global\n'
                  '\tInt tree = ESSBNodes.TreeOf(aiElement)\n'
                  '\tReturn 1.0 + ESSBNodes.Pct(akCtl, ESSBNodes.Rank(akCtl, tree, 2, 0), 0.02) ; @node 終焉{elements}\n'
                  'EndFunction\n')

    def probe_clean(data):   # the probes as written are accepted (so the three faults below are the only errors)
        data['sources']['ESSBElem.psc'] += probe + probe_tree
    _, clean = run_checks(**(lambda d: (probe_clean(d), d)[1])(copy.deepcopy(inputs)))
    assert not [e for e in clean if 'Probe22' in e], clean

    def skeleton_guard(data):  # R2-style: the subset list is right but the aiElement guard is gone
        data['sources']['ESSBElem.psc'] += probe.replace(probe_guard, 'If aiElement > 0', 1)
    expect('skeleton subset read without its aiElement guard (the R2 bug)', skeleton_guard, 'can run for element(s)')

    def compound_element(data):   # aiElement changed inside the guard (review round 21 escape)
        data['sources']['ESSBElem.psc'] += probe.replace(probe_guard, probe_guard + '\n\t\taiElement += 1', 1)
    expect('aiElement += 1 inside the skeleton guard', compound_element, 'reassigns aiElement')

    def compound_tree(data):      # the local tree variable bumped after its single assignment
        data['sources']['ESSBElem.psc'] += probe_tree.replace('TreeOf(aiElement)\n', 'TreeOf(aiElement)\n\ttree += 1\n', 1)
    expect('t += 1 on the skeleton tree variable', compound_tree, 'assigned exactly once')

    def cpp_init(data):        # C++ builds a slot by aggregate initialisation
        path = next(p for p in data['native'] if p.endswith('HitMath.h'))
        data['native'][path] += '\nconstexpr essb::BranchId kSneaky2 = { 11, 1, 0, 0 };\n'
    expect('C++ BranchId initialised outside ManifestData.h', cpp_init, 'built in C++')

    def cpp_return(data):      # C++ function returning a hand-made NodeId
        path = next(p for p in data['native'] if p.endswith('HitMath.h'))
        data['native'][path] += '\nconstexpr NodeId Sneaky(int t)\n{\n    return { t, 0, 1 };\n}\n'
    expect('C++ function returning a NodeId', cpp_return, 'built in C++')

    def cpp_index(data):       # C++ indexes the perk array or NodeIndex directly
        path = next(p for p in data['native'] if p.endswith('Plugin.cpp'))
        data['native'][path] += '\nauto* sneaky = state.forms.branchPerks[NodeIndex(11, 1, 0) * 4];\n'
    expect('C++ perk array / NodeIndex indexing', cpp_index, 'indexed in C++')
    return cases


def run(b=None):
    inputs = current(b)
    result, errors = run_checks(**inputs)
    if errors:
        raise SystemExit('FIX21 IDENTITY failed:\n  ' + '\n  '.join(errors))
    # The self-test needs a few lookup tables next to the inputs (ignored by run_checks).
    helper = dict(inputs)
    helper['plan_status'] = {k: v[0] for k, v in result['table'].items()}
    helper['kinds'] = {k: n['kind'] for k, n in result['by_name'].items()}
    helper['nodes'] = result['by_name']
    helper['trees'] = [t['id'] for t in inputs['plan']['trees']]
    helper['readers'] = dict(result['readers'])

    cases = self_test(helper)
    reads = result['reads']
    literal_reads = sum(1 for r in reads if r['kind'] == 'literal')
    skeleton_reads = sum(1 for r in reads if r['kind'] == 'skeleton')
    counts = collections.Counter(v[0].split('-')[0] for v in result['table'].values())
    report = dict(papyrus_reads=len(reads), literal=literal_reads, skeleton=skeleton_reads,
                  dll_constants=len(inputs['identity']), esp_main=len(inputs['esp_main']),
                  esp_branch=len(inputs['esp_branch']), statuses=dict(sorted(counts.items())), self_test=cases,
                  readers={f'{k[0]} {k[1]}': v for k, v in sorted(result['readers'].items())})
    (ROOT / 'build/fix21-identity.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'FIX21 IDENTITY ok: {len(reads)} Papyrus node reads by v0.4 name ({literal_reads} literal, {skeleton_reads} '
          f'element-skeleton), {len(inputs["identity"])} DLL constants, {len(inputs["esp_main"])}+{len(inputs["esp_branch"])} '
          f'ESP entry-point nodes; statuses {dict(sorted(counts.items()))}; no LATER node read, every working node read; '
          f'{len(cases)}/{len(cases)} injected faults caught')
    return report


if __name__ == '__main__':
    run()
