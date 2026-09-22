from pathlib import Path
p=Path('build_v03.py');raw=p.read_bytes();s=raw.decode('utf-8').replace('\r\n','\n')
old='''ROUTE_X = [3.0, 0.0, -3.0]      # x 正值往左；三條路線各一欄。
TIER_Y_STEP = 2.0               # y 正值往上；新手在下、傳奇在上。
BRANCH_DY = 0.5
BRANCH_ROW_DY = 0.7
'''
new='''TIER_Y_STEP = 1.0               # y 正值往上；五階落在 0..4。
LAYOUT_LANE_STEP = 0.95         # 同階橫排；第三分支使用同一路線的額外欄。
LAYOUT_MIN_SPACING = 0.9
LAYOUT_X_BOUNDS = (-4.5, 4.5)
LAYOUT_Y_BOUNDS = (0.0, 4.5)


def csf_route_x(tree):
    # Reserve 3 lanes (main + two branches), or 4 for a route with a third branch.
    # Center the complete tree, keeping each route in its own adjacent lane block.
    widths = [1 + max(len(t['branches']) for t in r['tiers']) for r in tree['routes']]
    cursor = (sum(widths) - 1) * LAYOUT_LANE_STEP / 2
    centers = []
    for width in widths:
        centers.append(round(cursor - LAYOUT_LANE_STEP, 6))
        cursor -= width * LAYOUT_LANE_STEP
    return centers


def validate_csf_layout(tree, nodes):
    label = tree['id']
    by_id = {n['id']: n for n in nodes}
    assert len(by_id) == len(nodes), f'{label}: duplicate node ids'
    for i, node in enumerate(nodes):
        x, y = node['x'], node['y']
        assert LAYOUT_X_BOUNDS[0] <= x <= LAYOUT_X_BOUNDS[1], (label, node, 'x bounds')
        assert LAYOUT_Y_BOUNDS[0] <= y <= LAYOUT_Y_BOUNDS[1], (label, node, 'y bounds')
        for other in nodes[i + 1:]:
            # Reject pairs closer than 0.9 on BOTH axes, including other routes.
            assert max(abs(x - other['x']), abs(y - other['y'])) + 1e-9 >= LAYOUT_MIN_SPACING, (
                label, node['id'], other['id'], 'overlap')
    expected_ids = set()
    route_bounds = []
    for route in tree['routes']:
        r = route['index']
        route_nodes = []
        previous = None
        for tier in route['tiers']:
            k = tier['index']
            main_id = f'm{r}{k}'
            expected_ids.add(main_id)
            main = by_id[main_id]
            route_nodes.append(main)
            if previous is not None:
                assert main['y'] > previous['y'], (label, main_id, 'tier order')
                assert main['x'] == previous['x'], (label, main_id, 'mainline column')
            previous = main
            links = [f'm{r}{k + 1}'] if k + 1 < len(route['tiers']) else []
            for branch in tier['branches']:
                branch_id = f'b{r}{k}{branch["index"]}'
                expected_ids.add(branch_id)
                links.append(branch_id)
                node = by_id[branch_id]
                route_nodes.append(node)
                assert not node['links'], (label, branch_id, 'branch links')
                assert node['y'] == main['y'], (label, branch_id, 'branch tier')
                assert abs(node['x'] - main['x']) <= 2 * LAYOUT_LANE_STEP + 1e-9, (
                    label, branch_id, 'branch adjacency')
            assert main['links'] == links, (label, main_id, 'mainline/branch links')
        route_bounds.append((min(n['x'] for n in route_nodes), max(n['x'] for n in route_nodes)))
    assert set(by_id) == expected_ids, (label, 'unexpected nodes')
    for left, right in zip(route_bounds, route_bounds[1:]):
        assert left[0] - right[1] + 1e-9 >= LAYOUT_MIN_SPACING, (label, 'route separation')
    return {'valid': True, 'x': [min(n['x'] for n in nodes), max(n['x'] for n in nodes)],
            'y': [min(n['y'] for n in nodes), max(n['y'] for n in nodes)],
            'min_spacing': min(max(abs(a['x'] - b['x']), abs(a['y'] - b['y']))
                               for i, a in enumerate(nodes) for b in nodes[i + 1:]),
            'route_x': csf_route_x(tree)}
'''
assert old in s;s=s.replace(old,new)
s=s.replace("    nodes = []\n    for route in tree['routes']:","    nodes = []\n    route_x = csf_route_x(tree)\n    for route in tree['routes']:")
s=s.replace('        x = ROUTE_X[r]','        x = route_x[r]')
s=s.replace("'x': x + (1.0 if n % 2 == 0 else -1.0),\n                    'y': y + BRANCH_DY + (n // 2) * BRANCH_ROW_DY,", "'x': round(x + (1 if n == 0 else -n) * LAYOUT_LANE_STEP, 6),\n                    'y': y,")
s=s.replace("        unresolved = []\n        for node, edid", "        layout = validate_csf_layout(tree, reloaded['skills'][0]['nodes'])\n        unresolved = []\n        for node, edid")
s=s.replace("            'tree': tree['id'],\n            'path':", "            'tree': tree['id'],\n            'layout': layout,\n            'path':")
s=s.replace("            'route_x': ROUTE_X, 'tier_y_step': TIER_Y_STEP,\n            'branch_dx': [1.0, -1.0], 'branch_dy': BRANCH_DY, 'branch_row_dy': BRANCH_ROW_DY,", "            'lane_step': LAYOUT_LANE_STEP, 'tier_y_step': TIER_Y_STEP,\n            'x_bounds': LAYOUT_X_BOUNDS, 'y_bounds': LAYOUT_Y_BOUNDS,\n            'min_spacing': LAYOUT_MIN_SPACING, 'branch_dy': 0.0,")
s=s.replace("    return files\n\n\ndef compile_scripts", "    print(f'LAYOUT ok: trees={len(files)}/13 x=[-4.5,4.5] y=[0,4.5] '\n          f'min_spacing={min(f[\"layout\"][\"min_spacing\"] for f in files):.2f} >= {LAYOUT_MIN_SPACING}; '\n          'tier order + route separation + mainline/branch links valid')\n    return files\n\n\ndef compile_scripts")
# Additional exact snapshot check, retaining all previous build checks.
s=s.replace("    perks = sum(1 for r in check if r.sig == 'PERK')", "    fix2_path = WORK / '.codex/pre-fix2-snapshot/v03-formids.json'\n    if fix2_path.is_file():\n        fix2_records = json.loads(fix2_path.read_text(encoding='utf-8'))['records']\n        assert written['records'] == fix2_records, 'fix round 2 record identities changed'\n    perks = sum(1 for r in check if r.sig == 'PERK')")
p.write_bytes(s.replace('\n','\r\n' if b'\r\n' in raw else '\n').encode('utf-8'))
p=Path('.codex/impl-fix-round2.html');s=p.read_text(encoding='utf-8').replace('待修改：13 棵 bounds、spacing、links 檢查。','已修改：五階 y=0..4，同階橫排、路線獨立分欄；新增 bounds、所有配對 spacing、階序、路線分隔、主線／分支 links 斷言及 LAYOUT ok。待執行驗證。');p.write_text(s,encoding='utf-8')
print('Layout edits complete.')
