"""Round 27h / 28 (DLL 0.28.0) records.

  ESSB_PapyrusReady                the Papyrus half is set up (ESSBController.Setup sets 1 at its end; the DLL writes 0 at
                                   kPreLoadGame / kNewGame and holds form switches -- one pending -- until it reads 1).
                                   Review 2 (Papyrus layer): after a load Setup runs ~2 s late; a switch meanwhile was
                                   handled by nobody on the Papyrus side.
  ESSB_HeatBodyFx                  the MCM switch 「白熱全身特效」 (default 1): the body fire of 白熱 / 熔燒 / 熔身 is its own
                                   effect in those status spells, conditioned on this global -- off, the status still works
                                   and nothing burns on you (review 1-3, an A/B switch for the HDT-SMP freeze).
  ESSB_HeatBodyFxEffect            that visual-only effect: the vanilla Flame Cloak's shader and flame art (round 27f), FX
                                   persist, no magnitude, hidden; the status effects themselves carry no shader any more.
  KINDS                            new status kinds appended after round 25's (build/fix19_native.status_ids):
                                   kTrioCooldown -- 三重奏 fired: it cannot fire again for its 10 s window (the user's fix
                                   list 2026-09-28).

  CASTWITH                         round 28b (F1): whole-second copies (1..CASTWITH_MAX_SECONDS s) of every spell with a
                                   magnitude that ESSBNative.CastWith is asked to cast for its own number of seconds (恐懼,
                                   瘋狂, 狂刃, the timed ESSB_Util_* of ApplyUtil). CastSpellImmediate cannot set a duration and
                                   an effectiveness other than 1 scales such an effect's MAGNITUDE (max(|m| x eff, 1), the
                                   duration kept: 0x140540360), so the DLL casts the copy of the asked length with
                                   effectiveness 1 and the asked magnitude as the override (round 24's timed precedent). Each
                                   copy is its base spell's subrecords with only the EDID and the EFIT duration changed.

IDs 0x005E00-0x005EFF (after round 27's 0x005D00-0x005DFF). Append-only.
"""
import struct

BASE = 0x5E00
PAPYRUS_READY_GLOBAL = 'ESSB_PapyrusReady'
HEAT_BODY_FX_GLOBAL = 'ESSB_HeatBodyFx'
HEAT_BODY_FX_EFFECT = 'ESSB_HeatBodyFxEffect'

SELF_HIDDEN_FLAGS = 0x00008C10   # hidden, no magnitude / area / hit event (round 25's self windows)
BODY_FX_FLAGS = 0x00009C10       # the same, FX persist (the shader and art stay for the effect's lifetime)
ARCHETYPE_SCRIPT = 1

# (kind, editor id suffix, label, on_player, seconds, description)
KINDS = [
    ('kTrioCooldown', 'TrioCooldown', '三重奏冷卻', True, 10.0, '三重奏剛觸發：10 秒內不會再觸發。'),
]
KIND_NAMES = [k[0] for k in KINDS]

_ids = {}
_next = BASE


def _take(name, count=1):
    global _next
    _ids[name] = _next
    _next += count
    return _ids[name]


# Round 28b (F1): (name, base spell) -- ('spell', build_v03 constant) / ('util', UTILS index) / ('fix22', frenzy blade)
CASTWITH_MAX_SECONDS = 20   # fear / frenzy <= 3 s x 持續時間 3.0; ApplyUtil <= 6 s x 3.0 = 18 (longer clamps)
CASTWITH = [
    ('Fear', 'spell', 'ID_FEAR_SPELL'),             # ApplyFear: magnitude = the level cap
    ('Frenzy', 'spell', 'ID_FRENZY_SPELL'),         # ApplyFrenzy
    ('FrenzyBlade', 'fix22', 'frenzy_blade'),       # 狂刃: AttackDamageMult +0.5 for the frenzy's seconds
    ('UtilSlow', 'util', 0),                        # ApplyUtil(0, 30, 3): 霜鎖 / 寒霜 slows
    ('UtilFireResistDebuff', 'util', 13),           # ApplyUtil(13, rank, 6)
    ('UtilPoisonResistBuff', 'util', 23),           # ApplyUtil(23, 100, 3)
    ('UtilHealRateBuff', 'util', 25),               # ApplyUtil(25, 20, 3)
    ('UtilDiseaseResistBuff', 'util', 26),          # ApplyUtil(26, 100, 3)
]

_take('PapyrusReady.glob')
_take('HeatBodyFx.glob')
_take('HeatBodyFx.effect')
for _kind in KINDS:
    _take(_kind[0] + '.effect')
    _take(_kind[0] + '.spell')
for _name, *_ in CASTWITH:
    _take('castwith.' + _name, CASTWITH_MAX_SECONDS)
LAST = _next - 1
assert LAST <= 0x5EFF, hex(LAST)


def papyrus_ready_id():
    return _ids['PapyrusReady.glob']


def heat_body_fx_id():
    return _ids['HeatBodyFx.glob']


def heat_body_fx_effect_id():
    return _ids['HeatBodyFx.effect']


def effect_id(kind):
    return _ids[kind + '.effect']


def spell_id(kind):
    return _ids[kind + '.spell']


def edid_effect(suffix):
    return f'ESSB_N7_{suffix}Effect'


def edid_spell(suffix):
    return f'ESSB_N7_{suffix}'


def heat_body_fx_items(b, seconds):
    """The visual effect's item in a heat status spell (build/fix22_records.py): the same duration as the status, on
    only while ESSB_HeatBodyFx is 1 (the engine checks it when the spell lands)."""
    return [('EFID', b.I(b.own(heat_body_fx_effect_id()))), ('EFIT', struct.pack('<fII', 0.0, 0, int(seconds))),
            ('CTDA', b.gv_eq(heat_body_fx_id(), 1))]


def add_records(b, add, flames_shader, flames_art):
    """flames_shader / flames_art: the Skyrim.esm Flame Cloak shader and art as written refs (fix22_records)."""
    I, Z, own = b.I, b.Z, b.own
    etyp = ('ETYP', I(b.ref('Skyrim.esm', 0x13F45)))
    add('GLOB', papyrus_ready_id(), PAPYRUS_READY_GLOBAL, [('FNAM', b's'), ('FLTV', b.F(0))])
    add('GLOB', heat_body_fx_id(), HEAT_BODY_FX_GLOBAL, [('FNAM', b's'), ('FLTV', b.F(1))])
    add('MGEF', heat_body_fx_effect_id(), HEAT_BODY_FX_EFFECT, [
        ('FULL', Z('白熱全身特效')),
        ('DATA', b.mgef_data(BODY_FX_FLAGS, ARCHETYPE_SCRIPT, casting=1, delivery=0, hit_shader=flames_shader,
                             hit_effect_art=flames_art)),
        ('DNAM', Z('白熱、熔燒、熔身時身上的火焰（MCM 可關）。'))])
    for kind, suffix, label, on_player, seconds, text in KINDS:
        delivery = 0 if on_player else 1
        add('MGEF', effect_id(kind), edid_effect(suffix), [
            ('FULL', Z(label)), ('DATA', b.mgef_data(SELF_HIDDEN_FLAGS, ARCHETYPE_SCRIPT, casting=1, delivery=delivery)),
            ('DNAM', Z(text))])
        add('SPEL', spell_id(kind), edid_spell(suffix), [
            ('OBND', bytes(12)), ('FULL', Z(label)), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, delivery)),
            ('EFID', I(own(effect_id(kind)))), ('EFIT', struct.pack('<fII', 0.0, 0, int(seconds))),
        ])


def castwith_base_id(b, name):
    """The local FormID of family `name`'s base spell."""
    import fix22_records as hit22
    _name, kind, arg = next(row for row in CASTWITH if row[0] == name)
    if kind == 'spell':
        return getattr(b, arg)
    if kind == 'util':
        return b.util_spell_id(arg)
    return hit22.frenzy_blade_spell_id()


def castwith_id(name, seconds):
    if not 1 <= seconds <= CASTWITH_MAX_SECONDS:
        raise ValueError(seconds)
    return _ids['castwith.' + name] + seconds - 1


def castwith_edid(name, seconds):
    return f'ESSB_N7_CastWith{name}_{seconds}'


def castwith_rows(b):
    """(name, base local id, [variant local id per second 1..N]) for the DLL table (build/fix19_native.py)."""
    return [(name, castwith_base_id(b, name), [castwith_id(name, s) for s in range(1, CASTWITH_MAX_SECONDS + 1)])
            for name, *_ in CASTWITH]


def add_castwith_variants(b, add, spell_subrecords):
    """Round 28b (F1): after every base spell is written. `spell_subrecords`: local id -> the subrecords add() wrote
    (EDID excluded). A copy keeps everything but its EFIT duration (the magnitude, the effect, SPIT and its flags)."""
    for name, *_ in CASTWITH:
        base = spell_subrecords[castwith_base_id(b, name)]
        assert sum(1 for k, _v in base if k == 'EFID') == 1, (name, 'CastWith casts single-effect spells only')
        for seconds in range(1, CASTWITH_MAX_SECONDS + 1):
            ss = []
            for key, value in base:
                if key == 'EFIT':
                    magnitude, area, _duration = struct.unpack('<fII', value)
                    value = struct.pack('<fII', magnitude, area, seconds)
                ss.append((key, value))
            add('SPEL', castwith_id(name, seconds), castwith_edid(name, seconds), ss)


def contact_edids(b=None):
    names = {edid_spell(suffix) for kind, suffix, label, on_player, *_ in KINDS if not on_player}
    if b is not None:   # round 28b: a copy is delivered as its base (the harmful utilities, fear, frenzy, 狂刃: contact)
        for name, kind, arg in CASTWITH:
            if kind != 'util' or b.UTILS[arg][4]:
                names |= {castwith_edid(name, s) for s in range(1, CASTWITH_MAX_SECONDS + 1)}
    return names


def new_edids():
    names = {PAPYRUS_READY_GLOBAL, HEAT_BODY_FX_GLOBAL, HEAT_BODY_FX_EFFECT}
    for kind, suffix, *_ in KINDS:
        names |= {edid_effect(suffix), edid_spell(suffix)}
    for name, *_ in CASTWITH:
        names |= {castwith_edid(name, s) for s in range(1, CASTWITH_MAX_SECONDS + 1)}
    return names
