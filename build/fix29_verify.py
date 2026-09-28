"""Round 29 (DLL 0.29.0): offline checks of 灌注 (v0.4 5.2 common sustain legend branch, 2.7 K_infuse, 6.2 two sliders;
.codex/design-infuse-2026-09-28.md, the user's ruling 1A-7A), each rule with an injected fault that must fail it.

  NODE     the plan (build/plan-tree-nodes.json, from v0.4 5.2) has 灌注 at common / 持續 / 傳奇, order 1 beside 永續, slot 1
           (tree_v04.NEW_SLOTS), owner DLL N2; every other node of that tier unchanged.
  PERK     ESSB_P_common_0_4_B2 (0x0022E1) is in the ESP: FULL 灌注, DESC 「分支：需 5 點。」 + the v0.4 sentence with no design
           markup, the same conditions and DATA as 永續 (level 100, 化身 >= 1); the Custom Skill Menu tree lists it from 化身.
  MCM      ESSB_InfuseCostPct / ESSB_InfuseFloorPct: float GLOBs with settings.json's defaults (10 / 30); the 平衡 page's two
           sliders (5-25 %, 0-60 %); the generated RestoreTunableDefaults writes both.
  DLL      ManifestData.h node::kCommonInfuse = {12, 0, 4, 1} and the two glob ids; ReadTuning reads them; the hit sink reads
           your magicka; Handle decides once (DecideInfuse) and pays in the hit task on the DrainAllMagicka path
           (RestoreActorValue kDamage kMagicka); the repeats go through RepeatInfuse / RepeatTerms; the log formats of the spec.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
import fix29_records as r29  # noqa: E402

PERK = 'ESSB_P_common_0_4_B2'
SIBLING = 'ESSB_P_common_0_4_B1'   # 永續
PERK_ID = '0022E1'
TEXT = ('灌注：形態開啟時，每一次重擊（弓弩為潛行射擊）自動消耗最大魔力 10%，這一擊的元素附傷 ×2；雷改為必定暴擊。'
        '魔力低於下限時不會發動。倒地目標的攻擊與無形態的重擊不算')
SKIPS = {'noform', 'nopower', 'knockdown', 'repeat', 'floor', 'mcm'}   # the spec's skip reasons
MARKUP = ('**', '`', '自有', '（見', '已決', 'DLL', 'N2')


def check_node(plan):
    errors = []
    tree = next(t for t in plan['trees'] if t['id'] == 'common')
    tier = tree['routes'][0]['tiers'][4]
    names = [(b['order'], b['name'], b['slot']) for b in tier['branches']]
    if names != [(0, '永續', 0), (1, '灌注', 1)]:
        errors.append(f'NODE: common 持續 傳奇 branches are {names}')
    infuse = next((b for b in tier['branches'] if b['name'] == '灌注'), None)
    if infuse and (infuse['owner'] != 'DLL N2' or infuse['description'] != TEXT or infuse['v03'] is not None):
        errors.append('NODE: 灌注 row differs from v0.4 5.2 (owner DLL N2, the sentence, new node)')
    if tier['main_label'] != '化身':
        errors.append('NODE: the tier is not 化身')
    return errors


def check_perk(records, manifest, csf):
    errors = []
    by = {r.edid: r for r in records}
    perk, sibling = by.get(PERK), by.get(SIBLING)
    if not perk or perk.sig != 'PERK':
        return [f'PERK: {PERK} missing']
    if manifest.get(PERK, {}).get('id') != PERK_ID:
        errors.append(f'PERK: {PERK} is not 0x{PERK_ID}')
    full = perk.d.get('FULL', b'').rstrip(b'\0').decode('utf-8')
    desc = perk.d.get('DESC', b'').rstrip(b'\0').decode('utf-8')
    if full != '灌注':
        errors.append(f'PERK: FULL {full!r}')
    if desc != '分支：需 5 點。' + TEXT:
        errors.append(f'PERK: DESC {desc!r}')
    if any(m in desc for m in MARKUP):
        errors.append('PERK: design markup in the player text')
    ctda = [v for k, v in perk.ss if k == 'CTDA']
    if not sibling or ctda != [v for k, v in sibling.ss if k == 'CTDA'] or perk.d.get('DATA') != sibling.d.get('DATA'):
        errors.append('PERK: conditions / DATA differ from 永續 (level 100, 化身 >= 1)')
    nodes = [n for s in csf['skills'] for n in s['nodes']]
    mine = [n for n in nodes if n['perk'].upper().endswith(PERK_ID)]
    avatar = [n for n in nodes if n['perk'].upper().endswith('004AC8')]
    if len(mine) != 1 or len(avatar) != 1 or mine[0]['id'] not in avatar[0]['links']:
        errors.append('PERK: the Custom Skill Menu does not list 灌注 from 化身')
    return errors


def check_mcm(records, manifest, config, state_src, settings):
    errors = []
    by = {r.edid: r for r in records}
    rows = {r.get('id'): r for r in config['pages'][1]['content']}
    for name, key, (low, high, step) in ((r29.COST_GLOBAL, r29.COST_KEY, r29.COST_RANGE), (r29.FLOOR_GLOBAL, r29.FLOOR_KEY, r29.FLOOR_RANGE)):
        g = by.get(name)
        want = float(settings[key])
        if not g or g.d.get('FNAM') != b'f' or struct.unpack('<f', g.d['FLTV'])[0] != want:
            errors.append(f'MCM: GLOB {name} missing or its default is not {want}')
        fid = manifest.get(name, {}).get('id')
        if fid != f'{r29.global_id(name):06X}':
            errors.append(f'MCM: {name} is not 0x{r29.global_id(name):06X}')
        row = rows.get(name)
        v = (row or {}).get('valueOptions', {})
        if not row or row['type'] != 'slider' or (v.get('min'), v.get('max'), v.get('step'), v.get('defaultValue')) != (low, high, step, want):
            errors.append(f'MCM: the 平衡 slider {name} is not {low}-{high} step {step} default {want}')
        body = state_src.split('Function RestoreTunableDefaults() Global')[-1].split('EndFunction')[0]
        if f'GetFormFromFile(0x{fid}, "Elements Spellblade.esp")' not in body or f'knob.SetValue({want!r})' not in body:
            errors.append(f'MCM: 回復預設設定 does not reset {name} to {want}')
    if settings.get(r29.COST_KEY) != 10.0 or settings.get(r29.FLOOR_KEY) != 30.0:
        errors.append('MCM: settings.json defaults are not 10 / 30 (取捨 4A / 7A)')
    return errors


def check_dll(cpp, header, hitmath, selflayer, timer, facts):
    errors = []
    need = {
        'node::kCommonInfuse = {12, 0, 4, 1}': re.search(r'BranchId kCommonInfuse\{12, 0, 4, 1\};', header),
        'glob ids': f'kInfuseCostPct = {hex(r29.global_id(r29.COST_GLOBAL))};' in header and
                    f'kInfuseFloorPct = {hex(r29.global_id(r29.FLOOR_GLOBAL))};' in header,
        'ReadTuning reads both': 't.infuseCostPct = global(glob::kInfuseCostPct);' in facts and
                                 't.infuseFloorPct = global(glob::kInfuseFloorPct);' in facts,
        'the sink reads your magicka': 'seen.magicka = player->AsActorValueOwner()->GetActorValue(RE::ActorValue::kMagicka);' in cpp,
        'one decision per event': cpp.count('essb::DecideInfuse(') == 1 and 'seen.magicka, seen.magickaMax, c.tuning' in cpp,
        'the DrainAllMagicka path': re.search(r'float SpendInfuse\([^)]*\)\n\{[^}]*RestoreActorValue\(RE::ACTOR_VALUE_MODIFIER::kDamage, '
                                              r'RE::ActorValue::kMagicka, -spend\)', cpp),
        'repeats share the charge': 'essb::RepeatInfuse(infuse)' in cpp and 'essb::RepeatTerms(terms, againInfuse)' in cpp and
                                    'again.cost = 0.0f;' in selflayer,
        'the corpse pays nothing': 'if (infuse.on && corpse) {' in cpp,
        'hit L2 log': 'cut=%d infuse=%d cost=%.1f"' in cpp,
        'spend L4 log': '"[ESSB][infuse][L4] %08X spent=%.1f max=%.1f before=%.1f after=%.1f floor=%.1f k=%.1f crit=%d' in cpp,
        'skip L4 log': '"[ESSB][infuse][L4] %08X skip=%s' in cpp,
        'the second: upkeep alone': 'out.spent * n6::kFlowMagickaShare' in timer and 'infused=%.2f' in cpp and
                                    'f.infused = state.infusedSince.exchange(0.0f);' in cpp,
        'K_infuse on the proc only': 'proc.magnitude *= kInfuseK;' in hitmath and 'proc.magnitude *= kInfuseCrit;' in hitmath and
                                     hitmath.index('proc.magnitude *= kInfuseK;') < hitmath.index('proc.magnitude += terms.flat[element]'),
    }
    for what, ok in need.items():
        if not ok:
            errors.append(f'DLL: {what}')
    names = re.search(r'constexpr const char\* names\[\] = \{ "none", "nonode", ([^}]*)\};', hitmath)
    if not names or {n.strip().strip('"') for n in names.group(1).split(',')} != SKIPS:
        errors.append('DLL: the skip names are not the spec\'s noform|nopower|knockdown|repeat|floor|mcm')
    return errors


def faults(plan, records, manifest, csf, config, state_src, settings, src):
    """Each injected fault must fail its check."""
    import copy
    caught = []

    def expect(name, errors):
        assert errors, f'FIX29 fault not caught: {name}'
        caught.append(name)

    p = copy.deepcopy(plan)
    tier = next(t for t in p['trees'] if t['id'] == 'common')['routes'][0]['tiers'][4]
    tier['branches'][1]['slot'] = 2
    expect('NODE slot moved', check_node(p))
    p = copy.deepcopy(plan)
    tier = next(t for t in p['trees'] if t['id'] == 'common')['routes'][0]['tiers'][4]
    tier['branches'][1]['description'] += '（見 2.7）'
    expect('NODE text changed', check_node(p))

    class Rec:
        def __init__(self, r, **d):
            self.edid, self.sig, self.ss = r.edid, r.sig, list(r.ss)
            self.d = dict(r.d, **d)
    by = {r.edid: r for r in records}
    fake = [Rec(by[PERK], DESC='分支：需 5 點。灌注：**形態開啟時**'.encode('utf-8') + b'\0') if r.edid == PERK else r for r in records]
    expect('PERK markdown in DESC', check_perk(fake, manifest, csf))
    fake = [r for r in records if r.edid != PERK]
    expect('PERK missing', check_perk(fake, manifest, csf))
    odd = copy.deepcopy(csf)
    for s in odd['skills']:
        s['nodes'] = [n for n in s['nodes'] if not n['perk'].upper().endswith(PERK_ID)]
    expect('PERK not in the Custom Skill Menu', check_perk(records, manifest, odd))
    odd_config = copy.deepcopy(config)
    for r in odd_config['pages'][1]['content']:
        if r.get('id') == r29.FLOOR_GLOBAL:
            r['valueOptions']['max'] = 100.0
    expect('MCM floor range', check_mcm(records, manifest, odd_config, state_src, settings))
    expect('MCM reset misses the cost', check_mcm(records, manifest, config, state_src.replace('knob.SetValue(10.0)', 'knob.SetValue(1.0)'), settings))
    expect('MCM default 20', check_mcm(records, manifest, config, state_src, dict(settings, infuse_cost_pct=20.0)))
    cpp, header, hitmath, selflayer, timer, facts = src
    expect('DLL task reads the magicka', check_dll(cpp.replace('seen.magicka = player->AsActorValueOwner()', 'float m = player->AsActorValueOwner()'),
                                                   header, hitmath, selflayer, timer, facts))
    expect('DLL decides per repeat', check_dll(cpp.replace('essb::RepeatInfuse(infuse)', 'essb::DecideInfuse(infuse)'), header, hitmath,
                                               selflayer, timer, facts))
    expect('DLL spends by a spell', check_dll(cpp.replace('RE::ActorValue::kMagicka, -spend)', 'RE::ActorValue::kMagicka, spend)'), header,
                                              hitmath, selflayer, timer, facts))
    expect('DLL repeat pays again', check_dll(cpp, header, hitmath, selflayer.replace('again.cost = 0.0f;', '(void)again.cost;'), timer, facts))
    expect('DLL flat part doubled', check_dll(cpp, header, hitmath.replace('proc.magnitude *= kInfuseK;', '(void)0;', 1) + '\nproc.magnitude += terms.flat[element]; proc.magnitude *= kInfuseK;',
                                              selflayer, timer, facts))
    expect('DLL refund with the infusion', check_dll(cpp, header, hitmath, selflayer,
                                                     timer.replace('out.spent * n6::kFlowMagickaShare', '(out.spent + f.infused) * n6::kFlowMagickaShare'), facts))
    expect('DLL skip name', check_dll(cpp, header, hitmath.replace('"knockdown"', '"downed"'), selflayer, timer, facts))
    expect('DLL L2 log', check_dll(cpp.replace('infuse=%d cost=%.1f"', 'infuse=%d"'), header, hitmath, selflayer, timer, facts))
    return caught


def run(b):
    plan = json.loads((ROOT / 'build/plan-tree-nodes.json').read_text(encoding='utf-8'))
    records, _meta = b.read_plugin(b.OUT / b.PLUGIN)
    manifest = json.loads((ROOT / 'build/v03-formids.json').read_text(encoding='utf-8'))['records']
    csf = json.loads((b.OUT / 'SKSE/Plugins/CustomSkills/ESSB_common.json').read_text(encoding='utf-8'))
    config = json.loads((b.OUT / 'MCM/Config/Elements Spellblade/config.json').read_text(encoding='utf-8'))
    state_src = (ROOT / 'src/ESSBState.psc').read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    settings = json.loads((ROOT / 'settings.json').read_text(encoding='utf-8'))
    inc = ROOT / 'native/include'
    src = ((ROOT / 'native/src/Plugin.cpp').read_text(encoding='utf-8'), (inc / 'ManifestData.h').read_text(encoding='utf-8'),
           (inc / 'HitMath.h').read_text(encoding='utf-8'), (inc / 'SelfLayer.h').read_text(encoding='utf-8'),
           (inc / 'Timer.h').read_text(encoding='utf-8'), (inc / 'EngineFacts.h').read_text(encoding='utf-8'))
    errors = (check_node(plan) + check_perk(records, manifest, csf) + check_mcm(records, manifest, config, state_src, settings) +
              check_dll(*src))
    assert not errors, '\n  '.join(['FIX29 failed:'] + errors)
    caught = faults(plan, records, manifest, csf, config, state_src, settings, src)
    (ROOT / 'build/fix29-check.json').write_text(json.dumps({'faults_caught': caught, 'perk': PERK, 'perk_id': PERK_ID,
                                                             'globals': {r29.COST_GLOBAL: settings[r29.COST_KEY],
                                                                         r29.FLOOR_GLOBAL: settings[r29.FLOOR_KEY]}},
                                                            ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'FIX29 ok: 灌注 at common 持續 傳奇 slot 1 beside 永續 ({PERK} 0x{PERK_ID}, clean text, 化身 >= 1, listed in the Custom '
          f'Skill Menu); 灌注成本 {settings[r29.COST_KEY]:g}% / 灌注下限 {settings[r29.FLOOR_KEY]:g}% GLOBs, sliders and reset; the DLL '
          f'reads them, the sink\'s magicka, one decision and one payment per event on the DrainAllMagicka path, the spec\'s logs; '
          f'{len(caught)}/{len(caught)} faults caught')


if __name__ == '__main__':
    import runpy
    run(runpy.run_path(str(ROOT / 'build_v03.py'), run_name='fix29'))
