"""Round 27e (0.27.4): player-facing text without the design document's annotations.

The tree generator copies 元素魔戰士規劃-v0.4.md's cells verbatim, and the document carries notes for its readers
(「（2026-09-27 依實作：…）」, 待決, 指揮官裁定, v0.3 / v0.4, round numbers, file names, 探針, 實作紀錄, 自有). player_text() drops
every parenthetical group that holds such a marker and keeps the gameplay text; markers() finds any left, and
build/fix27_verify.py fails the build when a perk name / description, a Custom Skills file or the MCM config still has one.
"""
from __future__ import annotations

import re

MARKER = re.compile(
    r'20\d\d-\d\d-\d\d|依實作|待決|指揮官|裁定|已決|[vV]0\.\d|[Rr]ound\s?\d|探針|實作紀錄|規劃文件|native-verification|'
    r'[A-Za-z0-9_]+\.(?:md|py|h|cpp|psc|json|esp|esm|log)\b|HitMath|Status\.h|Reactions\.h|Plugin\.cpp|'
    # round 28c: the document's markdown and its change notes -- 「**粗體**」, `code`, 「原「…」」, section references 「見 2.4」
    r'\*|`|原「|見\s?\d+\.\d+|'
    # round 28d: 「（自有）」「（自有，可調）」「（自有效果把耐力回復設 0）」 tell the document's readers how a node is built
    # (our own effect, not a vanilla one); the player only needs the rule
    r'自有')

_OPEN = '（('
_CLOSE = '）)'


# Round 28c: an override replaces the player text of ONE node, named by its perk (the EditorID without the rank:
# ESSB_P_<tree>_<route>_<tier>_M for a main line, ..._B<slot + 1> for a branch). Each entry pins the node's v0.4 name
# and the sha256 (first 16 hex) of the v0.4 text it was written against: when the document's wording of that node changes,
# node_text() fails the build (StaleOverride) instead of silently falling back to the document text, and check_overrides()
# fails on an entry whose node no longer exists. Round 27e keyed these by the cleaned text, so 1b62153's rewrite of
# 水臨強化 and 印潮 dropped them without a word. After a document change: read the new text, update the player text if the
# rule changed, then put the new digest here (the error prints it).
OVERRIDES = {
    # A note that corrected the number itself: stripping it would leave the document's old number, so the player text
    # states what the game does (the DLL's HitMath: 3 × points × G(L) of the target's stamina).
    'ESSB_P_earth_0_2_M': ('命中削減目標耐力', 'ef47131b17a27373',
                           '命中削減目標耐力：削減量＝3 × 點數 × G(L)'),
    # Round 28 (D3) / 28b (F7, the user's rulings 2026-09-28): 25% of max magicka, only with a hostile in range, 10 s cooldown.
    'ESSB_P_water_1_2_B1': ('水臨強化', '07665dc19db2f0b7',
                            '水臨強化：水臨時範圍內有敵人才發動：範圍內敵人浸濕，你立即淨化（清除全部負面效果）並回復最大魔力 25%'
                            '（受回復倍率影響）；冷卻 10 秒：發動後 10 秒內再開水形態或切到水不會再發動'),
    # Round 28b (F5, the user's ruling 2026-09-28): the new 印潮.
    'ESSB_P_common_1_3_B3': ('印潮', 'de38b9b688b15706',
                             '印潮：切換形態後的第一擊開印時，那個目標 15 公尺內身上沒有任何印記的其他敵人（最近的最多 2 人）也掛上新元素的印記；'
                             '不會切換任何人已有的印記'),
    # Round 28 (the user's ruling 2026-09-28): a wind-form sneak attack that kills outright counts as marked.
    'ESSB_P_wind_2_4_B2': ('連殺', 'e84dee317de349f8',
                           '連殺：帶風印記的目標被你的潛行攻擊殺死後 5 秒內不解除潛行，下一次潛行攻擊附傷 ×2 並重置奇襲；'
                           '風形態下潛行攻擊一擊直接殺死的目標也算帶印'),
    # Round 28d: the document's sentence runs 「（含武器傷害）只要點了此節點即生效」 together; the player text adds the comma
    # (the 「（自有）」 note and the markdown go as they would through player_text).
    'ESSB_P_wind_0_4_B1': ('御風', '91c74e15eaadc238',
                           '御風：同調三段時免疫減速；失衡目標受你所有傷害 +30%（含武器傷害），只要點了此節點即生效，不需同調三段'),
}


class StaleOverride(AssertionError):
    pass


def digest(source: str) -> str:
    import hashlib
    return hashlib.sha256((source or '').encode('utf-8')).hexdigest()[:16]


def markers(text: str) -> list[str]:
    return MARKER.findall(text or '')


def player_text(text: str) -> str:
    """The text without the document's markdown emphasis and with every parenthetical note that carries a marker removed
    (innermost first, repeated). No override here: a node's override goes through node_text()."""
    if not text:
        return text
    out = text.replace('**', '')   # round 28c: markdown bold is emphasis for the document's readers, not text
    while True:
        changed = False
        stack = []
        for i, ch in enumerate(out):
            if ch in _OPEN:
                stack.append(i)
            elif ch in _CLOSE and stack:
                start = stack.pop()
                inner = out[start + 1:i]
                if MARKER.search(inner):   # inner groups closed first; a group with a marker goes whole (nested ones too)
                    out = out[:start] + out[i + 1:]
                    changed = True
                    break
        if not changed:
            break
    return re.sub(r'[ 　]{2,}', ' ', out).strip()


def node_text(node: str, name: str, source: str, overrides=None) -> str:
    """The player text of one perk node: its override when it has one (checked against the node's name and v0.4 text),
    else player_text(source)."""
    table = OVERRIDES if overrides is None else overrides
    if node not in table:
        return player_text(source)
    want_name, want_digest, text = table[node]
    if name != want_name:
        raise StaleOverride(f'fix27_text.OVERRIDES[{node!r}] is for 「{want_name}」 but the node is now 「{name}」')
    if digest(source) != want_digest:
        raise StaleOverride(f'fix27_text.OVERRIDES[{node!r}]（{name}）: the v0.4 text changed (digest {digest(source)}, '
                            f'override written for {want_digest}); review the player text against: {source}')
    return text


def plan_nodes(plan):
    """{node: (name, source text)} for every main line and branch of the plan (build/plan-tree-nodes.json)."""
    nodes = {}
    for tree in plan['trees']:
        for route in tree['routes']:
            for tier in route['tiers']:
                stem = f"ESSB_P_{tree['id']}_{route['index']}_{tier['index']}"
                nodes[f'{stem}_M'] = (tier['main_label'], tier['main'])
                for branch in tier['branches']:
                    nodes[f"{stem}_B{branch['slot'] + 1}"] = (branch['name'], branch['description'])
    return nodes


def check_overrides(plan, overrides=None):
    """Errors for every override whose node is gone, renamed or rewritten in v0.4, and for an override that still carries a
    design marker itself."""
    table = OVERRIDES if overrides is None else overrides
    nodes = plan_nodes(plan)
    errors = []
    for node, (name, _digest, text) in table.items():
        if node not in nodes:
            errors.append(f'fix27_text.OVERRIDES[{node!r}]（{name}）: no such node in the plan')
            continue
        try:
            node_text(node, *nodes[node], overrides=table)
        except StaleOverride as e:
            errors.append(str(e))
        if markers(text):
            errors.append(f'fix27_text.OVERRIDES[{node!r}]: design note {markers(text)} in the override')
    return errors


# ---------------------------------------------------------------- the build check (build/fix27_verify.py)

# A string that is a form reference or an identifier (no player text): "Plugin.esp|00ABCD", "0xABCD~Plugin.esp", an ID.
_REFERENCE = re.compile(r'^[^|]+\.(esp|esm)\|[0-9A-Fa-f]+$|^0x[0-9A-Fa-f]+~[^~]+\.(esp|esm)$|^[A-Za-z0-9_$.:/ -]+$')


def _strings(value, path='', owner=''):
    if isinstance(value, dict):
        owner = value.get('id', owner) if isinstance(value.get('id'), str) else owner
        for k, v in value.items():
            yield from _strings(v, f'{path}/{k}', owner)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _strings(v, f'{path}[{i}]', owner)
    elif isinstance(value, str):
        yield path, value, owner


# The MCM debug-level control is the testers' tool: its option「4：探針 log」names the probe log on purpose (the sheet and
# build/fix26_verify.py read that label) and tells where the log is. Only those two are allowed there.
EXEMPT = {'ESSB_DebugLevel': {'探針', 'ElementsSpellblade.log'}}   # the probe log's label and where to find the log


def scan_json(path):
    """[(json path, markers, text)] for every player-visible string of a JSON file (form references and IDs skipped)."""
    import json
    found = []
    for where, text, owner in _strings(json.loads(path.read_text(encoding='utf-8'))):
        if _REFERENCE.match(text):
            continue
        hit = [m for m in markers(text) if m not in EXEMPT.get(owner, set())]
        if hit:
            found.append((where, hit, text))
    return found
