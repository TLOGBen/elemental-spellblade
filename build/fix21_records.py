"""Round 21 records: what the v0.4 skill trees need that the ESP did not have yet.

  * soaked slow in fixed durations (commander ruling R6): CastSpellImmediate cannot set a duration, so the DLL
    picks the spell of the right length, the same technique as the eight silences. 1..30 seconds; the existing
    10-second ESSB_Native_SoakSlow (round 20) is the 10-second member, the other 29 are new.
  * 寂 (ESSB_Hush, magnitude = layers, 10 s) and the 寂滅 "used" marker: 寂 is given by 冷寂 at 融斷 (N5); the
    DLL already reads it for 寂滅 (R5, the N2 half) and marks the target once the bonus is spent.
  * 反擊 window on the player (3 s): ESSBGuard opens it on a successful block (N4 detection stays in Papyrus),
    the DLL doubles the next no-form siphon and removes it.
  * 冰甲 / 冰甲＋霜膚: a constant cloak on the player in frost form (3 m, 5 m) whose touched spell slows hostiles
    20% / 30% for one second at a time (v0.4 5.4, 引擎效果 + Papyrus 掛披風).
IDs 0x005320-0x00534F (after round 20's 0x005300-0x00531F).
"""
import struct

SOAK_MAX_SECONDS = 30
SOAK_EXISTING = 0x5302           # round 20 ESSB_Native_SoakSlow: 10 s
SOAK_EXISTING_SECONDS = 10
SOAK_BASE = 0x5320               # the 29 others, in ascending seconds (1..9, 11..30)

HUSH_EFFECT = 0x5340
HUSH = 0x5341
HUSH_SPENT_EFFECT = 0x5342
HUSH_SPENT = 0x5343
RIPOSTE_EFFECT = 0x5344
RIPOSTE = 0x5345
ICE_CHILL_EFFECT = 0x5346
ICE_CHILL = 0x5347
ICE_CHILL_WIDE = 0x5348
ICE_CLOAK_EFFECT = 0x5349
ICE_CLOAK_WIDE_EFFECT = 0x534A
ICE_ARMOR = 0x534B
ICE_ARMOR_WIDE = 0x534C

HUSH_SECONDS = 10                # v0.4 5.1 冷寂：寂 10 秒
RIPOSTE_SECONDS = 3              # v0.4 5.1 反擊：格擋成功後 3 秒內
ICE_CHILL_PCT = 20.0             # v0.4 5.4 冰甲：範圍內敵人減速 20%
ICE_CHILL_WIDE_PCT = 30.0        # 霜膚：寒氣減速再 +10%
ICE_RADIUS_FEET = 10.0           # cloak magnitude is the radius in feet: 3 m = 9.8 ft
ICE_RADIUS_WIDE_FEET = 16.0      # 霜膚：5 m = 16.4 ft

# MGEF flags: 0x1 hostile, 0x2 recover, 0x4 detrimental, 0x10 no hit event, 0x800 no area, 0x8000 hide in UI.
HUSH_FLAGS = 0x00000814          # detrimental stack holder, magnitude = layers (visible), no area, no hit event
MARKER_FLAGS = 0x00008C10        # hidden script marker without magnitude (same as round 20's markers)
CLOAK_FLAGS = 0x00000800         # the player's cloak ability: no area (the magnitude is the radius)
CHILL_FLAGS = 0x00008817         # hostile, recover, detrimental, no hit event, no area, hidden (like the shared slow)
# The cloak's touched effect only lands on hostiles: the exact condition vanilla FrostDamageConcAimedCloak carries
# (Skyrim.esm, function 0x2CF == 1, run on the subject).
HOSTILE_CTDA = bytes.fromhex('000000000000803fcf02000000000000000000000000000000000000ffffffff')


def soak_id(seconds):
    if not 1 <= seconds <= SOAK_MAX_SECONDS:
        raise ValueError(seconds)
    if seconds == SOAK_EXISTING_SECONDS:
        return SOAK_EXISTING
    return SOAK_BASE + seconds - 1 - (1 if seconds > SOAK_EXISTING_SECONDS else 0)


def soak_edid(seconds):
    return 'ESSB_Native_SoakSlow' if seconds == SOAK_EXISTING_SECONDS else f'ESSB_Native_Soak_{seconds}'


def add_records(b, add):
    I, Z = b.I, b.Z
    own = b.own
    etyp = ('ETYP', I(b.ref('Skyrim.esm', 0x13F45)))
    for seconds in range(1, SOAK_MAX_SECONDS + 1):
        if seconds == SOAK_EXISTING_SECONDS:
            continue   # round 20's record (build/fix20_records.py) is this length already
        add('SPEL', soak_id(seconds), soak_edid(seconds), [
            ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：浸濕減速')), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, 1)),
            ('EFID', I(own(b.util_effect_id(0)))), ('EFIT', struct.pack('<fII', 0.0, 0, seconds)),
        ])
    add('MGEF', HUSH_EFFECT, 'ESSB_HushEffect', [
        ('FULL', Z('寂')),
        ('DATA', b.mgef_data(HUSH_FLAGS, 1, casting=1, delivery=1)),
        ('DNAM', Z('寂 <mag> 層：冷寂結清的元素數（沉默每層 +0.5 秒；寂滅以它為條件）。')),
    ])
    add('SPEL', HUSH, 'ESSB_Hush', [
        ('OBND', bytes(12)), ('FULL', Z('寂')), etyp, ('DESC', Z('')),
        ('SPIT', b.spit(0, 1, 1)),
        ('EFID', I(own(HUSH_EFFECT))), ('EFIT', struct.pack('<fII', 1.0, 0, HUSH_SECONDS)),
    ])
    for effect, spell, edid, label, seconds, delivery in [
            (HUSH_SPENT_EFFECT, HUSH_SPENT, 'ESSB_HushSpent', '寂滅已用', HUSH_SECONDS, 1),
            (RIPOSTE_EFFECT, RIPOSTE, 'ESSB_RiposteWindow', '反擊', RIPOSTE_SECONDS, 0)]:
        add('MGEF', effect, edid + 'Effect', [
            ('FULL', Z(label)),
            ('DATA', b.mgef_data(MARKER_FLAGS, 1, casting=1, delivery=delivery)),
        ])
        add('SPEL', spell, edid, [
            ('OBND', bytes(12)), ('FULL', Z(label)), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, delivery)),
            ('EFID', I(own(effect))), ('EFIT', struct.pack('<fII', 0.0, 0, seconds)),
        ])
    # 冰甲：the touched slow (concentration / aimed, as vanilla cloak payloads), peak value modifier on SpeedMult so
    # it does not add to the mod's other slows.
    add('MGEF', ICE_CHILL_EFFECT, 'ESSB_IceArmorChillEffect', [
        ('FULL', Z('冰甲寒氣')),
        ('DATA', b.mgef_data(CHILL_FLAGS, 34, actor_value=30, casting=2, delivery=2)),
        ('DNAM', Z('寒氣減速 <mag>%。')),
        ('CTDA', HOSTILE_CTDA),
    ])
    for spell, edid, pct in [(ICE_CHILL, 'ESSB_IceArmorChill', ICE_CHILL_PCT),
                             (ICE_CHILL_WIDE, 'ESSB_IceArmorChillWide', ICE_CHILL_WIDE_PCT)]:
        add('SPEL', spell, edid, [
            ('OBND', bytes(12)), ('FULL', Z('冰甲寒氣')), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 2, 2)),
            ('EFID', I(own(ICE_CHILL_EFFECT))), ('EFIT', struct.pack('<fII', pct, 0, 1)),
        ])
    for effect, payload, ability, edid, label, feet in [
            (ICE_CLOAK_EFFECT, ICE_CHILL, ICE_ARMOR, 'ESSB_IceArmor', '冰甲', ICE_RADIUS_FEET),
            (ICE_CLOAK_WIDE_EFFECT, ICE_CHILL_WIDE, ICE_ARMOR_WIDE, 'ESSB_IceArmorWide', '冰甲（霜膚）', ICE_RADIUS_WIDE_FEET)]:
        data = bytearray(b.mgef_data(CLOAK_FLAGS, 35, casting=0, delivery=0))
        struct.pack_into('<I', data, 8, own(payload))    # Assoc. Item: the spell the cloak applies
        add('MGEF', effect, edid + 'CloakEffect', [
            ('FULL', Z(label)),
            ('DATA', bytes(data)),
            ('DNAM', Z(f'{label}：身上一圈寒氣，範圍內的敵人被減速。')),
        ])
        add('SPEL', ability, edid, [
            ('OBND', bytes(12)), ('FULL', Z(f'元素魔戰士：{label}')), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(4, 0, 0)),
            ('EFID', I(own(effect))), ('EFIT', struct.pack('<fII', feet, 0, 0)),
        ])


def new_edids():
    names = {soak_edid(s) for s in range(1, SOAK_MAX_SECONDS + 1) if s != SOAK_EXISTING_SECONDS}
    names |= {'ESSB_HushEffect', 'ESSB_Hush', 'ESSB_HushSpentEffect', 'ESSB_HushSpent', 'ESSB_RiposteWindowEffect',
              'ESSB_RiposteWindow', 'ESSB_IceArmorChillEffect', 'ESSB_IceArmorChill', 'ESSB_IceArmorChillWide',
              'ESSB_IceArmorCloakEffect', 'ESSB_IceArmorWideCloakEffect', 'ESSB_IceArmor', 'ESSB_IceArmorWide'}
    return names
