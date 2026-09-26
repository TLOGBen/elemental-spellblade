"""Round 21 (v0.4 trees): offline checks of what this round changed, each with injected faults.

Executes the actual Papyrus sources with the source-level harness and reads back the written ESP / CSF / MCM
(natives mocked; not the game runtime):

  R2        ESSBElem.OnEnd grants 接管附傷 (SetEndBoost) exactly for the element trees whose v0.4 table has
            「終焉後 5 秒內接管元素附傷」 at 關閉·專精 - derived from the identity table, not from the code; the
            pre-fix21 script (which granted it on every tree) must fail the same check.
  ENTRIES   the PERK records that carry entry points are exactly the base rules plus the perks the v0.4 names in
            build_v03.BRANCH_ENTRY_NODES / MAIN_ENTRY_NODES resolve to; rock armor base 4% per layer to 60%.
  RETIRED   the 49 v0.3 branches v0.4 removed keep their FormID / EditorID, are not playable, hidden, carry no
            entry point and appear in no CSF tree; every v0.4 node appears in its CSF tree exactly once.
  APPEND    no FormID the pre-fix21 plugin used changed identity; the 47 new branch perks use slots nothing used.
  RECORDS   the round-21 native records: soaked slow 1..30 s (one effect, that duration), 寂 / 寂滅 marker /
            反擊 window, 冰甲 cloaks pointing at their chill spells (aimed, hostile-only).
  MCM       節點倍率 slider 1-5, default 3 (ruling R3).
  HISTORY   every declared round-21 change in build/fix21_history.py is real.
The DLL halves of R5 / R6 are the native A0 anchors and A7 scenarios (native/tests, build/fix20_fixture.py).
"""
from pathlib import Path
from types import SimpleNamespace as NS
import copy, json, re, runpy, struct, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
# Round 22: these checks run on the pre-fix22 scripts; build/fix22_history.py ties them to today's (declared changes only).
import sys as _sys22
_sys22.path.insert(0, str(ROOT / 'build'))
import fix22_history as _fix22_history
SRC22 = _fix22_history.legacy_source()

sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]

NEW = SRC22
R20 = ROOT / '.codex/pre-fix21-snapshot/src'
TAKEOVER = '終焉後 5 秒內接管元素附傷'
PLUGIN_KEY = 'Elements Spellblade.esp'


def plan():
    return json.loads((ROOT / 'build/plan-tree-nodes.json').read_text(encoding='utf-8'))


# ---------------------------------------------------------------- R2

def takeover_trees(p):
    """Element indices (1..11) whose 關閉·專精 main line is the takeover line in v0.4."""
    return {t['index'] + 1 for t in p['trees'][:11] if t['routes'][2]['tiers'][2]['main_label'] == TAKEOVER}


def r2_boosts(folder):
    F18 = runpy.run_path(str(ROOT / 'build/fix18_verify.py'))
    got = {}
    for element in range(1, 12):
        f = F18['fixture'](folder)
        for tree in range(11):
            F18['ranks'](f, tree, 2, 2, 7, 0)
        boosts = []
        f.c.overrides['SetEndBoost'] = lambda e, seconds, amount: boosts.append((e, seconds, amount))
        for script, names in (('ESSBElem', ('EndFireNodes', 'EndFrostNodes', 'EndShockNodes')),
                              ('ESSBElem2', ('OnEnd',)), ('ESSBElem3', ('OnEnd',))):
            for name in names:
                f.env[script].overrides[name] = lambda *a: None   # the per-tree nodes are not under test here
        f.env['ESSBElem'].OnEnd(f.c, element, f.v, 0, 1.0)
        got[element] = boosts
    return got


def check_r2(got, expected, scale):
    for element, boosts in got.items():
        if element in expected:
            assert len(boosts) == 1, ('R2: takeover missing', element, boosts)
            e, seconds, amount = boosts[0]
            assert e == element and seconds == 5 and abs(amount - 0.01 * 7 * scale) < 1e-9, ('R2: takeover value', element, boosts)
        else:
            assert not boosts, ('R2: takeover granted on a tree whose v0.4 table has another node', element, boosts)


# ---------------------------------------------------------------- ESP readback

def perk_edid(t, r, k, slot=None, rank=None):
    return f'ESSB_P_{t}_{r}_{k}_' + (f'M{rank}' if slot is None else f'B{slot + 1}')


def check_entries(records, p, branch_keys, main_keys, base_edid):
    edid_of = {}
    for t in p['trees']:
        for r in t['routes']:
            for k in r['tiers']:
                for b in k['branches']:
                    edid_of[(t['id'], b['name'])] = perk_edid(t['id'], r['index'], k['index'], b['slot'])
                edid_of[(t['id'], k['main_label'])] = perk_edid(t['id'], r['index'], k['index'], rank=1)
    want = {edid_of[key] for key in branch_keys}
    for key in main_keys:   # a main-line key puts entries on every rank of that line
        want |= {edid_of[key][:-1] + str(n) for n in range(1, 16)}
    have = {r.edid for r in records if r.sig == 'PERK' and any(s == 'PRKE' for s, _ in r.ss)}
    tree_have = {e for e in have if e.startswith('ESSB_P_') and e != base_edid}
    assert tree_have == want, ('ENTRIES: perks with entry points differ from the v0.4 names',
                               sorted(tree_have - want), sorted(want - tree_have))
    return len(want)


def check_rock_armor(records, b):
    base = next(r for r in records if r.edid == 'ESSB_P_BaseRules')
    values = []
    for sig, data in base.ss:
        if sig == 'EPFD' and len(data) == 4:
            values.append(round(struct.unpack('<f', data)[0], 6))
    rock = sorted(v for v in values if v < 1.0 and v != 0.0)
    want = sorted(round(1.0 - min(0.04 * n, 0.6), 6) for n in range(1, b.ROCK_ARMOR_MAX_LAYERS + 1))
    assert rock == want, ('ENTRIES: rock armor base per layer', rock, want)
    return len(rock)


def perk_data(rec):
    """The PERK's own DATA (trait, level, ranks, playable, hidden); entry points carry DATA subrecords too."""
    return next(v for s, v in rec.ss if s == 'DATA')


def check_retired(records, p, csf_nodes):
    by = {r.edid: r for r in records}
    retired = 0
    for t in p['trees']:
        for r in t['routes']:
            for k in r['tiers']:
                for old in k['retired']:
                    edid = perk_edid(t['id'], r['index'], k['index'], old['slot'])
                    rec = by.get(edid)
                    assert rec is not None and rec.sig == 'PERK', ('RETIRED: record missing', edid)
                    data = perk_data(rec)
                    assert data[3] == 0 and data[4] == 1, ('RETIRED: must be unplayable and hidden', edid, data)
                    assert rec.name.endswith('（已退役）'), ('RETIRED: name', edid, rec.name)
                    assert not any(s == 'PRKE' for s, _ in rec.ss), ('RETIRED: carries an entry point', edid)
                    assert edid not in csf_nodes, ('RETIRED: still on a CSF tree', edid)
                    retired += 1
                for b in k['branches']:
                    edid = perk_edid(t['id'], r['index'], k['index'], b['slot'])
                    assert csf_nodes.get(edid) == 1, ('RETIRED: v0.4 branch not on its CSF tree once', edid, csf_nodes.get(edid))
                    assert perk_data(by[edid])[3] == 1, ('RETIRED: v0.4 branch not playable', edid)
                assert csf_nodes.get(perk_edid(t['id'], r['index'], k['index'], rank=1)) == 1
    return retired


def csf_nodes(b, written):
    """EditorID -> how many CSF nodes point at that perk (the CSF files name perks by plugin|FormID)."""
    edid_of = {v['id'].upper(): e for e, v in written.items()}
    counts = {}
    for path in sorted((b.OUT / b.CSF_DIR).glob('*.json')):
        for skill in json.loads(path.read_text(encoding='utf-8'))['skills']:
            for node in skill['nodes']:
                edid = edid_of[node['perk'].split('|')[1].upper()]
                counts[edid] = counts.get(edid, 0) + 1
    return counts


def check_append(written, before, new_perks):
    import state_schema   # the two quests move with state_schema_version by design (ruling R1: one bump)
    changed = [e for e, v in before.items() if written.get(e) is not None and not state_schema.stable_identity(e, written[e], v)]
    assert not changed, ('APPEND: FormIDs changed identity', changed[:5])
    gone = [e for e in before if e not in written]
    assert not gone, ('APPEND: records the pre-fix21 plugin had are gone', gone[:5])
    used = {v['id'] for v in before.values()}
    reused = [e for e in new_perks if written[e]['id'] in used]
    assert not reused, ('APPEND: a new perk reuses a used FormID', reused)
    return len(before)


# ---------------------------------------------------------------- round-21 native records

def check_records(records, hit21):
    by = {r.edid: r for r in records}
    key = lambda fid: f'{PLUGIN_KEY}|{fid:06X}'.lower()
    keys = {r.key.lower(): r for r in records}
    for seconds in range(1, hit21.SOAK_MAX_SECONDS + 1):
        spell = by[hit21.soak_edid(seconds)]
        efits = [v for s, v in spell.ss if s == 'EFIT']
        assert len(efits) == 1 and struct.unpack('<fII', efits[0])[2] == seconds, ('RECORDS: soak duration', seconds)
        assert struct.unpack_from('<I', spell.d['SPIT'], 20)[0] == 1, ('RECORDS: soak must be contact', seconds)
    for ability, chill, feet, pct in ((hit21.ICE_ARMOR, hit21.ICE_CHILL, hit21.ICE_RADIUS_FEET, hit21.ICE_CHILL_PCT),
                                      (hit21.ICE_ARMOR_WIDE, hit21.ICE_CHILL_WIDE, hit21.ICE_RADIUS_WIDE_FEET, hit21.ICE_CHILL_WIDE_PCT)):
        a = keys[key(ability)]
        assert struct.unpack_from('<I', a.d['SPIT'], 8)[0] == 4, ('RECORDS: cloak must be an ability', a.edid)
        cloak = keys[a.refs('EFID')[0].lower()]
        data = cloak.d['DATA']
        assert struct.unpack_from('<I', data, 64)[0] == 35, ('RECORDS: cloak archetype', cloak.edid)
        assert struct.unpack_from('<I', data, 8)[0] & 0xFFFFFF == chill, ('RECORDS: cloak applies the wrong spell', cloak.edid)
        assert abs(struct.unpack('<fII', a.d['EFIT'])[0] - feet) < 1e-6, ('RECORDS: cloak radius', a.edid)
        c = keys[key(chill)]
        assert struct.unpack_from('<I', c.d['SPIT'], 20)[0] == 2, ('RECORDS: cloak payload must be aimed', c.edid)
        # Round 22 added a second effect (the freeze-gauge variant, build/fix22_records.py); the round-21 chill is the first.
        first_efit = next(v for s, v in c.ss if s == 'EFIT')
        assert abs(struct.unpack('<fII', first_efit)[0] - pct) < 1e-6, ('RECORDS: chill percent', c.edid)
        effect = keys[c.refs('EFID')[0].lower()]
        assert effect.d.get('CTDA') == hit21.HOSTILE_CTDA, ('RECORDS: chill must be hostile-only', effect.edid)
    for edid, delivery in (('ESSB_Hush', 1), ('ESSB_HushSpent', 1), ('ESSB_RiposteWindow', 0)):
        assert struct.unpack_from('<I', by[edid].d['SPIT'], 20)[0] == delivery, ('RECORDS: delivery', edid)
    new = hit21.new_edids()
    assert new <= set(by), ('RECORDS: round-21 records missing', sorted(new - set(by)))
    return len(new)   # 29 soak spells (the 10 s one is round 20's) + 寂 2 + 寂滅 2 + 反擊 2 + 冰甲 7 = 42


def check_mcm(config):
    rows = [r for page in config['pages'] for r in page['content'] if r.get('id') == 'ESSB_NodeScale']
    assert len(rows) == 1, 'MCM: 節點倍率 slider missing'
    v = rows[0]['valueOptions']
    assert (v['min'], v['max'], v['defaultValue']) == (1.0, 5.0, 3.0), ('MCM: R3 slider range', v)
    return 1


# ---------------------------------------------------------------- VMAD: no script property holds a tree perk

def vmad_object_refs(data):
    """Every object FormID in a VMAD subrecord (scripts, properties incl. arrays, alias fragments)."""
    refs, pos = [], 0

    def unpack(fmt):
        nonlocal pos
        v = struct.unpack_from(fmt, data, pos)
        pos += struct.calcsize(fmt)
        return v

    def string():
        nonlocal pos
        n = unpack('<H')[0]
        pos += n

    def value(typ):
        nonlocal pos
        if typ == 1:
            refs.append(unpack('<HHI')[2])
        elif typ == 2:
            string()
        elif typ in (3, 4):
            pos += 4
        elif typ == 5:
            pos += 1
        elif typ in (11, 12, 13, 14, 15):
            for _ in range(unpack('<I')[0]):
                value(typ - 10)
        else:
            raise AssertionError(('VMAD type', typ))

    def scripts():
        version, fmt, count = unpack('<HHH')
        assert version == 5 and fmt == 2
        for _ in range(count):
            string()
            unpack('<B')
            for _ in range(unpack('<H')[0]):
                string()
                typ, _status = unpack('<BB')
                value(typ)

    scripts()
    if pos < len(data):
        assert unpack('<B')[0] == 2 and unpack('<H')[0] == 0
        string()
        for _ in range(unpack('<H')[0]):
            refs.append(unpack('<HHI')[2])
            scripts()
    assert pos == len(data), (pos, len(data))
    return refs


def check_vmad_perks(records):
    """Perks are read by position only through ESSBTrees (GetFormFromFile of a computed ID, checked by
    fix21_identity); no script property may bind a tree-cell perk (ESSB_P_<tree>_<r>_<k>_M<n>/B<n>) directly."""
    tree_perks = {int(r.key.split('|')[1], 16) & 0xFFFFFF: r.edid for r in records
                  if r.sig == 'PERK' and re.fullmatch(r'ESSB_P_[a-z]+_[0-2]_[0-4]_[MB]\d+', r.edid)}
    bound = []
    for r in records:
        if 'VMAD' in r.d:
            bound += [(r.edid, tree_perks[f & 0xFFFFFF]) for f in vmad_object_refs(r.d['VMAD'])
                      if (f >> 24) == 1 and (f & 0xFFFFFF) in tree_perks]
    assert not bound, ('VMAD: a script property holds a tree perk', bound[:5])
    return sum(1 for r in records if 'VMAD' in r.d)


# ---------------------------------------------------------------- run with injected faults

def expect_fail(label, action, needle, faults):
    try:
        action()
    except AssertionError as e:
        assert needle in str(e), (label, 'caught for the wrong reason', str(e))
        faults.append(label)
        return
    raise AssertionError(('injected fault not caught', label))


def run(b=None):
    if b is None:
        import build_v03 as b
    import fix21_records as hit21, fix21_history, tree_v04
    p = plan()
    scale = json.loads((ROOT / 'settings.json').read_text(encoding='utf-8'))['node_percent_scale']
    faults = []

    expected = takeover_trees(p)
    assert expected == {2, 3, 7, 8, 9, 11}, ('R2: v0.4 takeover trees', expected)   # frost lightning divine poison water astral
    got = r2_boosts(NEW)
    check_r2(got, expected, scale)
    expect_fail('R2 pre-fix21 OnEnd (every tree)', lambda: check_r2(r2_boosts(R20), expected, scale), 'R2: takeover granted', faults)
    expect_fail('R2 expected set loses a tree', lambda: check_r2(got, expected - {9}, scale), 'R2: takeover granted', faults)

    records, meta = b.read_plugin(b.OUT / b.PLUGIN)
    branch_keys, main_keys = list(b.BRANCH_ENTRY_NODES), list(b.MAIN_ENTRY_NODES)
    entries = check_entries(records, p, branch_keys, main_keys, 'ESSB_P_BaseRules')
    swapped = [('earth', '磐石') if k == ('earth', '不動') else k for k in branch_keys]
    expect_fail('ENTRIES key names a neighbouring node', lambda: check_entries(records, p, swapped, main_keys, 'ESSB_P_BaseRules'),
                'ENTRIES: perks with entry points differ', faults)
    rock = check_rock_armor(records, b)

    written = json.loads((ROOT / 'build/v03-formids.json').read_text(encoding='utf-8'))['records']
    counts = csf_nodes(b, written)
    retired = check_retired(records, p, counts)
    assert retired == 49, retired
    bad = copy.deepcopy(records)
    victim = next(r for r in bad if r.edid == perk_edid('fire', 2, 0, 1))   # fire 關閉新手 slot 1 (v0.3 洩壓, retired)
    victim.ss = [(s, (v[:3] + b'\x01' + v[4:]) if s == 'DATA' else v) for s, v in victim.ss]
    expect_fail('RETIRED perk made playable', lambda: check_retired(bad, p, counts), 'RETIRED: must be unplayable', faults)
    expect_fail('RETIRED perk left on the CSF tree', lambda: check_retired(records, p, dict(counts, **{victim.edid: 1})),
                'RETIRED: still on a CSF tree', faults)

    before = json.loads((ROOT / '.codex/pre-fix21-snapshot/build/v03-formids.json').read_text(encoding='utf-8'))['records']
    ids = check_append(written, before, tree_v04.NEW_PERK_EDIDS)
    some = tree_v04.NEW_PERK_EDIDS[0]
    reused = dict(written, **{some: dict(written[some], id=before['ESSB_DebugLevel']['id'])})
    expect_fail('APPEND new perk on a used FormID', lambda: check_append(reused, before, tree_v04.NEW_PERK_EDIDS),
                'APPEND: a new perk reuses', faults)

    native = check_records(records, hit21)
    vmads = check_vmad_perks(records)
    forged = copy.deepcopy(records)
    victim = next(r for r in forged if 'VMAD' in r.d and r.edid == 'ESSB_MainQuest')
    perk = next(r for r in records if r.edid == 'ESSB_P_fire_0_1_M1')
    fid = 0x01000000 | (int(perk.key.split('|')[1], 16) & 0xFFFFFF)
    data = bytearray(victim.d['VMAD'])
    # Rewrite the first object property of the quest script to point at a tree perk.
    idx = next(i for i, x in enumerate(vmad_object_refs(bytes(data))) if (x >> 24) == 1)
    old = vmad_object_refs(bytes(data))[idx]
    at = bytes(data).index(struct.pack('<I', old))
    data[at:at + 4] = struct.pack('<I', fid)
    victim.ss = [(s, bytes(data) if s == 'VMAD' else v) for s, v in victim.ss]
    expect_fail('VMAD property bound to a tree perk', lambda: check_vmad_perks(forged), 'VMAD: a script property holds', faults)
    config = json.loads((b.OUT / 'MCM/Config/Elements Spellblade/config.json').read_text(encoding='utf-8'))
    check_mcm(config)
    wrong = copy.deepcopy(config)
    for page in wrong['pages']:
        for row in page['content']:
            if row.get('id') == 'ESSB_NodeScale':
                row['valueOptions']['max'] = 3.0
    expect_fail('MCM slider back to 0.25-3', lambda: check_mcm(wrong), 'MCM: R3', faults)

    history = fix21_history.self_check()
    report = dict(r2_trees=sorted(expected), entry_perks=entries, rock_layers=rock, retired=retired, identities=ids,
                  native_records=native, history=history, injected_faults=faults, runtime_tested=False)
    (ROOT / 'build/fix21-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'FIX21 ok: R2 takeover on exactly {len(expected)} v0.4 trees (pre-fix21 OnEnd fails); {entries} entry-point perks '
          f'== v0.4 names; rock armor 4%/layer x{rock} to 60%; {retired} retired perks unplayable/hidden/off CSF; '
          f'{ids} pre-fix21 FormIDs unchanged, 47 new perks on unused slots; {native} round-21 native records; '
          f'{vmads} VMAD records bind no tree perk; '
          f'MCM 節點倍率 1-5 default 3; {history["changed"]}+{history["removed"]}+{history["added"]} declared round-21 changes sealed by sha256 '
          f'({len(history["silent_edits_caught"])} reviewer silent edits caught); '
          f'{len(faults)}/{len(faults)} injected faults caught')
    return report


if __name__ == '__main__':
    run()
