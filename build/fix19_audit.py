"""Readback preservation against the round-18 release (pre-fix19 snapshot), native-only delivery,
and explicit acceptance boundaries. Manual evidence script: python -B build/fix19_audit.py (after the build).

Allowed differences from round 18, each checked exactly:
  - ESSB_P_HitProc emptied (round 19: the DLL delivers the base proc)
  - new GLOBs ESSB_NativeHit / ESSB_NativeWanted (round 19)
  - state schema 7 -> 8 (round 19b: ESSBController gained NativeHit/NativeWanted properties):
    both quests move to their schema-8 IDs, two schema-7 inert stubs appear, every VMAD that points
    at a quest now points at the new ID, and the main quest's VMAD gains exactly the two properties.
"""
from pathlib import Path
import json, sys, struct
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'build')]
import build_v03 as b
import fix19_native as n
import state_schema
OLD = ROOT / '.codex/pre-fix19-snapshot'
OLD_SCHEMA = 7

CONTROLLER_INSERTIONS = [
    '; ESSB_NativeHit (DLL status, 1 = native base proc running). Read as a GLOB, never by calling into the DLL,\r\n'
    '; so a missing DLL cannot cause unbound-native errors on the hit path.\r\n'
    'GlobalVariable Property NativeHit Auto\r\n'
    '; ESSB_NativeWanted (MCM preference for the DLL). Read once per load for the not-running notice.\r\n'
    'GlobalVariable Property NativeWanted Auto\r\n',
    '\t; No base delivery means no on-hit difference spell either. Status handling stays independent.\r\n'
    '\tIf NativeHit.GetValue() != 1.0\r\n\t\tReturn\r\n\tEndIf\r\n',
    '\tIf !NativeHit || !NativeWanted\r\n\t\tReturn False\r\n\tEndIf\r\n',
    '\t; A DLL that is missing or refuses to start (game/SKSE version, Address Library) cannot show anything\r\n'
    '\t; itself, so the script says so once per load. A running DLL reports its own faults and the MCM switch.\r\n'
    '\tIf Enabled.GetValueInt() == 1 && NativeWanted.GetValueInt() == 1 && NativeHit.GetValueInt() != 1\r\n'
    '\t\tDebug.Notification("元素魔戰士：DLL 命中附傷未運作（未安裝、遊戲／SKSE 版本或 Address Library 不符，或已故障）")\r\n'
    '\tEndIf\r\n',
]


def quest_id_map():
    """New full FormID bytes -> old full FormID bytes for both quests (plugin index 01)."""
    old = state_schema.quest_ids(OLD_SCHEMA)
    new = state_schema.quest_ids(b.STATE_SCHEMA_VERSION)
    return {struct.pack('<I', 0x01000000 | new[q]): struct.pack('<I', 0x01000000 | old[q]) for q in old}


def property_entry(vmad, name):
    """Bytes of one object property entry: wstring name, type 1, status 1, 8-byte object."""
    start = vmad.index(struct.pack('<H', len(name)) + name.encode())
    end = start + 2 + len(name) + 2 + 8
    assert vmad[start + 2 + len(name)] == 1, 'property must be an object'
    return vmad[start:end]


def check_records(before, after):
    mapping = quest_id_map()
    changed = []
    for name, old in before.items():
        new = after[name]
        if (old.flags, old.ss) == (new.flags, new.ss):
            continue
        changed.append(name)
        if name == 'ESSB_P_HitProc':
            assert new.ss == old.ss[:3], ('empty perk changed unrelated data', new.ss)
            continue
        assert old.flags == new.flags and [t for t, _ in old.ss] == [t for t, _ in new.ss], name
        for (tag, a), (_tag, z) in zip(old.ss, new.ss):
            if a == z:
                continue
            assert tag == 'VMAD', (name, tag)
            for new_id, old_id in mapping.items():
                z = z.replace(new_id, old_id)
            if name == 'ESSB_MainQuest':
                for prop in ('NativeHit', 'NativeWanted'):
                    z = z.replace(property_entry(z, prop), b'', 1)
                # The script's property count is the only other difference: exactly +2.
                diffs = [i for i in range(len(a)) if a[i] != z[i]] if len(a) == len(z) else None
                assert diffs and len(diffs) <= 2, (name, 'VMAD differs beyond the two properties')
                at = diffs[0]  # low byte of the little-endian count (high byte too only on a carry)
                assert struct.unpack_from('<H', z, at)[0] == struct.unpack_from('<H', a, at)[0] + 2, name
            else:
                assert z == a, (name, 'VMAD differs beyond the quest ID move')
    return changed


def run():
    a, am = b.read_plugin(OLD / 'package/Elements Spellblade' / b.PLUGIN)
    z, zm = b.read_plugin(b.OUT / b.PLUGIN)
    before = {r.edid: r for r in a}
    after = {r.edid: r for r in z}
    stubs = {f'{q}_Schema{OLD_SCHEMA}_Stub' for q in state_schema.QUESTS}
    assert set(after) - set(before) == n.NEW_EDIDS | stubs and not set(before) - set(after)
    changed = check_records(before, after)
    assert am['masters'] == zm['masters'] == ['Skyrim.esm']
    native = after['ESSB_NativeHit']
    assert native.flags & 0x40 and struct.unpack('<f', native.d['FLTV'])[0] == 0
    kept = []
    formats = {}
    for p in sorted((OLD / 'src').glob('*.psc')):
        oldraw = p.read_bytes()
        newraw = (ROOT / 'src' / p.name).read_bytes()
        assert oldraw.startswith(b'\xef\xbb\xbf') == newraw.startswith(b'\xef\xbb\xbf')
        assert b'\r\n' not in oldraw or b'\n' not in newraw.replace(b'\r\n', b''), p.name
        formats[p.name] = {'bom': newraw.startswith(b'\xef\xbb\xbf'), 'crlf': newraw.count(b'\r\n'),
                           'bare_lf': newraw.replace(b'\r\n', b'').count(b'\n')}
        if p.name == 'ESSBState.psc':  # generated; carries the main quest ID, which moved with the schema
            old_id = f"0x{state_schema.quest_ids(OLD_SCHEMA)['ESSB_MainQuest']:06X}".encode()
            new_id = f"0x{state_schema.quest_ids(b.STATE_SCHEMA_VERSION)['ESSB_MainQuest']:06X}".encode()
            assert newraw.replace(new_id, old_id) == oldraw, 'ESSBState changed beyond the quest ID'
        elif p.name not in ['ESSBController.psc', 'ESSBMCM.psc']:
            assert oldraw == newraw, ('unexpected Papyrus change', p.name)
            kept.append(p.name)
    controller = (ROOT / 'src/ESSBController.psc').read_bytes()
    assert b'ESSBNative.' not in controller, 'the hit path must not call into the DLL'
    stripped = controller
    for block in CONTROLLER_INSERTIONS:
        block = block.encode('utf8')
        assert stripped.count(block) == 1, block[:70]
        stripped = stripped.replace(block, b'')
    assert stripped == (OLD / 'src/ESSBController.psc').read_bytes(), 'Controller changed beyond the listed insertions'
    assert b'\n' not in (ROOT / 'build_v03.py').read_bytes().replace(b'\r\n', b'')
    fmold = json.loads((OLD / 'build/v03-formids.json').read_text(encoding='utf8'))['records']
    fmnew = json.loads((ROOT / 'build/v03-formids.json').read_text(encoding='utf8'))['records']
    diff = {'added': {k: v for k, v in fmnew.items() if k not in fmold}, 'removed': [k for k in fmold if k not in fmnew],
            'changed': {k: [v, fmnew.get(k)] for k, v in fmold.items() if fmnew.get(k) != v}}
    assert not diff['removed'] and set(diff['changed']) == set(state_schema.QUESTS), diff['changed']
    (ROOT / 'build/fix19-formid-diff.json').write_text(json.dumps(diff, indent=2, ensure_ascii=False), encoding='utf8')
    # The actual Papyrus ApplyProc with the DLL status GLOB at 0 casts no difference spell.
    import fix18_verify as v
    f = v.fixture()
    f.c.fields['NativeHit'].v = 0
    f.c.overrides['TargetProcPossible'] = lambda *args: True
    f.c.ApplyProc(f.v, 1, False, False, False)
    assert not f.apps, 'native OFF still applies difference damage'
    n.verify(b)
    report = {'records': len(z), 'unchanged_existing_records': len(a) - len(changed), 'changed_records': changed,
              'new_records': diff['added'], 'unchanged_papyrus': kept, 'formats': formats,
              'controller_insertions': len(CONTROLLER_INSERTIONS), 'disabled_difference_casts': len(f.apps),
              'runtime_tested': False, 'deployed': False,
              'dll_sha256': n.sha(b.OUT / 'SKSE/Plugins/ElementsSpellblade.dll'), 'esp_sha256': n.sha(b.OUT / b.PLUGIN)}
    (ROOT / 'build/fix19-audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
    print(f'FIX19 PRESERVATION ok: {len(a) - len(changed)} existing records byte-identical; {len(changed)} changed '
          '(hit perk emptied, quests moved to schema 8, main quest +2 properties); Controller = round 18 + 4 listed insertions; '
          'native OFF => zero difference casts')
    return report


if __name__ == '__main__':
    run()
