"""把規劃 v0.3 第 5 章的 13 張表解析成結構化節點表。

產出 build/plan-tree-nodes.json，是技能樹前線的唯一真相來源：
  - build_v03.py 從它產生 PERK 記錄與 CSF 設定檔。
  - 之後的規劃覆蓋檢查也從它比對，所以第 5 章的每一列、每一格都必須被收進來。

規劃 3 的結構：13 棵樹 × 3 條路線 × 5 階；每階一個主線節點（最多 15 點）
加一到多個分支（各 5 點，可複選）。分支格以全形斜線「／」分隔，
每個分支是「名稱：說明」。
"""
from __future__ import annotations

import re

from tes import WORK, dump

PLAN = WORK / '元素魔戰士規劃-v0.3.md'
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

# 規劃 3：樹等級到了該階才開放。
TIERS = [('新手', 10), ('熟練', 25), ('專精', 50), ('大師', 75), ('傳奇', 100)]
TIER_NAMES = [t for t, _ in TIERS]

MAIN_MAX_RANK = 15
BRANCH_COST = 5
MAX_BRANCH = 4          # FormID 每階預留 4 格；超過就要改配置表，所以硬性檢查。

SLASH = '／'
COLON = '：'


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


def parse_branches(cell: str) -> list[dict]:
    """分支格：以全形斜線分隔，每個分支是「名稱：說明」。"""
    out = []
    if not cell or cell in ('—', '-', '－'):
        return out
    for index, part in enumerate(cell.split(SLASH)):
        part = part.strip()
        if not part:
            raise ValueError(f'empty branch in cell {cell!r}')
        if COLON not in part:
            # 沒有全形冒號代表切錯了（說明裡出現了非分隔用的斜線）。
            raise ValueError(f'branch without "{COLON}" separator: {part!r} (cell {cell!r})')
        name = part.split(COLON, 1)[0].strip()
        out.append({'index': index, 'name': name, 'description': part, 'cost': BRANCH_COST})
    return out


def parse() -> dict:
    text = PLAN.read_text(encoding='utf-8')
    lines = text.splitlines()

    # 找出 5.1–5.13 每一節的行範圍。
    heads = []
    for number, line in enumerate(lines):
        m = re.match(r'^### (5\.\d+) (.+)$', line)
        if m:
            heads.append((number, m.group(1), m.group(2).strip()))
    if len(heads) != 13:
        raise SystemExit(f'expected 13 section-5 headings, found {len(heads)}')

    trees_by_id = {}
    for position, (start, section, title) in enumerate(heads):
        end = heads[position + 1][0] if position + 1 < len(heads) else len(lines)
        tree_id = SECTION_TO_TREE[section]
        block = lines[start:end]

        # 只取「路線 | 階 | 主線 | 分支」那一張表（5.12 另有一張復生階級對照表）。
        table = None
        for number, line in enumerate(block):
            if line.startswith('| 路線 ') and '主線' in line and '分支' in line:
                table = number
                break
        if table is None:
            raise SystemExit(f'{section} {title}: skill table not found')
        rows = []
        for line in block[table + 2:]:
            if not line.startswith('|'):
                break
            rows.append(cells(line))
        if len(rows) != 15:
            raise SystemExit(f'{section} {title}: expected 15 rows, got {len(rows)}')

        routes = []
        current = None
        for row in rows:
            if len(row) != 4:
                raise SystemExit(f'{section}: row has {len(row)} cells, expected 4: {row}')
            route_cell, tier_cell, main_cell, branch_cell = row
            if route_cell:
                name = strip_bold(route_cell)
                # 路線格通常是 `**持續（烈焰）**`；粗體裡的內容是路線類型。
                bold = re.match(r'^\*\*(.+?)\*\*', route_cell)
                kind = strip_bold(bold.group(1)) if bold else name
                current = {'index': len(routes), 'name': name, 'kind': kind, 'tiers': []}
                routes.append(current)
            if current is None:
                raise SystemExit(f'{section}: tier row before any route row: {row}')
            tier_index = len(current['tiers'])
            if tier_index >= len(TIERS):
                raise SystemExit(f'{section} {current["name"]}: more than 5 tiers')
            if tier_cell != TIER_NAMES[tier_index]:
                raise SystemExit(f'{section} {current["name"]}: tier {tier_index} is '
                                 f'{tier_cell!r}, expected {TIER_NAMES[tier_index]!r}')
            if not main_cell:
                raise SystemExit(f'{section} {current["name"]} {tier_cell}: empty mainline cell')
            try:
                branches = parse_branches(branch_cell)
            except ValueError as error:
                raise SystemExit(f'{section} {current["name"]} {tier_cell}: {error}')
            if not branches:
                raise SystemExit(f'{section} {current["name"]} {tier_cell}: no branch')
            if len(branches) > MAX_BRANCH:
                raise SystemExit(f'{section} {current["name"]} {tier_cell}: '
                                 f'{len(branches)} branches > {MAX_BRANCH} reserved slots')
            current['tiers'].append({
                'index': tier_index,
                'name': TIER_NAMES[tier_index],
                'level': TIERS[tier_index][1],
                'main': main_cell,
                'main_max_rank': MAIN_MAX_RANK,
                'branches': branches,
            })
        if len(routes) != 3:
            raise SystemExit(f'{section} {title}: expected 3 routes, got {len(routes)}')
        for route in routes:
            if len(route['tiers']) != 5:
                raise SystemExit(f'{section} {route["name"]}: expected 5 tiers, '
                                 f'got {len(route["tiers"])}')
        trees_by_id[tree_id] = {'id': tree_id, 'section': section, 'title': title, 'routes': routes}

    trees = []
    for index, tree_id in enumerate(TREE_ORDER):
        if tree_id not in trees_by_id:
            raise SystemExit(f'tree {tree_id} missing from section 5')
        tree = trees_by_id[tree_id]
        tree['index'] = index
        trees.append(tree)

    # 硬性檢查：13 × 3 × 5。
    assert len(trees) == 13, len(trees)
    assert all(len(t['routes']) == 3 for t in trees)
    assert all(len(r['tiers']) == 5 for t in trees for r in t['routes'])

    main_nodes = sum(1 for t in trees for r in t['routes'] for _ in r['tiers'])
    branch_nodes = sum(len(ti['branches']) for t in trees for r in t['routes'] for ti in r['tiers'])
    return {
        'source': PLAN.name,
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
            'asserted': '13 trees x 3 routes x 5 tiers',
        },
        'trees': trees,
    }



def classify_main(tree_id, route, tier, text):
    """Semantic exclusions precede percentage matching. Ambiguous composite nodes stay unchanged."""
    key = (tree_id, route, tier)
    if key in {('noform', 1, 0), ('water', 0, 1), ('water', 1, 0), ('frost', 1, 0)}:
        return 'SPECIFIC', '第 2／2b 項指定數值'
    if key in {('noform', 1, 1), ('noform', 1, 3)}:
        return 'UNCHANGED', '第 2 項明定比例／對施法者 +5% 不變'
    if any(word in text for word in ('機率', '暴擊率')):
        return 'UNCHANGED', '機率'
    if any(word in text for word in ('回血', '回復', '吸血比例', '治療', '長流')):
        return 'UNCHANGED', '治療／回復'
    if any(word in text for word in ('抗性侵蝕', '火抗', '減防', '護甲削減')):
        return 'UNCHANGED', '減抗／削甲'
    if any(word in text for word in ('減速', '移速', '凍結累積', '同調門檻', '受傷')):
        return 'UNCHANGED', '移動／控制／防禦／門檻'
    if key == ('blood', 0, 0):
        return 'DECISION', '複合兩種百分比：流血傷害與放血係數，保留待決'
    if key == ('noform', 0, 4):
        return 'DECISION', '文字是無視護甲；實作為補真傷，保留待決'
    if '開印效果' in text:
        return 'DECISION', '開印倍率同時放大層數／控制／回復，保留待決'
    if key == ('earth', 2, 2):
        return 'DECISION', '削耐而非生命傷害，保留待決'
    if re.search(r'\+([\d.]+)%／點', text) and any(w in text for w in
            ('附傷', '傷害', '終焉', '融斷', '爆燃', '碎冰', '放電', '裁決', '死咒', '星落', '導引', '風刃', '地震', '血潮', '聖傷')):
        return 'SCALED', '純百分比傷害／傷害係數'
    return 'UNCHANGED', '非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數）'


def scaled_main_text(text, scale):
    match = re.search(r'\+([\d.]+)%／點', text)
    assert match, text
    per = float(match[1])
    out = text[:match.start(1)] + f'{per * scale:g}' + text[match.end(1):]
    def span(m):
        start, unit, end = float(m[1]), m[2], float(m[3])
        return f'（{m[1]}{unit} → {start + (end - start) * scale:g}{unit}）'
    out = re.sub(r'（([\d.]+)(%) → ([\d.]+)%）', span, out)
    out = re.sub(r'（×([\d.]+) → ×([\d.]+)）',
                 lambda m: f'（×{m[1]} → ×{float(m[1]) + (float(m[2])-float(m[1]))*scale:g}）', out)
    return out


def apply_balance_text(data):
    """Design document stays immutable. PERK and CSF consume this same generated text."""
    import json
    settings = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))
    scale = settings['node_percent_scale']
    for tree in data['trees']:
        for route in tree['routes']:
            for tier in route['tiers']:
                key = (tree['id'], route['index'], tier['index'])
                old = tier['main']
                status, reason = classify_main(*key, old)
                tier['main_original'] = old
                tier['balance_class'] = status
                tier['balance_reason'] = reason
                if status == 'SCALED':
                    tier['main'] = scaled_main_text(old, scale)
                elif key == ('noform', 1, 0):
                    tier['main'] = (f'破魔：命中削減目標魔力（{settings["manabreak_base"]:g} + '
                        f'{settings["manabreak_per_rank"]:g}／點）× G(L_無元素)，回復你實際削減的等量魔力，'
                        '造成實際削減量 ×0.5 的真實傷害（此路徑不重複乘 G），並施加「破魔印」8 秒')
                elif key == ('frost', 1, 0):
                    tier['main'] = old + f'（霜結基礎減速 {settings["frost_open_slow_pct"]:g}%，持續 3 秒；總減速上限 {settings["slow_cap_pct"]:g}%）'
                elif key == ('water', 0, 1):
                    base, per = settings['water_flow_base_pct'], settings['water_flow_per_rank_pct']
                    tier['main'] = f'長流每秒回復 +{per:g}%／點（{base:.1f}% → {base + 15*per:.1f}%）'
                elif key == ('water', 1, 0):
                    base = settings['water_wet_slow_pct']
                    tier['main'] = f'浸濕減速 +1%／點（{base:g}% → {base+15:g}%；本模組總減速上限 {settings["slow_cap_pct"]:g}%）'
                for branch in tier['branches']:
                    desc = branch['description']
                    branch['description_original'] = desc
                    if key == ('noform', 1, 0) and branch['name'] == '蝕魔':
                        desc = desc.replace('2%', f'{settings["manabreak_maxmag_pct"]:g}%')
                    elif key == ('noform', 1, 2) and branch['name'] == '枯竭':
                        desc = desc.replace('5%', f'{settings["manabreak_dry_pct"]:g}%')
                    elif key == ('water', 0, 0) and branch['name'] == '清流':
                        desc = desc.replace('5', f'{settings["water_clear_stamina"]:g}')
                    elif key == ('water', 1, 1) and branch['name'] == '回流':
                        desc = desc.replace('15', f'{settings["water_open_stamina"]:g}')
                    branch['description'] = desc
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
          f'branch_nodes={totals["branch_nodes"]} -> {OUT.name}')


if __name__ == '__main__':
    main()
