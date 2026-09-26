"""把規劃 v0.4 第 5 章的 13 張技能樹表解析成結構化節點表（＝身分表）。

產出 build/plan-tree-nodes.json，是技能樹的唯一真相來源：
  - build_v03.py 從它產生 PERK 記錄與 CSF 設定檔；
  - Papyrus 的每一個點數讀取（`; @node 名稱` 註記）、DLL 的 node:: 常數（build/fix19_native.py）、
    ESP 的 PERK 進入點（build_v03.main_entries／branch_entries）都以 **v0.4 節點名稱** 對它核對，
    名稱對不上、讀到退役格、或讀到本輪不做的節點，建置就失敗（build/fix21_identity.py）。

規劃 v0.4 的結構：13 棵樹 × 3 條路線 × 5 階；表格一個節點一列（路線｜階｜節點｜觸發｜負責），
「主線：」開頭的是該階主線（15 點），其餘是分支（名稱加粗，各 5 點）。

格位（slot）＝ FormID 的分支格 n（0x002000 + 階號 × 4 + n），跟顯示順序（order，v0.4 表序）分開：
沿用 v0.3 的節點保留 v0.3 的格（同名，或 tree_v04.RENAMES 的改名），新節點放 tree_v04.NEW_SLOTS
指定的、v0.3 從沒用過的格；v0.3 有、v0.4 沒有的分支是「退役 perk」（記錄保留、不可購買、不進 CSF）。
v0.3 的規劃檔永遠不改，這裡只讀它來推格位與保存歷史文字。
"""
from __future__ import annotations

import json
import re

from tes import WORK, dump

PLAN = WORK / '元素魔戰士規劃-v0.4.md'
PLAN_V03 = WORK / '元素魔戰士規劃-v0.3.md'   # 只用來推「沿用哪一格」與保存 v0.3 文字（歷史）
OUT = WORK / 'build/plan-tree-nodes.json'

# 規劃 5.1–5.13 的順序 → 樹 id。前 11 個對應 build_v03.ELEMENTS 的 0–10。
SECTION_TO_TREE = {
    '5.1': 'noform', '5.2': 'common', '5.3': 'fire', '5.4': 'frost', '5.5': 'lightning',
    '5.6': 'earth', '5.7': 'wind', '5.8': 'blood', '5.9': 'divine', '5.10': 'poison',
    '5.11': 'water', '5.12': 'darkness', '5.13': 'astral',
}
# 樹的正式索引（build_v03 用同一份順序配 FormID 與 CSF 檔名）。
TREE_ORDER = ['fire', 'frost', 'lightning', 'earth', 'wind', 'blood', 'divine', 'poison',
              'water', 'darkness', 'astral', 'noform', 'common']
ELEMENT_TREES = TREE_ORDER[:11]

# 規劃 3：樹等級到了該階才開放。
TIERS = [('新手', 10), ('熟練', 25), ('專精', 50), ('大師', 75), ('傳奇', 100)]
TIER_NAMES = [t for t, _ in TIERS]

MAIN_MAX_RANK = 15
BRANCH_COST = 5
MAX_BRANCH = 4          # FormID 每階預留 4 格；超過就要改配置表，所以硬性檢查。

SLASH = '／'
COLON = '：'
MAIN_PREFIX = '主線：'
TABLE_HEADER_V04 = '| 路線 | 階 | 節點 | 觸發 | 負責 |'


def cells(line: str) -> list[str]:
    """把一列 markdown 表格切成儲存格（去掉首尾的空欄）。"""
    if not line.startswith('|'):
        raise ValueError(f'not a table row: {line!r}')
    parts = line.split('|')
    if parts[0].strip() or parts[-1].strip():
        raise ValueError(f'unbalanced table row: {line!r}')
    return [c.strip() for c in parts[1:-1]]


def strip_bold(text: str) -> str:
    return re.sub(r'\*\*(.+?)\*\*', r'\1', text).strip()


def section_blocks(lines: list[str], *, stop_heading: str | None) -> list[tuple[str, str, list[str]]]:
    """第 5 章 13 個 `### 5.N` 小節的 (編號, 標題, 行)。"""
    heads = []
    for number, line in enumerate(lines):
        m = re.match(r'^### (5\.\d+) (.+)$', line)
        if m:
            heads.append((number, m.group(1), m.group(2).strip()))
    if len(heads) != 13:
        raise SystemExit(f'expected 13 section-5 headings, found {len(heads)}')
    end_all = len(lines)
    if stop_heading:
        after = [n for n, line in enumerate(lines) if n > heads[-1][0] and line.startswith(stop_heading)]
        if not after:
            raise SystemExit(f'heading {stop_heading!r} after section 5.13 not found')
        end_all = after[0]
    out = []
    for position, (start, section, title) in enumerate(heads):
        end = heads[position + 1][0] if position + 1 < len(heads) else end_all
        out.append((section, title, lines[start:end]))
    return out


def main_label(text: str) -> str:
    """主線的短名：主線文字到第一個「 +」「 -」「，」「（」「：」為止。同一棵樹內必須唯一。"""
    label = re.split(r' \+| -|，|（|：', text, maxsplit=1)[0].strip()
    if not label:
        raise SystemExit(f'empty main-line label for {text!r}')
    return label


# ------------------------------------------------------------------ v0.3（只讀，推格位用）
def parse_v03() -> dict:
    """v0.3 的 4 欄表（路線｜階｜主線｜分支，分支以「／」分隔）。回傳 {樹: {(路線, 階): {...}}}。"""
    lines = PLAN_V03.read_text(encoding='utf-8').splitlines()
    trees = {}
    for section, title, block in section_blocks(lines, stop_heading=None):
        tree_id = SECTION_TO_TREE[section]
        table = next((n for n, line in enumerate(block)
                      if line.startswith('| 路線 ') and '主線' in line and '分支' in line), None)
        if table is None:
            raise SystemExit(f'v0.3 {section}: skill table not found')
        rows = []
        for line in block[table + 2:]:
            if not line.startswith('|'):
                break
            rows.append(cells(line))
        if len(rows) != 15:
            raise SystemExit(f'v0.3 {section}: expected 15 rows, got {len(rows)}')
        tiers = {}
        route = -1
        tier = 0
        for row in rows:
            route_cell, tier_cell, main_cell, branch_cell = row
            if route_cell:
                route += 1
                tier = 0
            branches = []
            for index, part in enumerate(branch_cell.split(SLASH)):
                part = part.strip()
                if COLON not in part:
                    raise SystemExit(f'v0.3 {section}: branch without colon: {part!r}')
                branches.append({'slot': index, 'name': part.split(COLON, 1)[0].strip(), 'description': part})
            tiers[(route, tier)] = {'main': main_cell, 'branches': branches}
            tier += 1
        trees[tree_id] = tiers
    return trees


# ------------------------------------------------------------------ v0.4
def parse_v04_rows() -> dict:
    """v0.4 的 5 欄表 → {樹: {'section', 'title', 'routes': [{'name','kind','tiers':[{main, branches}]}]}}。"""
    lines = PLAN.read_text(encoding='utf-8').splitlines()
    out = {}
    for section, title, block in section_blocks(lines, stop_heading='## 6.'):
        tree_id = SECTION_TO_TREE[section]
        headers = [n for n, line in enumerate(block) if line.startswith(TABLE_HEADER_V04)]
        if len(headers) != 1:
            raise SystemExit(f'{section} {title}: expected exactly one node table, found {len(headers)}')
        rows = []
        for line in block[headers[0] + 2:]:
            if not line.startswith('|'):
                break
            rows.append(cells(line))
        routes = []
        route = tier = None
        for row in rows:
            if len(row) != 5:
                raise SystemExit(f'{section}: row has {len(row)} cells, expected 5: {row}')
            route_cell, tier_cell, node_cell, trigger, owner = row
            if route_cell:
                bold = re.match(r'^\*\*(.+?)\*\*(.*)$', route_cell)
                if not bold:
                    raise SystemExit(f'{section}: route cell is not bold: {route_cell!r}')
                route = {'index': len(routes), 'name': strip_bold(route_cell), 'kind': bold.group(1).strip(),
                         'tiers': []}
                routes.append(route)
                tier = None
            if route is None:
                raise SystemExit(f'{section}: row before any route: {row}')
            if tier_cell:
                expected = TIER_NAMES[len(route['tiers'])] if len(route['tiers']) < 5 else None
                if tier_cell != expected:
                    raise SystemExit(f'{section} {route["name"]}: tier {tier_cell!r}, expected {expected!r}')
                tier = {'index': len(route['tiers']), 'name': tier_cell,
                        'level': TIERS[len(route['tiers'])][1], 'main': None, 'branches': []}
                route['tiers'].append(tier)
                if not node_cell.startswith(MAIN_PREFIX):
                    raise SystemExit(f'{section} {route["name"]} {tier_cell}: first row is not the main line')
            if tier is None:
                raise SystemExit(f'{section}: node row before any tier: {row}')
            if node_cell.startswith(MAIN_PREFIX):
                if tier['main'] is not None:
                    raise SystemExit(f'{section} {route["name"]} {tier["name"]}: two main lines')
                tier['main'] = {'text': node_cell[len(MAIN_PREFIX):].strip(), 'trigger': trigger, 'owner': owner}
                continue
            m = re.match(r'^\*\*(.+?)\*\*：(.+)$', node_cell)
            if not m:
                raise SystemExit(f'{section} {route["name"]} {tier["name"]}: branch cell is not '
                                 f'"**名稱**：說明": {node_cell!r}')
            name = m.group(1).strip()
            tier['branches'].append({'order': len(tier['branches']), 'name': name,
                                     'description': f'{name}{COLON}{m.group(2).strip()}',
                                     'trigger': trigger, 'owner': owner})
        if len(routes) != 3:
            raise SystemExit(f'{section} {title}: expected 3 routes, got {len(routes)}')
        for r in routes:
            if len(r['tiers']) != 5:
                raise SystemExit(f'{section} {r["name"]}: expected 5 tiers, got {len(r["tiers"])}')
            for t in r['tiers']:
                if not t['branches']:
                    raise SystemExit(f'{section} {r["name"]} {t["name"]}: no branch')
                if len(t['branches']) > MAX_BRANCH:
                    raise SystemExit(f'{section} {r["name"]} {t["name"]}: {len(t["branches"])} branches')
        out[tree_id] = {'section': section, 'title': title, 'routes': routes}
    return out


def assign_slots(tree_id: str, route: int, tier: int, branches: list[dict], v03_branches: list[dict]):
    """每個 v0.4 分支配一個 FormID 格；回傳 (branches 帶 slot, 退役清單)。規則見檔頭。"""
    import tree_v04
    by_v03 = {b['name']: b for b in v03_branches}
    renames = tree_v04.RENAMES.get((tree_id, route, tier), {})
    claimed = {}
    for b in branches:
        name = b['name']
        new_slot = tree_v04.NEW_SLOTS.get((tree_id, route, tier, name))
        source = renames.get(name, name)
        if new_slot is not None:
            if source in by_v03:
                raise SystemExit(f'{tree_id} {route} {tier} {name}: listed as new but v0.3 has {source!r}')
            if any(v['slot'] == new_slot for v in v03_branches):
                raise SystemExit(f'{tree_id} {route} {tier} {name}: new slot {new_slot} was used in v0.3 '
                                 '(retired slots are never reused)')
            b['slot'] = new_slot
            b['v03'] = None
        elif source in by_v03:
            b['slot'] = by_v03[source]['slot']
            b['v03'] = {'name': source, 'description': by_v03[source]['description']}
        else:
            raise SystemExit(f'{tree_id} {route} {tier} {name}: not in v0.3 and no tree_v04.NEW_SLOTS entry')
        if not 0 <= b['slot'] < MAX_BRANCH:
            raise SystemExit(f'{tree_id} {route} {tier} {name}: slot {b["slot"]} out of range')
        if b['slot'] in claimed:
            raise SystemExit(f'{tree_id} {route} {tier}: slot {b["slot"]} claimed by {claimed[b["slot"]]} and {name}')
        claimed[b['slot']] = name
    for name, source in renames.items():
        if name not in {b['name'] for b in branches}:
            raise SystemExit(f'{tree_id} {route} {tier}: rename target {name!r} not in v0.4')
        if source not in by_v03:
            raise SystemExit(f'{tree_id} {route} {tier}: rename source {source!r} not in v0.3')
    retired = [{'slot': v['slot'], 'name': v['name'], 'description': v['description']}
               for v in v03_branches if v['slot'] not in claimed]
    return branches, retired


def parse() -> dict:
    v04 = parse_v04_rows()
    v03 = parse_v03()
    trees = []
    for index, tree_id in enumerate(TREE_ORDER):
        if tree_id not in v04:
            raise SystemExit(f'tree {tree_id} missing from v0.4 section 5')
        src = v04[tree_id]
        labels = {}
        routes = []
        for route in src['routes']:
            tiers = []
            for tier in route['tiers']:
                key = (route['index'], tier['index'])
                old = v03[tree_id][key]
                branches, retired = assign_slots(tree_id, route['index'], tier['index'],
                                                 tier['branches'], old['branches'])
                text = tier['main']['text']
                label = main_label(text)
                for name in [label] + [b['name'] for b in branches]:
                    if name in labels:
                        raise SystemExit(f'{tree_id}: node name {name!r} is not unique '
                                         f'({labels[name]} and {key})')
                    labels[name] = key
                tiers.append({
                    'index': tier['index'],
                    'name': tier['name'],
                    'level': tier['level'],
                    'main': text,
                    'main_label': label,
                    'main_trigger': tier['main']['trigger'],
                    'main_owner': tier['main']['owner'],
                    'main_max_rank': MAIN_MAX_RANK,
                    'v03_main': old['main'],
                    'branches': sorted(branches, key=lambda b: b['order']),
                    'retired': retired,
                })
            routes.append({'index': route['index'], 'name': route['name'], 'kind': route['kind'], 'tiers': tiers})
        trees.append({'id': tree_id, 'index': index, 'section': src['section'], 'title': src['title'],
                      'routes': routes})

    assert len(trees) == 13 and all(len(t['routes']) == 3 for t in trees)
    assert all(len(r['tiers']) == 5 for t in trees for r in t['routes'])
    main_nodes = sum(1 for t in trees for r in t['routes'] for _ in r['tiers'])
    branch_nodes = sum(len(ti['branches']) for t in trees for r in t['routes'] for ti in r['tiers'])
    retired = sum(len(ti['retired']) for t in trees for r in t['routes'] for ti in r['tiers'])
    new = sum(1 for t in trees for r in t['routes'] for ti in r['tiers'] for b in ti['branches'] if b['v03'] is None)
    return {
        'source': PLAN.name,
        'slot_source': PLAN_V03.name,
        'plan_section': '5.1–5.13',
        'tier_names': TIER_NAMES,
        'tier_levels': [lv for _, lv in TIERS],
        'main_max_rank': MAIN_MAX_RANK,
        'branch_cost': BRANCH_COST,
        'max_branch_slots': MAX_BRANCH,
        'totals': {
            'trees': len(trees),
            'routes': len(trees) * 3,
            'tiers': main_nodes,
            'main_nodes': main_nodes,
            'main_rank_perks': main_nodes * MAIN_MAX_RANK,
            'branch_nodes': branch_nodes,
            'new_branches': new,
            'retired_branches': retired,
            'asserted': '13 trees x 3 routes x 5 tiers',
        },
        'trees': trees,
    }


# ------------------------------------------------------------------ 節點倍率（規劃 3）
# 「純百分比傷害主線每點 ×3：文件寫 +1%／點的純增傷主線，遊戲內顯示與生效都是 +3%／點。時間、機率、範圍、
# 層數、回復、抗性類節點不吃這個倍率。」表內另有明寫「不吃節點倍率」的列。
DAMAGE_WORDS = ('附傷', '傷害', '終焉', '融斷', '爆燃', '碎冰', '放電', '裁決', '聖裁', '死咒', '星落', '導引',
                '風刃', '地震', '血潮', '聖傷', '闇星')
NOT_SCALED_WORDS = ('機率', '暴擊率', '回血', '回復', '吸血比例', '治療', '長流', '抗性侵蝕', '火抗', '減防',
                    '護甲削減', '減速', '移速', '凍結累積', '同調門檻', '受傷', '分擔', '效率', '燒魔', '上限',
                    '持續', '範圍', '延遲', '比例', '倍數', '倍率', '衰減', '耐力削減')
# 開啟傳奇「開印效果 +3%／點」：fix8 使用者核准整體套用節點倍率（v0.4 沿用）。
OPEN_EFFECT_LABEL = '開印效果'


def classify_main(tree_id, route, tier, text):
    """v0.4 主線是否吃節點倍率。明寫的排除先於百分比比對；回傳 (狀態, 理由)。"""
    if '不吃節點倍率' in text:
        if tree_id == 'blood' and (route, tier) == (0, 0):
            # 「流血每層傷害 +2%／點，放血係數 +0.01%／點（0.3% → 0.45%，不吃節點倍率）」：括號只屬於放血係數。
            return 'SCALED', 'fix8 使用者核准：只縮放流血每層傷害，放血係數保持原值（v0.4 明寫）'
        return 'UNCHANGED', 'v0.4 明寫「不吃節點倍率」'
    if main_label(text) == OPEN_EFFECT_LABEL:
        return 'SCALED', 'fix8 使用者核准：開印效果整體套用 ESSB_NodeScale'
    if not re.search(r'\+([\d.]+)%／點', text):
        return 'UNCHANGED', '不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數）'
    if any(word in text for word in NOT_SCALED_WORDS):
        return 'UNCHANGED', '時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率）'
    if any(word in text for word in DAMAGE_WORDS):
        return 'SCALED', '純百分比傷害主線（規劃 3）'
    return 'UNCHANGED', '非傷害百分比'


RANGE_RE = re.compile(r'（(×?)([\d.]+)(%?) → (×?)([\d.]+)(%?)')


def scaled_main_text(text, scale):
    """只放大第一個「+X%／點」，以及緊接在它後面的「（a → b）」區間的終點（b' = a + (b − a) × 倍率）；
    遊戲內顯示＝生效值。區間前若隔著別的「／點」項（例如血的放血係數），那個區間屬於別的項，不動。"""
    match = re.search(r'\+([\d.]+)%／點', text)
    assert match, text
    per = float(match[1])
    out = text[:match.start(1)] + f'{per * scale:g}' + text[match.end(1):]
    tail_at = match.start(1) + len(f'{per * scale:g}') + (match.end() - match.end(1))
    rng = RANGE_RE.match(out, tail_at)
    if rng:
        start, end = float(rng[2]), float(rng[5])
        new_end = start + (end - start) * scale
        out = out[:rng.start(5)] + f'{new_end:g}' + out[rng.end(5):]
    return out


def check_settings_text(data, settings):
    """v0.4 表內寫死的數字，跟 settings.json 裡同一個可調值必須一致（任一邊改了、另一邊沒跟，建置失敗）。"""
    def branch(tree_id, name):
        for t in data['trees']:
            if t['id'] == tree_id:
                for r in t['routes']:
                    for k in r['tiers']:
                        for b in k['branches']:
                            if b['name'] == name:
                                return b['description']
        raise SystemExit(f'{tree_id} {name}: branch not found')

    def main(tree_id, route, tier):
        tree = next(t for t in data['trees'] if t['id'] == tree_id)
        return tree['routes'][route]['tiers'][tier]['main_original']

    checks = [
        (branch('noform', '奪魔'), f'目標最大魔力 {settings["manabreak_maxmag_pct"]:g}%'),
        (branch('water', '清流'), f'命中回復耐力 {settings["water_clear_stamina"]:g}'),
        (branch('water', '湧泉'), f'開印時回復耐力 {settings["water_open_stamina"]:g}'),
        (main('water', 0, 1), f'（{settings["water_flow_base_pct"]:.1f}% → '
                              f'{settings["water_flow_base_pct"] + 15 * settings["water_flow_per_rank_pct"]:.1f}%'),
        (main('water', 0, 1), f'+{settings["water_flow_per_rank_pct"]:g}%／點'),
    ]
    for text, needle in checks:
        if needle not in text:
            raise SystemExit(f'settings.json disagrees with v0.4 text: {needle!r} not in {text!r}')


def apply_balance_text(data):
    """設計文件不改；PERK 與 CSF 用這份產生的文字（純百分比傷害主線顯示乘過節點倍率的值）。"""
    settings = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))
    scale = settings['node_percent_scale']
    for tree in data['trees']:
        for route in tree['routes']:
            for tier in route['tiers']:
                old = tier['main']
                status, reason = classify_main(tree['id'], route['index'], tier['index'], old)
                tier['main_original'] = old
                tier['balance_class'] = status
                tier['balance_reason'] = reason
                if status == 'SCALED':
                    tier['main'] = scaled_main_text(old, scale)
                for branch in tier['branches']:
                    branch['description_original'] = branch['description']
    check_settings_text(data, settings)
    return data


def build():
    data = apply_balance_text(parse())
    dump(OUT, data)
    return data


def main():
    data = build()
    totals = data['totals']
    print(f'PLAN TREES ok: trees={totals["trees"]} routes={totals["routes"]} tiers={totals["tiers"]} '
          f'main_nodes={totals["main_nodes"]} main_rank_perks={totals["main_rank_perks"]} '
          f'branch_nodes={totals["branch_nodes"]} new={totals["new_branches"]} '
          f'retired={totals["retired_branches"]} -> {OUT.name}')


if __name__ == '__main__':
    main()
