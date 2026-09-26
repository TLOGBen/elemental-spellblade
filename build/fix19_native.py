"""Native (DLL) build contract: generated header, node-table identity, test fixtures, freshness receipt,
packaging, verification.

Round 20 (slice N2) layout, round 21 (v0.4 trees) naming:
  node_table(b)       the skill-tree nodes the DLL reads, by v0.4 name (NODE_IDENTITY); each slot is looked up in
                      the identity table (build/plan-tree-nodes.json), never written here, and build/fix21_identity.py
                      checks every name against the node status table
  generate_header(b)  -> native/include/ManifestData.h (record FormIDs, node slots, settings, version)
  fixture(b)          -> build/fix20-magnitude-table.json (group A, from build/fix20_reference.py) and
                         build/fix20-wiring.json (group B, from the generator's record identities)
  inputs()            -> hashes of exactly what the DLL and its tests are built from
  require_fresh(b)    -> the DLL receipt matches those hashes and the generated files are current
  verify(b)           -> ESP / manifest / fixture identities, proc spells single-damage-effect, native tests
The file keeps its round-19 name because build_v03.py and native/build.py import it as the native contract.
"""
from pathlib import Path
import hashlib, json, struct, subprocess, shutil, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build'))
import fix20_records as hit20
import fix21_records as hit21
import fix20_fixture
import fix20_reference as _ref
NATIVE = ROOT / 'native'
NATIVE_VERSION = '0.21.0'
NATIVE_HIT = 0x52d1
NATIVE_WANTED = 0x52d2
NATIVE_GLOBALS = {'ESSB_NativeHit', 'ESSB_NativeWanted'}      # round 19: the MCM shows both
NEW_EDIDS = NATIVE_GLOBALS | hit20.new_edids() | hit21.new_edids()   # every record the native slices added
DEPS = {
    'CommonLibSSE-NG': ('https://github.com/CharmedBaryon/CommonLibSSE-NG', 'b93280e832f263dbef44e44cbe2936622a02f91a'),
    'spdlog': ('https://github.com/gabime/spdlog', '27cb4c76708608465c413f6d0e6b8d99a4d84302'),
    'rapidcsv': ('https://github.com/d99kris/rapidcsv', 'a98b85e663114b8fdc9c0dc03abf22c296f38241'),
    'json': ('https://github.com/nlohmann/json', '9cca280a4d0ccf0c08f47a99aa71d1b0e52f8d03'),
}
HEADER = NATIVE / 'include/ManifestData.h'
TABLE = ROOT / fix20_fixture.TABLE
WIRING = ROOT / fix20_fixture.WIRING
ENTRY_POINT = 2  # PRKE effect type: 0 quest stage, 1 ability, 2 entry point
ENTRY_51 = 51    # Apply Combat Hit Spell

# Every node:: constant the DLL reads -> (tree id, v0.4 node name). The same mapping the reference model resolves
# (build/fix20_reference.NODE_NAMES); the slot of each is looked up by name in the identity table.
NODE_IDENTITY = dict(_ref.NODE_NAMES)
ELEMENT_SHORT = ['火', '冰', '雷', '土', '風', '血', '聖', '毒', '水', '暗', '星']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_if_changed(path, text):
    data = text.encode('utf8')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def settings():
    return json.loads((ROOT / 'settings.json').read_text(encoding='utf8'))


def address_library():
    """The Address Library file the DLL pins by SHA-256 (settings.json address_library_bin)."""
    path = Path(settings()['address_library_bin'])
    if not path.is_file():
        raise RuntimeError(f'address_library_bin not found: {path}; set it in settings.json')
    return path


# ---------------------------------------------------------------- identities


def node_table(b):
    """{constant: slot} for every node the DLL reads, looked up by v0.4 name in the identity table; the element
    skeleton tables (kProcAdept / kProcMaster) are checked by name too."""
    import fix20_reference as ref
    # parse + balance text without plan_trees.build(): build() rewrites build/plan-tree-nodes.json, and this runs
    # after main() has written the decided plan there.
    plan = b.apply_fix8_decisions(b.plan_trees.apply_balance_text(b.plan_trees.parse()))
    trees = {t['index']: t for t in plan['trees']}

    def tier(tree, route, level):
        return trees[tree]['routes'][route]['tiers'][level]

    for name, slot in ref.NODES.items():
        tree_id, label = NODE_IDENTITY[name]
        cell = tier(*slot[:3])
        assert trees[slot[0]]['id'] == tree_id, (name, slot, tree_id)
        if len(slot) == 3:
            assert cell['main_label'] == label, (name, slot, cell['main_label'], label)
        else:
            branch = next((x for x in cell['branches'] if x['slot'] == slot[3]), None)
            assert branch and branch['name'] == label, (name, slot, branch, label)
    for element in range(1, 12):
        short = ELEMENT_SHORT[element - 1]
        adept, master = ref.adept(element), ref.master(element)
        if adept is None:
            assert element == ref.WATER and tier(element - 1, 0, 1)['main_label'] != f'{short}附傷' \
                and tier(element - 1, 0, 3)['main_label'] != f'同調每段{short}附傷'
            continue
        assert tier(*adept)['main_label'] == f'{short}附傷', (element, tier(*adept)['main_label'])
        assert tier(*master)['main_label'] == f'同調每段{short}附傷', (element, tier(*master)['main_label'])
    return dict(ref.NODES)


def globals_(b):
    """Every GLOB the DLL reads, by editor ID."""
    ids = {k: b.ID_GLOB[k] for k in ['ESSB_Enabled', 'ESSB_FormActive', 'ESSB_CurrentElement', 'ESSB_DebugLevel']}
    ids |= {'ESSB_NativeHit': NATIVE_HIT, 'ESSB_NativeWanted': NATIVE_WANTED}
    for name in ['ESSB_BaseDamageMult', 'ESSB_NodeScale', 'ESSB_MultDrain', 'ESSB_MultRecovery', 'ESSB_MultDuration',
                 'ESSB_SlowCapPct', 'ESSB_WaterWetSlowPct', 'ESSB_WaterClearStamina', 'ESSB_ManabreakMaxmagPct']:
        ids[name] = b.ID_BALANCE_GLOB[name][0]
    mech = [name for name, _ in b.MECH_GLOBALS]
    for name in ['ESSB_SyncStage', 'ESSB_PrevElement', 'ESSB_TwinElement']:
        ids[name] = b.ID_MECH_GLOB + mech.index(name)
    for name in ['ESSB_EnvWet', 'ESSB_EnvNight']:
        ids[name] = b.ID_GLOB_ENGINE[name]
    for tree, key in enumerate(b.TREES):
        ids[f'ESSB_Lvl_{key}'] = b.ID_TREE_GLOB['Lvl'] + tree
    return ids


# Tuning field (EngineFacts.h ReadTuning) -> GLOB editor ID; group B checks the C++ reads the same GLOB.
TUNING_GLOBALS = {
    'baseDamageMult': 'ESSB_BaseDamageMult', 'nodeScale': 'ESSB_NodeScale', 'multDrain': 'ESSB_MultDrain',
    'multRecovery': 'ESSB_MultRecovery', 'multDuration': 'ESSB_MultDuration', 'slowCapPct': 'ESSB_SlowCapPct',
    'wetSlowPct': 'ESSB_WaterWetSlowPct', 'waterClearStamina': 'ESSB_WaterClearStamina',
    'seizeMaxPct': 'ESSB_ManabreakMaxmagPct', 'syncStage': 'ESSB_SyncStage', 'envWet': 'ESSB_EnvWet',
    'envNight': 'ESSB_EnvNight', 'prevElement': 'ESSB_PrevElement', 'twinElement': 'ESSB_TwinElement',
}


def proc_rows(b):
    return b.hit18.variants(b)


def spells(b):
    """Cast name (HitMath.h Cast) -> the single spell record the DLL uses for it."""
    rows = {
        'kDrainMagicka': (b.util_spell_id(2), 'ESSB_Util_DrainMagicka'),
        'kDrainStamina': (b.util_spell_id(3), 'ESSB_Util_DrainStamina'),
        'kHeal': (b.util_spell_id(4), 'ESSB_Util_RestoreHealth'),
        'kRestoreMagicka': (b.util_spell_id(5), 'ESSB_Util_RestoreMagicka'),
        'kRestoreStamina': (b.util_spell_id(6), 'ESSB_Util_RestoreStamina'),
        'kTrueDamage': (b.ID_TRUE_SPELL, 'ESSB_TrueDamageSpell'),
        'kDispelMark': (b.ID_MANABREAK_SPELL, 'ESSB_ManaBreakSpell'),
        'kSpendMagicka': (hit20.SPEND, 'ESSB_Native_SpendMagicka'),
        'kBloodGuard': (hit20.GUARD, 'ESSB_BloodGuard'),
        'kHushSpent': (hit21.HUSH_SPENT, 'ESSB_HushSpent'),
    }
    for seconds in range(1, hit20.SILENCE_COUNT + 1):
        rows[f'kSilence{seconds}'] = (hit20.SILENCE + seconds - 1, hit20.silence_edid(seconds))
    for seconds in range(1, hit21.SOAK_MAX_SECONDS + 1):
        rows[f'kSoak{seconds}'] = (hit21.soak_id(seconds), hit21.soak_edid(seconds))
    return {k: dict(local_id=v[0], editor_id=v[1]) for k, v in rows.items()}


def effects(b):
    rows = {
        'kBloodMark': (b.ID_MARK_EFFECT + b.ELEMENTS.index('Blood'), 'ESSB_MarkEffect_Blood'),
        'kSilence': (b.ID_SILENCE_EFFECT, 'ESSB_SilenceEffect'),
        'kBloodGuard': (hit20.GUARD_EFFECT, 'ESSB_BloodGuardEffect'),
        'kEchoPending': (hit20.ECHO_EFFECT, 'ESSB_EchoPendingEffect'),
        'kTwinWindow': (hit20.TWIN_EFFECT, 'ESSB_TwinWindowEffect'),
        'kRiposteWindow': (hit21.RIPOSTE_EFFECT, 'ESSB_RiposteWindowEffect'),
        'kHush': (hit21.HUSH_EFFECT, 'ESSB_HushEffect'),
        'kHushSpent': (hit21.HUSH_SPENT_EFFECT, 'ESSB_HushSpentEffect'),
    }
    return {k: dict(local_id=v[0], editor_id=v[1]) for k, v in rows.items()}


def vanilla(b):
    """Skyrim.esm forms the target facts read (the same ones ESSBController's properties point at)."""
    return {
        'kUndeadKeyword': dict(form_id=b.FID_KW_UNDEAD, kind='KYWD'),
        'kDaedraKeyword': dict(form_id=b.FID_KW_DAEDRA, kind='KYWD'),
        'kArmorSpellKeyword': dict(form_id=b.FID_KW_ARMOR_SPELL, kind='KYWD'),
        'kCloakKeyword': dict(form_id=b.FID_KW_CLOAK, kind='KYWD'),
        'kNecroClass': dict(form_id=b.FID_CLASS_NECRO, kind='CLAS'),
        'kNecroFaction': dict(form_id=b.FID_FACT_NECRO, kind='FACT'),
    }


# ---------------------------------------------------------------- generated header


def _slot(slot):
    return '{' + ', '.join(map(str, slot)) + '}'


def header_text(b):
    import fix20_reference as ref
    nodes = node_table(b)
    s = settings()
    g = globals_(b)
    L = ['#pragma once',
         '// Generated by build/fix19_native.py from build_v03.py, build/fix20_records.py and settings.json. Do not edit.',
         '#include "NodeIds.h"', '#include <cstdint>', '#include <string_view>', 'namespace essb {', '',
         'struct ProcRow { int element; int power; std::uint32_t id; std::string_view name; };',
         '// Element proc spells: element x normal / power (build/fix18_records.py variants).',
         'inline constexpr ProcRow procRows[] = {']
    for v in proc_rows(b):
        L.append(f'    {{{v["e"]}, {v["p"]}, {hex(v["id"])}, "{v["edid"]}"}},')
    L += ['};', '', '// Spell per planned cast (HitMath.h Cast). Local FormIDs in Elements Spellblade.esp.', 'namespace spell {']
    sp = spells(b)
    for name, row in sp.items():
        if not name.startswith(('kSilence', 'kSoak')):
            L.append(f'inline constexpr std::uint32_t {name} = {hex(row["local_id"])};  // {row["editor_id"]}')
    L.append('inline constexpr std::uint32_t kSilence[' + str(hit20.SILENCE_COUNT) + '] = {'
             + ', '.join(hex(sp[f'kSilence{i}']['local_id']) for i in range(1, hit20.SILENCE_COUNT + 1)) + '};  // ESSB_Native_Silence_1..8')
    L.append('inline constexpr std::uint32_t kSoak[' + str(hit21.SOAK_MAX_SECONDS) + '] = {'
             + ', '.join(hex(sp[f'kSoak{i}']['local_id']) for i in range(1, hit21.SOAK_MAX_SECONDS + 1))
             + '};  // soaked slow of 1..30 s: ESSB_Native_Soak_<s>, 10 s = ESSB_Native_SoakSlow')
    L += ['}  // namespace spell', '', '// Effects the DLL looks for on the target or the player.', 'namespace effect {']
    for name, row in effects(b).items():
        L.append(f'inline constexpr std::uint32_t {name} = {hex(row["local_id"])};  // {row["editor_id"]}')
    L += ['}  // namespace effect', '', 'namespace glob {']
    names = {'ESSB_Enabled': 'kEnabled', 'ESSB_FormActive': 'kFormActive', 'ESSB_CurrentElement': 'kCurrentElement',
             'ESSB_DebugLevel': 'kDebugLevel', 'ESSB_NativeHit': 'kNativeHit', 'ESSB_NativeWanted': 'kNativeWanted'}
    for edid, fid in g.items():
        if edid.startswith('ESSB_Lvl_'):
            continue
        cname = names.get(edid, 'k' + edid.removeprefix('ESSB_'))
        L.append(f'inline constexpr std::uint32_t {cname} = {hex(fid)};  // {edid}')
    L.append('inline constexpr std::uint32_t kTreeLevel[13] = {' + ', '.join(hex(g[f'ESSB_Lvl_{k}']) for k in b.TREES) + '};  // ESSB_Lvl_<tree>')
    L += ['}  // namespace glob', '', '// Skyrim.esm forms (local FormIDs in Skyrim.esm).', 'namespace vanilla {']
    for name, row in vanilla(b).items():
        L.append(f'inline constexpr std::uint32_t {name} = {hex(row["form_id"])};  // {row["kind"]}')
    L += ['}  // namespace vanilla', '',
          '// Perk layout (build_v03 ID_MAIN_PERK / ID_BRANCH_PERK, plan_trees MAIN_MAX_RANK / MAX_BRANCH).',
          f'inline constexpr std::uint32_t kMainPerkBase = {hex(b.ID_MAIN_PERK)};',
          f'inline constexpr std::uint32_t kBranchPerkBase = {hex(b.ID_BRANCH_PERK)};',
          f'inline constexpr int kMainMaxRank = {b.plan_trees.MAIN_MAX_RANK};',
          f'inline constexpr int kBranchSlots = {b.plan_trees.MAX_BRANCH};', '',
          '// Node slots the DLL reads, looked up by v0.4 name (NODE_IDENTITY in fix19_native.py, build/fix21_identity.py).',
          'namespace node {']
    for name, slot in nodes.items():
        kind = 'NodeId' if len(slot) == 3 else 'BranchId'
        tree_id, label = NODE_IDENTITY[name]
        L.append(f'inline constexpr {kind} {name}{_slot(slot)};  // v0.4 {tree_id} {label}')
    for label, fn in (('kProcAdept', ref.adept), ('kProcMaster', ref.master)):
        cells = ['kNoNode'] + [_slot(fn(e)) if fn(e) else 'kNoNode' for e in range(1, 12)]
        L.append(f'inline constexpr NodeId {label}[12] = {{{", ".join(cells)}}};  // [element]; water has none')
    L += ['}  // namespace node', '',
          '// settings.json element_damage (B_min, B_max per element; [0] unused) and noform_base_true.',
          'inline constexpr float kElementDamage[12][2] = {{0.0f, 0.0f}, '
          + ', '.join('{' + ', '.join(f'{float(x)}f' for x in s['element_damage'][n]) + '}' for n in b.ELEMENTS) + '};',
          f'inline constexpr float kNoFormBaseTrue = {float(s["noform_base_true"])}f;',
          'inline constexpr std::string_view elementNames[12] = {"無元素", ' + ', '.join(f'"{z}"' for z in b.ZH) + '};',
          f'inline constexpr char nativeVersion[] = "{NATIVE_VERSION}";',
          f'inline constexpr char addressHash[] = "{sha(address_library())}";',
          '}  // namespace essb']
    return '\n'.join(L) + '\n'


def generate_header(b):
    write_if_changed(HEADER, header_text(b))
    write_if_changed(NATIVE / 'dependencies.lock.json', json.dumps(DEPS, indent=2) + '\n')


def fixture(b):
    """Write the group A table (reference model) and the group B wiring expectations. Returns the scenario count."""
    count = fix20_fixture.write(b, settings(), write_if_changed, ROOT)
    g = globals_(b)
    fix20_fixture.wiring(b, node_table(b), {k: v['local_id'] for k, v in spells(b).items()},
                         dict(tuning={field: g[edid] for field, edid in TUNING_GLOBALS.items()},
                              levels=[g[f'ESSB_Lvl_{k}'] for k in b.TREES]),
                         write_if_changed, ROOT)
    return count


# ---------------------------------------------------------------- freshness, package, verify


def perk_entries(record):
    """Yield (prke, fields) for each perk entry; fields maps subrecord tag -> list of values."""
    entry = None
    for tag, value in record.ss:
        if tag == 'PRKE':
            entry = (value, [])
        elif entry is not None:
            if tag == 'PRKF':
                yield entry
                entry = None
            else:
                entry[1].append((tag, value))


def entry51_count(record):
    """Entry-point entries of type 51. DATA is only an entry-point id when PRKE says entry point."""
    count = 0
    for prke, fields in perk_entries(record):
        if prke[0] != ENTRY_POINT:
            continue
        data = next(v for t, v in fields if t == 'DATA')
        count += data[0] == ENTRY_51
    return count


def input_paths():
    """Exactly what the DLL and its tests are generated from; nothing else forces a rebuild."""
    paths = [ROOT / 'build/fix19_native.py', ROOT / 'build/fix20_records.py', ROOT / 'build/fix21_records.py',
             ROOT / 'build/fix20_reference.py',
             ROOT / 'build/fix20_fixture.py', TABLE, WIRING, NATIVE / 'build.py', NATIVE / 'CMakeLists.txt',
             NATIVE / 'dependencies.lock.json', NATIVE / 'toolchain.lock.json']
    for part in ['src', 'include', 'tests', 'cmake']:
        paths += [p for p in (NATIVE / part).rglob('*') if p.is_file()]
    return sorted(paths)


def inputs():
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in input_paths()}


def check_deps():
    for name, (_url, commit) in DEPS.items():
        folder = NATIVE / 'deps' / name
        actual = subprocess.check_output(['git', '-C', str(folder), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != commit:
            raise RuntimeError(f'Native dependency drift: {name}: {actual} != {commit}')
        subprocess.run(['git', '-C', str(folder), 'diff', '--exit-code', 'HEAD', '--'], check=True, stdout=subprocess.DEVNULL)


def require_fresh(b):
    dll = NATIVE / 'out/Release/ElementsSpellblade.dll'
    receipt = NATIVE / 'out/build-receipt.json'
    if not dll.is_file() or not receipt.is_file():
        raise RuntimeError('NATIVE DLL missing: run python -B native/build.py first; no entry-51 fallback')
    if HEADER.read_text(encoding='utf8') != header_text(b):
        raise RuntimeError('NATIVE DLL stale: generated ManifestData.h differs from build_v03/settings; run python -B native/build.py')
    data = json.loads(receipt.read_text(encoding='utf8'))
    if data['inputs'] != inputs() or data['dll_sha256'] != sha(dll):
        raise RuntimeError('NATIVE DLL stale: run python -B native/build.py; source/fixture/DLL hash mismatch')
    check_deps()
    return dll


def manifest(b):
    """Runtime identity file: the DLL checks every compiled constant against it and the ESP at data load."""
    return {'schema': 2, 'plugin': b.PLUGIN, 'native_version': NATIVE_VERSION, 'runtime': '1.5.97.0',
            'globals': globals_(b),
            'proc_spells': [{'local_id': v['id'], 'editor_id': v['edid'], 'element': v['e'], 'power': v['p']} for v in proc_rows(b)],
            'spells': spells(b), 'effects': effects(b), 'vanilla': vanilla(b),
            'perks': {'main_base': b.ID_MAIN_PERK, 'branch_base': b.ID_BRANCH_PERK,
                      'main_max_rank': b.plan_trees.MAIN_MAX_RANK, 'branch_slots': b.plan_trees.MAX_BRANCH}}


def package(b):
    dll = require_fresh(b)
    folder = b.OUT / 'SKSE/Plugins'
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dll, folder / 'ElementsSpellblade.dll')
    write_if_changed(folder / 'ElementsSpellblade/manifest.json', json.dumps(manifest(b), ensure_ascii=False, indent=2) + '\n')


def effect_ids(record):
    return [struct.unpack('<I', v)[0] & 0xffffff for k, v in record.ss if k == 'EFID']


def verify(b):
    dll = require_fresh(b)
    records, meta = b.read_plugin(b.OUT / b.PLUGIN)
    assert meta['masters'] == ['Skyrim.esm']
    ours = {r.edid: entry51_count(r) for r in records if r.sig == 'PERK'}
    assert sum(ours.values()) == 0, {k: v for k, v in ours.items() if v}
    by = {r.edid: r for r in records}
    key_id = {r.edid: int(r.key.split('|')[1], 16) for r in records}
    m = json.loads((b.OUT / 'SKSE/Plugins/ElementsSpellblade/manifest.json').read_text(encoding='utf8'))
    assert m == manifest(b)
    for row in m['proc_spells']:
        assert key_id[row['editor_id']] == row['local_id'], row
        # The override hits every effect: a proc spell may carry only the damage effect and the magnitude-less
        # engaged marker (lightning drain and the blood-rage bonus are separate casts since round 20).
        fx = effect_ids(by[row['editor_id']])
        assert len(fx) == 2 and fx[1] == b.ID_ENGAGED_EFFECT, (row['editor_id'], [hex(x) for x in fx])
    for group in ('spells', 'effects'):
        for name, row in m[group].items():
            assert key_id[row['editor_id']] == row['local_id'], (group, name, row)
    for name, row in m['spells'].items():
        fx = effect_ids(by[row['editor_id']])
        single = not name.startswith('kSilence')   # the soaked slows and the 寂滅 marker are single-effect
        assert (len(fx) == 1) if single else fx == [b.ID_SILENCE_EFFECT, b.util_effect_id(12)], (name, fx)
    for name, fid in m['globals'].items():
        assert key_id[name] == fid, name
    # Group B expectations must name the records the ESP really has.
    wiring = json.loads(WIRING.read_text(encoding='utf8'))
    trees = b.TREES
    for name, ids in wiring['main_perks'].items():
        t, r, k = wiring['slots'][name]
        assert [key_id[f'ESSB_P_{trees[t]}_{r}_{k}_M{i + 1}'] for i in range(len(ids))] == ids, name
    for name, fid in wiring['branch_perks'].items():
        t, r, k, n = wiring['slots'][name]
        assert key_id[f'ESSB_P_{trees[t]}_{r}_{k}_B{n + 1}'] == fid, name
    for cast, fid in wiring['spells'].items():
        assert m['spells'][cast]['local_id'] == fid
    for field, fid in wiring['globals']['tuning'].items():
        assert key_id[TUNING_GLOBALS[field]] == fid, field
    assert sha(dll) == sha(b.OUT / 'SKSE/Plugins/ElementsSpellblade.dll')
    test = NATIVE / 'out/Release/hit_pipeline_test.exe'
    result = subprocess.run([str(test), str(TABLE), str(WIRING)], text=True, capture_output=True)
    (ROOT / 'build/fix20-native-test.log').write_text(result.stdout + result.stderr, encoding='utf8')
    assert result.returncode == 0, result.stdout + result.stderr
    print(f'NATIVE ok: fresh DLL {NATIVE_VERSION} + exact dependencies + manifest/ESP identities (22 proc spells with one damage '
          f'effect each, {len(m["spells"])} cast spells, {len(m["effects"])} effects, {len(m["globals"])} globals, '
          f'{len(wiring["main_perks"])} main lines + {len(wiring["branch_perks"])} branches by EDID); '
          f'{len(ours)} PERK records scanned by PRKE type, 0 entry-point-51 entries')
    print(result.stdout.strip())
    return m
