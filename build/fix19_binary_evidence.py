"""Read-only PE evidence for native-verification.md; never loads or writes the game executable.

Reproduce: python -B build/fix19_binary_evidence.py  (needs llvm-objdump on PATH).
Writes build/fix19-binary-evidence.txt: the DoCombatSpellApply registration site plus the
full disassembly of every function the CastSpellImmediate / DoCombatSpellApply comparison cites.
"""
import hashlib, struct, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
GAME = Path('D:/Game/Other/SKSE/SkyrimSE/SkyrimSE.exe')

# (address, role) - every function cited in native-verification.md "CastSpellImmediate vs DoCombatSpellApply".
FUNCTIONS = [
    (0x1409582C0, 'Papyrus Actor.DoCombatSpellApply native thunk (registered with the string below)'),
    (0x1406282E0, 'DoCombatSpellApply body: disease resist roll, GetMagicCaster(3) (vfunc 0x2E0), call 0x14054CBE0'),
    (0x14054CBE0, 'MagicCaster cast-with-target wrapper used by DoCombat; SpellType gate 0x1401007F0 decides the path'),
    (0x1401007F0, 'SpellType predicate: vfunc 0x298 = MagicItem::GetSpellType (index 0x53); true for types in mask 0x412 = {1 Disease, 4 Ability, 10 Addiction}'),
    (0x140552E80, 'MagicTarget has-active-effect-from-spell visitor (vfunc 0x38 = GetActiveEffectList); only reached for mask-0x412 types'),
    (0x14054C950, 'DoCombat path for all other SpellTypes (our SpellType 0): CheckCast (vfunc 0x50) then 0x14054CD10'),
    (0x14054C5F0, 'ActorMagicCaster vtable slot 1 = MagicCaster::CastSpellImmediate: no CheckCast, no same-spell gate, calls 0x14054CD10'),
    (0x14054CD10, 'shared target-finding / apply core reached by both paths; effectiveness (xmm1) saved in xmm7, stored at visitor+0x30'),
    (0x140551980, 'apply visitor (vtable 0x141639878 slot 1): magnitude override caster+0x3C, then AdjustActiveEffect(effect, visitor+0x30 = effectiveness)'),
    (0x140543D70, 'ActorMagicCaster vtable slot 0x1C AdjustActiveEffect -> 0x140550CD0'),
    (0x140550CD0, 'MagicCaster::AdjustActiveEffect -> 0x14053DEB0'),
    (0x14053DEB0, 'skips SpellType mask 0x512 {1,4,8,10}; else 0x140540360(effect, power)'),
    (0x140540360, 'power == 1.0 (constant 0x1415232D8) or < 0: unchanged; otherwise magnitude = max(|magnitude| * power, 1.0) * sign. Effectiveness 0.0 therefore sets magnitude to 1.0'),
]

raw = GAME.read_bytes()
pe = struct.unpack_from('<I', raw, 0x3c)[0]
count, optsize = struct.unpack_from('<H', raw, pe + 6)[0], struct.unpack_from('<H', raw, pe + 20)[0]
base = struct.unpack_from('<Q', raw, pe + 24 + 24)[0]
sections = []
for i in range(count):
    o = pe + 24 + optsize + 40 * i
    name = raw[o:o + 8].rstrip(b'\0').decode()
    _vsize, rva, size, off = struct.unpack_from('<IIII', raw, o + 8)
    sections.append((name, rva, size, off))


def va(file_offset):
    for _name, rva, size, start in sections:
        if start <= file_offset < start + size:
            return base + rva + file_offset - start
    raise ValueError(file_offset)


def offset(address):
    for _name, rva, size, start in sections:
        if base + rva <= address < base + rva + size:
            return start + address - base - rva
    raise ValueError(hex(address))


def disasm(address, length):
    return subprocess.check_output(['llvm-objdump', '-d', '--x86-asm-syntax=intel',
                                    f'--start-address={address}', f'--stop-address={address + length}',
                                    str(GAME)], text=True)


def function(address):
    """Disassemble until the int3 padding after an unconditional ret/jmp (MSVC function padding)."""
    text = disasm(address, 0x600)
    lines = [l for l in text.splitlines() if l[:1].isdigit() or l.startswith(' ') and ':' in l]
    body = []
    for line in lines:
        fields = body[-1].split('	') if body else []
        last = fields[1] if len(fields) > 1 else ''  # mnemonic column
        if 'int3' in line and (last.startswith('ret') or last.startswith('jmp')):
            break
        body.append(line)
    return '\n'.join(body)


def registration(string):
    target = va(raw.index(string))
    out = [f'{string!r} string at {target:X}']
    for name, rva, size, start in sections:
        if name != '.text':
            continue
        for i in range(start, start + size - 7):
            if raw[i] in (0x48, 0x4c) and raw[i + 1] == 0x8d and raw[i + 2] & 0xc7 == 5:
                if va(i) + 7 + struct.unpack_from('<i', raw, i + 3)[0] == target:
                    out.append(disasm(va(i) - 40, 160))
    return out


def proc_spell_types():
    sys.path[:0] = [str(ROOT), str(ROOT / 'build')]
    import build_v03 as b
    records, _ = b.read_plugin(b.OUT / b.PLUGIN)
    types = {}
    for r in records:
        if r.sig == 'SPEL' and r.edid.startswith('ESSB_Hit_'):
            types[r.edid] = struct.unpack_from('<I', r.d['SPIT'], 8)[0]
    return types


if __name__ == '__main__':
    out = [f'SkyrimSE.exe sha256={hashlib.sha256(raw).hexdigest()} image base={base:X}',
           'Tool: llvm-objdump (Intel syntax). Addresses are 1.5.97 VAs, evidence only; the DLL calls none of them directly.', '']
    out += registration(b'DoCombatSpellApply\0')
    # VTABLE_ActorMagicCaster[0]: CommonLib-NG RELOCATION_ID(257613, ...) -> 1.5.97 VA 0x141637490 (Address Library).
    vtable = 0x141637490
    slot1 = struct.unpack_from('<Q', raw, offset(vtable + 8))[0]
    out += ['', f'ActorMagicCaster vtable {vtable:X} slot 1 (CastSpellImmediate, MagicCaster.h index 01) = {slot1:X}']
    assert slot1 == 0x14054C5F0, hex(slot1)
    slot1c = struct.unpack_from('<Q', raw, offset(vtable + 0x1C * 8))[0]
    one = struct.unpack_from('<f', raw, offset(0x1415232D8))[0]
    out += [f'ActorMagicCaster vtable slot 0x1C (AdjustActiveEffect) = {slot1c:X}; float at 1415232D8 = {one}',
            'DoCombat SpellType-0 path (0x14054C950) passes effectiveness = that 1.0 constant (via CheckCast) to 0x14054CD10.']
    assert slot1c == 0x140543D70 and one == 1.0
    for address, role in FUNCTIONS:
        out += ['', f'=== {address:X}: {role}', function(address)]
    types = proc_spell_types()
    out += ['', f'=== Released proc spells (ESSB_Hit_*): {len(types)} SPEL, SPIT spell types {sorted(set(types.values()))}',
            '0 = MagicSystem::SpellType::kSpell; not in mask 0x412, so DoCombat would take 0x14054C950, not the 0x140552E80 gate.']
    (ROOT / 'build/fix19-binary-evidence.txt').write_text('\n'.join(out) + '\n', encoding='utf8')
    print(f'BINARY EVIDENCE ok: {len(FUNCTIONS)} functions; proc spell types {sorted(set(types.values()))}')
