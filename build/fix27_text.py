"""Round 27e (0.27.4): player-facing text without the design document's annotations.

The tree generator copies 元素魔戰士規劃-v0.4.md's cells verbatim, and the document carries notes for its readers
(「（2026-09-27 依實作：…）」, 待決, 指揮官裁定, v0.3 / v0.4, round numbers, file names, 探針, 實作紀錄). player_text() drops
every parenthetical group that holds such a marker and keeps the gameplay text; markers() finds any left, and
build/fix27_verify.py fails the build when a perk name / description, a Custom Skills file or the MCM config still has one.
"""
from __future__ import annotations

import re

MARKER = re.compile(
    r'20\d\d-\d\d-\d\d|依實作|待決|指揮官|裁定|已決|[vV]0\.\d|[Rr]ound\s?\d|探針|實作紀錄|規劃文件|native-verification|'
    r'[A-Za-z0-9_]+\.(?:md|py|h|cpp|psc|json|esp|esm|log)\b|HitMath|Status\.h|Reactions\.h|Plugin\.cpp')

_OPEN = '（('
_CLOSE = '）)'


# A note that corrected the number itself: stripping it would leave the document's old number, so the player text states
# what the game does (the DLL's HitMath: 3 × points × G(L) of the target's stamina).
OVERRIDES = {
    '命中削減目標耐力 +0.5／點': '命中削減目標耐力：削減量＝3 × 點數 × G(L)',
    # Round 28 (D3) / 28b (F7, the user's rulings 2026-09-28): 25% of max magicka, only with a hostile in range, 10 s cooldown.
    '水臨強化：水臨時範圍內敵人浸濕，你立即清除全部負面效果並回滿魔力（開場就是滿的水幕）':
        '水臨強化：水臨時範圍內有敵人才發動：範圍內敵人浸濕，你立即清除全部負面效果並回復最大魔力 25%（受回復倍率影響）；'
        '發動後 10 秒內再開水形態或切到水不會再發動',
    # Round 28b (F5, the user's ruling 2026-09-28): the new 印潮.
    '印潮：切換後那一擊的開印，同時讓 15 公尺內帶著同一個舊印記的其他目標各觸發一次新元素的開印（最多 2 人；與大協奏對稱：大協奏傳終焉，印潮傳開印）':
        '印潮：切換形態後的第一擊開印時，那個目標 15 公尺內身上沒有任何印記的其他敵人（最近的最多 2 人）也掛上新元素的印記；'
        '不會切換任何人已有的印記',
}


def markers(text: str) -> list[str]:
    return MARKER.findall(text or '')


def player_text(text: str) -> str:
    """The text with every parenthetical note that carries a marker removed (innermost first, repeated)."""
    if not text:
        return text
    out = text
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
    out = re.sub(r'[ 　]{2,}', ' ', out).strip()
    return OVERRIDES.get(out, out)


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
