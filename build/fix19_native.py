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
import fix22_records as hit22
import fix23_records as hit23
import fix24_records as hit24
import fix20_fixture
import fix22_fixture
import fix23_fixture
import fix24_fixture
import fix20_reference as _ref
import fix22_reference as _ref22
import fix23_reference as _ref23
import fix24_reference as _ref24
NATIVE = ROOT / 'native'
NATIVE_VERSION = '0.24.0'
NATIVE_HIT = 0x52d1
NATIVE_WANTED = 0x52d2
NATIVE_GLOBALS = {'ESSB_NativeHit', 'ESSB_NativeWanted'}      # round 19: the MCM shows both
NEW_EDIDS = (NATIVE_GLOBALS | hit20.new_edids() | hit21.new_edids() | hit22.new_edids() | hit23.new_edids() |
             hit24.new_edids())   # every record the native slices added
DEPS = {
    'CommonLibSSE-NG': ('https://github.com/CharmedBaryon/CommonLibSSE-NG', 'b93280e832f263dbef44e44cbe2936622a02f91a'),
    'spdlog': ('https://github.com/gabime/spdlog', '27cb4c76708608465c413f6d0e6b8d99a4d84302'),
    'rapidcsv': ('https://github.com/d99kris/rapidcsv', 'a98b85e663114b8fdc9c0dc03abf22c296f38241'),
    'json': ('https://github.com/nlohmann/json', '9cca280a4d0ccf0c08f47a99aa71d1b0e52f8d03'),
}
HEADER = NATIVE / 'include/ManifestData.h'
TABLE = ROOT / fix20_fixture.TABLE
WIRING = ROOT / fix20_fixture.WIRING
STATUS_TABLE = ROOT / fix22_fixture.TABLE
STATUS_WIRING = ROOT / fix22_fixture.WIRING
SELF_TABLE = ROOT / fix23_fixture.TABLE
SELF_WIRING = ROOT / fix23_fixture.WIRING
BODY_TABLE = ROOT / fix24_fixture.TABLE
BODY_WIRING = ROOT / fix24_fixture.WIRING
ENTRY_POINT = 2  # PRKE effect type: 0 quest stage, 1 ability, 2 entry point
ENTRY_51 = 51    # Apply Combat Hit Spell

# Every node:: constant the DLL reads -> (tree id, v0.4 node name): the hit formulas' (build/fix20_reference.NODE_NAMES)
# and, from round 22, the status layer's (build/fix22_reference.NODE_NAMES); the slot of each is looked up by name in
# the identity table.
NODE_IDENTITY = (dict(_ref.NODE_NAMES) | dict(_ref22.NODE_NAMES) | dict(_ref23.NODE_NAMES) |   # round 23 (N4): the self layer's
                 dict(_ref24.NODE_NAMES))                                                          # round 24 (N5): the bodies'
assert len(NODE_IDENTITY) == len(_ref.NODE_NAMES) + len(_ref22.NODE_NAMES) + len(_ref23.NODE_NAMES) + len(_ref24.NODE_NAMES), \
    'a node constant is named twice'
ELEMENT_SHORT = ['火', '冰', '雷', '土', '風', '血', '聖', '毒', '水', '暗', '星']
TREE_IDS = ['fire', 'frost', 'lightning', 'earth', 'wind', 'blood', 'divine', 'poison', 'water', 'darkness', 'astral']


def _array_identity():
    """Every per-element node table the DLL indexes (node::kX[element]) -> [element] (tree id, v0.4 name) or None,
    by the same labels node_table / skeleton_tables check against the plan (build/fix21_identity.py registers the
    reads it finds in the C++ sources through this)."""
    import fix20_reference as ref
    out = {
        'kProcAdept': [None] + [(TREE_IDS[e - 1], f'{ELEMENT_SHORT[e - 1]}附傷') if ref.adept(e) else None
                                for e in range(1, 12)],
        'kProcMaster': [None] + [(TREE_IDS[e - 1], f'同調每段{ELEMENT_SHORT[e - 1]}附傷') if ref.master(e) else None
                                 for e in range(1, 12)],
    }
    for name, (_route, _level, pattern, without) in _ref22.SKELETON.items():
        out[name] = [None] + [None if TREE_IDS[e - 1] in without else
                              (TREE_IDS[e - 1], pattern.format(x=ELEMENT_SHORT[e - 1])) for e in range(1, 12)]
    out['kSignature'] = [None] + [(tree, _ref22.SIGNATURE[tree]) for tree in TREE_IDS]
    out['kSustainLegend'] = [None] + [(tree, _ref23.SUSTAIN_LEGEND[tree]) for tree in TREE_IDS]   # round 23 化身
    for name, (_route, _level, pattern, without) in _ref24.SKELETON.items():   # round 24: the burst lines
        out[name] = [None] + [None if TREE_IDS[e - 1] in without else
                              (TREE_IDS[e - 1], pattern.format(x=ELEMENT_SHORT[e - 1])) for e in range(1, 12)]
    for name, (_route, _level, labels) in _ref24.LABELED.items():   # round 24: the X臨 main lines
        out[name] = [None] + [(tree, labels[tree]) for tree in TREE_IDS]
    return out


ARRAY_IDENTITY = _array_identity()


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


def _plan(b):
    # parse + balance text without plan_trees.build(): build() rewrites build/plan-tree-nodes.json, and this runs
    # after main() has written the decided plan there.
    return b.apply_fix8_decisions(b.plan_trees.apply_balance_text(b.plan_trees.parse()))


def node_table(b):
    """{constant: slot} for every node the DLL reads, looked up by v0.4 name in the identity table; the element
    skeleton tables (kProcAdept / kProcMaster, and round 22's per-element lines) are checked by name too."""
    import fix20_reference as ref
    plan = _plan(b)
    trees = {t['index']: t for t in plan['trees']}
    by_name = {}
    for tree in plan['trees']:
        for route in tree['routes']:
            for cell in route['tiers']:
                by_name[(tree['id'], cell['main_label'])] = (tree['index'], route['index'], cell['index'])
                for branch in cell['branches']:
                    by_name[(tree['id'], branch['name'])] = (tree['index'], route['index'], cell['index'], branch['slot'])

    def tier(tree, route, level):
        return trees[tree]['routes'][route]['tiers'][level]

    missing = {k: v for k, v in NODE_IDENTITY.items() if v not in by_name}
    assert not missing, f'DLL nodes not in the v0.4 identity table: {missing}'
    table = {name: by_name[key] for name, key in NODE_IDENTITY.items()}
    for name, slot in ref.NODES.items():   # the round-20 reference resolves the same slots on its own
        assert table[name] == slot, (name, slot, table[name])
    for element in range(1, 12):
        short = ELEMENT_SHORT[element - 1]
        adept, master = ref.adept(element), ref.master(element)
        if adept is None:
            assert element == ref.WATER and tier(element - 1, 0, 1)['main_label'] != f'{short}附傷'                 and tier(element - 1, 0, 3)['main_label'] != f'同調每段{short}附傷'
            continue
        assert tier(*adept)['main_label'] == f'{short}附傷', (element, tier(*adept)['main_label'])
        assert tier(*master)['main_label'] == f'同調每段{short}附傷', (element, tier(*master)['main_label'])
    return table


def skeleton_tables(b):
    """Round 22: the per-element main lines the status layer reads, [element] -> slot or None, each checked by its
    v0.4 label in that element's own tree (a tree whose table has another line there gets None)."""
    plan = _plan(b)
    trees = {t['index']: t for t in plan['trees']}
    out = {}
    for name, (route, level, pattern, without) in _ref22.SKELETON.items():
        cells = [None]
        for element in range(1, 12):
            tree = trees[element - 1]
            label = pattern.format(x=ELEMENT_SHORT[element - 1])
            cell = tree['routes'][route]['tiers'][level]
            if tree['id'] in without:
                assert cell['main_label'] != label, (name, tree['id'], cell['main_label'])
                cells.append(None)
                continue
            assert cell['main_label'] == label, (name, tree['id'], cell['main_label'], label)
            cells.append((element - 1, route, level))
        out[name] = cells
    cells = [None]
    for element in range(1, 12):
        tree = trees[element - 1]
        cell = tree['routes'][2]['tiers'][4]
        assert cell['main_label'] == _ref22.SIGNATURE[tree['id']], (tree['id'], cell['main_label'])
        cells.append((element - 1, 2, 4))
    out['kSignature'] = cells
    cells = [None]   # round 23: 化身's 持續傳奇主線 of each element, checked by its v0.4 label
    for element in range(1, 12):
        tree = trees[element - 1]
        cell = tree['routes'][0]['tiers'][4]
        assert cell['main_label'] == _ref23.SUSTAIN_LEGEND[tree['id']], (tree['id'], cell['main_label'])
        cells.append((element - 1, 0, 4))
    out['kSustainLegend'] = cells
    for name, (route, level, pattern, without) in _ref24.SKELETON.items():   # round 24 (N5)
        cells = [None]
        for element in range(1, 12):
            tree = trees[element - 1]
            label = pattern.format(x=ELEMENT_SHORT[element - 1])
            cell = tree['routes'][route]['tiers'][level]
            if tree['id'] in without:
                assert cell['main_label'] != label, (name, tree['id'], cell['main_label'])
                cells.append(None)
                continue
            assert cell['main_label'] == label, (name, tree['id'], cell['main_label'], label)
            cells.append((element - 1, route, level))
        out[name] = cells
    for name, (route, level, labels) in _ref24.LABELED.items():   # round 24 (N5): X臨 (earth 地臨)
        cells = [None]
        for element in range(1, 12):
            tree = trees[element - 1]
            cell = tree['routes'][route]['tiers'][level]
            assert cell['main_label'] == labels[tree['id']], (name, tree['id'], cell['main_label'])
            cells.append((element - 1, route, level))
        out[name] = cells
    return out


def globals_(b):
    """Every GLOB the DLL reads, by editor ID."""
    ids = {k: b.ID_GLOB[k] for k in ['ESSB_Enabled', 'ESSB_FormActive', 'ESSB_CurrentElement', 'ESSB_DebugLevel']}
    ids |= {'ESSB_NativeHit': NATIVE_HIT, 'ESSB_NativeWanted': NATIVE_WANTED}
    for name in ['ESSB_BaseDamageMult', 'ESSB_NodeScale', 'ESSB_MultDrain', 'ESSB_MultRecovery', 'ESSB_MultDuration',
                 'ESSB_SlowCapPct', 'ESSB_WaterWetSlowPct', 'ESSB_WaterClearStamina', 'ESSB_ManabreakMaxmagPct',
                 'ESSB_MultCooldown', 'ESSB_MultDot', 'ESSB_PoisonDotK', 'ESSB_BleedDotK',
                 'ESSB_FrostOpenSlowPct', 'ESSB_WaterOpenStamina']:   # round 24: the open bodies' two tunables
        ids[name] = b.ID_BALANCE_GLOB[name][0]
    mech = [name for name, _ in b.MECH_GLOBALS]
    for name in ['ESSB_SyncStage', 'ESSB_PrevElement', 'ESSB_TwinElement']:
        ids[name] = b.ID_MECH_GLOB + mech.index(name)
    # Round 23 (N4): the mirrors the DLL writes from your resources (v0.4 2.3: PERK conditions read GLOBs).
    ids['ESSB_Sync'] = b.ID_GLOB['ESSB_Sync']
    for name in ['ESSB_Resolve', 'ESSB_Charge', 'ESSB_IceShield']:
        ids[name] = b.ID_MECH_GLOB + mech.index(name)
    mech2 = [name for name, _ in b.MECH2_GLOBALS]
    for name in ['ESSB_RockArmor', 'ESSB_Wind']:
        ids[name] = b.ID_MECH2_GLOB + mech2.index(name)
    for name, _default in hit23.GLOBALS:
        ids[name] = hit23.global_id(name)
    for name in ['ESSB_EnvWet', 'ESSB_EnvNight', 'ESSB_EnvStormy', 'ESSB_SyncT1', 'ESSB_SyncT2', 'ESSB_SyncT3']:
        ids[name] = b.ID_GLOB_ENGINE[name]   # round 23 review: the sync thresholds too (one source with Papyrus)
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
    'multCooldown': 'ESSB_MultCooldown', 'envStormy': 'ESSB_EnvStormy',
    'multDot': 'ESSB_MultDot', 'poisonDotK': 'ESSB_PoisonDotK', 'bleedDotK': 'ESSB_BleedDotK',
    'syncT1': 'ESSB_SyncT1', 'syncT2': 'ESSB_SyncT2', 'syncT3': 'ESSB_SyncT3',
    'frostOpenSlowPct': 'ESSB_FrostOpenSlowPct', 'waterOpenStamina': 'ESSB_WaterOpenStamina',   # round 24 (N5)
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
        'kBleedTick': (b.util_spell_id(7), 'ESSB_Util_BleedTick'),   # round 22 放血: no resist, no G(L)
        'kTrueDamage': (b.ID_TRUE_SPELL, 'ESSB_TrueDamageSpell'),
        'kDispelMark': (b.ID_MANABREAK_SPELL, 'ESSB_ManaBreakSpell'),
        'kSpendMagicka': (hit20.SPEND, 'ESSB_Native_SpendMagicka'),
        'kBloodGuard': (hit20.GUARD, 'ESSB_BloodGuard'),
        'kHushSpent': (hit21.HUSH_SPENT, 'ESSB_HushSpent'),
        'kRiposte': (hit21.RIPOSTE, 'ESSB_RiposteWindow'),   # round 23: 反擊's window, cast by the DLL on a block
        'kHush': (hit21.HUSH, 'ESSB_Hush'),                  # round 24: 寂 (冷寂 at 融斷, 萬寂)
        'kHealTarget': (0x005151, 'ESSB_UtilTarget_RestoreHealth'),   # round 24: 聖光 heals an ally
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
        'kManaBreak': (b.ID_MANABREAK_EFFECT, 'ESSB_ManaBreakEffect'),   # round 23: 反咒 reads it on a caster
        'kEngaged': (b.ID_ENGAGED_EFFECT, 'ESSB_EngagedEffect'),     # round 24: 2.9 你主動攻擊過的目標（30 秒）
        'kReanimate': (b.ID_REANIMATE_EFFECT, 'ESSB_ReanimateEffect'),   # round 24: your raised servant (亡衛)
    }
    return {k: dict(local_id=v[0], editor_id=v[1]) for k, v in rows.items()}


def vanilla(b):
    """Skyrim.esm forms the target facts read (the same ones ESSBController's properties point at)."""
    return {
        'kUndeadKeyword': dict(form_id=b.FID_KW_UNDEAD, kind='KYWD'),
        'kDaedraKeyword': dict(form_id=b.FID_KW_DAEDRA, kind='KYWD'),
        'kArmorSpellKeyword': dict(form_id=b.FID_KW_ARMOR_SPELL, kind='KYWD'),
        'kCloakKeyword': dict(form_id=b.FID_KW_CLOAK, kind='KYWD'),
        'kDragonKeyword': dict(form_id=b.FID_KW_DRAGON, kind='KYWD'),   # round 24: never knocked, raised or turned to ash
        'kNecroClass': dict(form_id=b.FID_CLASS_NECRO, kind='CLAS'),
        'kNecroFaction': dict(form_id=b.FID_FACT_NECRO, kind='FACT'),
        # round 23: the spell half of the pool PERKs is bound to these keywords (v0.4 5.11), so the hurt path counts a
        # spell as shared only when it carries one of them
        'kDamageFireKeyword': dict(form_id=b.FID_KW_DAMAGE_FIRE, kind='KYWD'),
        'kDamageFrostKeyword': dict(form_id=b.FID_KW_DAMAGE_FROST, kind='KYWD'),
        'kDamageShockKeyword': dict(form_id=b.FID_KW_DAMAGE_SHOCK, kind='KYWD'),
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
    for label, cells in skeleton_tables(b).items():
        text = ', '.join('kNoNode' if c is None else _slot(c) for c in cells)
        L.append(f'inline constexpr NodeId {label}[12] = {{{text}}};  // [element]; round 22, checked by v0.4 label')
    L += ['}  // namespace node', '']
    L += status_header(b)
    L += ['',
          '// settings.json element_damage (B_min, B_max per element; [0] unused) and noform_base_true.',
          'inline constexpr float kElementDamage[12][2] = {{0.0f, 0.0f}, '
          + ', '.join('{' + ', '.join(f'{float(x)}f' for x in s['element_damage'][n]) + '}' for n in b.ELEMENTS) + '};',
          f'inline constexpr float kNoFormBaseTrue = {float(s["noform_base_true"])}f;',
          'inline constexpr std::string_view elementNames[12] = {"無元素", ' + ', '.join(f'"{z}"' for z in b.ZH) + '};',
          f'inline constexpr char nativeVersion[] = "{NATIVE_VERSION}";',
          f'inline constexpr char addressHash[] = "{sha(address_library())}";',
          '}  // namespace essb']
    return '\n'.join(L) + '\n'


MARK_RECORD_SECONDS = 8   # build_v03 ESSB_MarkSpell_<X> (the DLL checks it against the loaded record)


def status_ids(b):
    """Round 22: every record the status layer casts or looks for, by role."""
    return {
        'marks': [dict(effect=b.ID_MARK_EFFECT + i, spell=b.ID_MARK_SPELL + i, editor_id=f'ESSB_MarkSpell_{n}')
                  for i, n in enumerate(b.ELEMENTS)],
        'react': [dict(spell=b.ID_REACT_SPELL + i, editor_id=f'ESSB_React_{n}') for i, n in enumerate(b.ELEMENTS)],
        'kinds': [dict(kind=k[0], effect=hit22.effect_id(k[0]), spell=hit22.spell_id(k[0]), seconds=k[4], player=k[3],
                       stub=k[5], editor_id=hit22.edid_spell(k[1])) for k in hit22.KINDS] +
                 # round 23 (N4): your resources, windows and cooldowns (build/fix23_records.py), after round 22's
                 [dict(kind=k[0], effect=hit23.effect_id(k[0]), spell=hit23.spell_id(k[0]), seconds=k[4], player=k[3],
                       stub=False, editor_id=hit23.edid_spell(k[1])) for k in hit23.KINDS] +
                 # round 24 (N5): the death markers, windows, cooldowns and 血承 (build/fix24_records.py)
                 [dict(kind=k[0], effect=hit24.effect_id(k[0]), spell=hit24.spell_id(k[0]), seconds=k[4], player=k[3],
                       stub=False, editor_id=hit24.edid_spell(k[1])) for k in hit24.KINDS],
        'timed': [dict(name=name, util=util, self=util in hit24.SELF_UTILS,
                       spells=[hit24.timed_id(name, s) for s in range(1, hit24.TIMED_MAX_SECONDS + 1)],
                       editor_ids=[hit24.timed_edid(name, s) for s in range(1, hit24.TIMED_MAX_SECONDS + 1)])
                  for util, name in hit24.TIMED],
        'dots': {key: dict(effect=hit22.dot_effect_id(key),
                           spells=[hit22.dot_spell_id(key, s) for s in range(1, hit22.DOT_MAX_SECONDS + 1)],
                           editor_id=hit22.edid_effect(suffix))
                 for key, suffix, *_ in hit22.DOT_KINDS},
        'fear': dict(effect=b.ID_FEAR_EFFECT, editor_id='ESSB_FearEffect'),
        'frenzy': dict(effect=b.ID_FRENZY_EFFECT, editor_id='ESSB_FrenzyEffect'),
        'slow': dict(effect=b.util_effect_id(0), editor_id='ESSB_UtilEffect_Slow'),
    }


def status_header(b):
    ids = status_ids(b)
    L = ['// Round 22 (slice N3): the status layer records (build/fix22_records.py KINDS, in this order), then round 23 (N4)',
         '// build/fix23_records.py KINDS.',
         'enum class StatusKind : std::uint8_t', '{']
    L += [f'    {row["kind"]},' for row in ids['kinds']]
    L += ['    kCount,', '};', '',
          'struct StatusRecord { std::uint32_t effect; std::uint32_t spell; float seconds; bool onPlayer; bool stub; std::string_view editorId; };',
          'inline constexpr StatusRecord kStatusRecords[] = {']
    for row in ids['kinds']:
        L.append(f'    {{{hex(row["effect"])}, {hex(row["spell"])}, {float(row["seconds"])}f, {str(row["player"]).lower()}, '
                 f'{str(row["stub"]).lower()}, "{row["editor_id"]}"}},')
    L += ['};', '', 'namespace status {']
    L.append('inline constexpr std::uint32_t kMarkEffect[12] = {0, ' + ', '.join(hex(m['effect']) for m in ids['marks']) + '};  // ESSB_MarkEffect_<X>')
    L.append('inline constexpr std::uint32_t kMarkSpell[12] = {0, ' + ', '.join(hex(m['spell']) for m in ids['marks']) + '};  // ESSB_MarkSpell_<X>')
    L.append('inline constexpr std::uint32_t kReactSpell[12] = {0, ' + ', '.join(hex(m['spell']) for m in ids['react']) + '};  // ESSB_React_<X>')
    L.append(f'inline constexpr int kDotMaxSeconds = {hit22.DOT_MAX_SECONDS};')
    for key, row in ids['dots'].items():
        cap = key[0].upper() + key[1:]
        L.append(f'inline constexpr std::uint32_t k{cap}DotEffect = {hex(row["effect"])};  // {row["editor_id"]}')
        L.append(f'inline constexpr std::uint32_t k{cap}Dot[{hit22.DOT_MAX_SECONDS}] = {{' + ', '.join(hex(x) for x in row['spells']) + '};  // 1..N s')
    L.append(f'inline constexpr float kMarkRecordSeconds = {float(MARK_RECORD_SECONDS)}f;  // ESSB_MarkSpell_<X> EFIT duration')
    for name in ('fear', 'frenzy', 'slow'):
        L.append(f'inline constexpr std::uint32_t k{name.capitalize()}Effect = {hex(ids[name]["effect"])};  // {ids[name]["editor_id"]}')
    timed = ids['timed']
    L.append(f'inline constexpr std::uint32_t kTimed[{len(timed)}][{hit24.TIMED_MAX_SECONDS}] = {{')
    for row in timed:
        L.append('    {' + ', '.join(hex(x) for x in row['spells']) + f'}},  // {row["name"]}: ESSB_N5_Timed<X>_1..{hit24.TIMED_MAX_SECONDS}')
    L.append('};')
    L += ['}  // namespace status', '',
          '// Round 24 (N5): the timed utilities a reaction body casts (build/fix24_records.py TIMED): Op::kTimed element.',
          f'inline constexpr int kTimedKinds = {len(timed)};',
          f'inline constexpr int kTimedMaxSeconds = {hit24.TIMED_MAX_SECONDS};',
          'namespace timed {']
    for i, row in enumerate(timed):
        L.append(f'inline constexpr int {row["name"]} = {i};  // ESSB_UtilEffect #{row["util"]}')
    L += ['}  // namespace timed',
          'inline constexpr bool kTimedOnPlayer[' + str(len(timed)) + '] = {' + ', '.join('true' if r['self'] else 'false' for r in timed) + '};']
    return L


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
    # Round 22: the status layer's scenario table (reference model) and record wiring.
    count += fix22_fixture.write(b, settings(), write_if_changed, ROOT)
    fix22_fixture.wiring(b, write_if_changed, ROOT)
    # Round 23 (N4): the self layer's and the hurt path's scenarios (reference model) and record wiring.
    count += fix23_fixture.write(b, settings(), write_if_changed, ROOT)
    fix23_fixture.wiring(b, globals_(b), write_if_changed, ROOT)
    # Round 24 (N5): the reaction bodies', the burst's and the death handling's scenarios (reference model) and wiring.
    count += fix24_fixture.write(b, settings(), write_if_changed, ROOT)
    fix24_fixture.wiring(b, globals_(b), write_if_changed, ROOT)
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
             ROOT / 'build/fix22_records.py', ROOT / 'build/fix20_reference.py', ROOT / 'build/fix22_reference.py',
             ROOT / 'build/fix20_fixture.py', TABLE, WIRING, ROOT / 'build/fix22_fixture.py', STATUS_TABLE, STATUS_WIRING,
             ROOT / 'build/fix23_records.py', ROOT / 'build/fix23_reference.py', ROOT / 'build/fix23_fixture.py', SELF_TABLE,
             SELF_WIRING,
             ROOT / 'build/fix24_records.py', ROOT / 'build/fix24_reference.py', ROOT / 'build/fix24_fixture.py', BODY_TABLE,
             BODY_WIRING,
             NATIVE / 'build.py', NATIVE / 'CMakeLists.txt',
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
            'spells': spells(b), 'effects': effects(b), 'vanilla': vanilla(b), 'status': status_ids(b),
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
    status = subprocess.run([str(NATIVE / 'out/Release/status_test.exe'), str(STATUS_TABLE), str(STATUS_WIRING)],
                            text=True, capture_output=True)
    (ROOT / 'build/fix22-native-test.log').write_text(status.stdout + status.stderr, encoding='utf8')
    assert status.returncode == 0, status.stdout + status.stderr
    own = subprocess.run([str(NATIVE / 'out/Release/self_test.exe'), str(SELF_TABLE), str(SELF_WIRING)], text=True, capture_output=True,
                         encoding='utf-8', errors='replace')   # its lines carry the v0.4 names (UTF-8)
    (ROOT / 'build/fix23-native-test.log').write_text(own.stdout + own.stderr, encoding='utf8')
    assert own.returncode == 0, own.stdout + own.stderr
    body = subprocess.run([str(NATIVE / 'out/Release/reaction_test.exe'), str(BODY_TABLE), str(BODY_WIRING)], text=True,
                          capture_output=True, encoding='utf-8', errors='replace')
    (ROOT / 'build/fix24-native-test.log').write_text(body.stdout + body.stderr, encoding='utf8')
    assert body.returncode == 0, body.stdout + body.stderr
    print(f'NATIVE ok: fresh DLL {NATIVE_VERSION} + exact dependencies + manifest/ESP identities (22 proc spells with one damage '
          f'effect each, {len(m["spells"])} cast spells, {len(m["effects"])} effects, {len(m["globals"])} globals, '
          f'{len(wiring["main_perks"])} main lines + {len(wiring["branch_perks"])} branches by EDID); '
          f'{len(ours)} PERK records scanned by PRKE type, 0 entry-point-51 entries')
    print(result.stdout.strip())
    print(status.stdout.strip())
    print(own.stdout.strip())
    print(body.stdout.strip())
    return m
