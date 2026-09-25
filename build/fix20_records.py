"""Round 20 (slice N2) records: what the DLL casts besides the element proc spells.

CastSpellImmediate's magnitude override is applied to every effect of a spell (native-verification-2
section 10: NO), so every value the DLL computes rides on a single-effect spell of its own:
  * existing single-effect utilities are reused as they are (drain / restore magicka, stamina, health),
    the true-damage spell and the 8-second dispel mark (滅法印 = the ESP's ESSB_ManaBreakSpell);
  * new here: a non-hostile self magicka spend (滅法 X), the 10-second soaked slow, eight fixed-duration
    silences (the override cannot change durations), the 護血 pool effect on the player, and the two
    markers Papyrus puts on the player at a form switch (echo pending, twin window).
IDs 0x005300-0x00531F.
"""
import struct

SPEND_EFFECT = 0x5300
SPEND = 0x5301
SOAK_SLOW = 0x5302
GUARD_EFFECT = 0x5303
GUARD = 0x5304
ECHO_EFFECT = 0x5305
ECHO = 0x5306
TWIN_EFFECT = 0x5307
TWIN = 0x5308
SILENCE = 0x5310          # + seconds - 1, seconds 1..8
SILENCE_COUNT = 8
SOAK_SLOW_SECONDS = 10    # v0.4 浸濕 lasts 10 s
GUARD_SECONDS = 86400     # the pool does not decay (v0.4 2.3); Papyrus dispels it when you leave the form
ECHO_SECONDS = 3600       # "first hit after a switch": no expiry in v0.4; one real hour is effectively none
TWIN_SECONDS = 30         # Papyrus rewrites it with DurationInt(30) before each cast

# MGEF flags: 0x1 hostile, 0x4 detrimental, 0x10 no hit event, 0x200 no duration, 0x400 no magnitude,
# 0x800 no area, 0x8000 hide in UI.
SPEND_FLAGS = 0x00008A14   # instant, self, detrimental but not hostile (no aggro, no hit event on you)
GUARD_FLAGS = 0x00000810   # visible in Active Effects with its magnitude (the pool), no area, no hit event
MARKER_FLAGS = 0x00008C10  # hidden script marker without magnitude


def silence_edid(seconds):
    return f'ESSB_Native_Silence_{seconds}'


def add_records(b, add):
    I, Z = b.I, b.Z
    own = b.own
    etyp = ('ETYP', I(b.ref('Skyrim.esm', 0x13F45)))
    add('MGEF', SPEND_EFFECT, 'ESSB_Native_SpendMagickaEffect', [
        ('FULL', Z('滅法：耗魔')),
        ('DATA', b.mgef_data(SPEND_FLAGS, 0, base_cost=1.0, skill=-1, resist=-1, actor_value=25, casting=1, delivery=0)),
    ])
    add('SPEL', SPEND, 'ESSB_Native_SpendMagicka', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：滅法耗魔')), etyp, ('DESC', Z('')),
        ('SPIT', b.spit(0, 1, 0)),
        ('EFID', I(own(SPEND_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
    ])
    add('SPEL', SOAK_SLOW, 'ESSB_Native_SoakSlow', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：浸濕減速')), etyp, ('DESC', Z('')),
        ('SPIT', b.spit(0, 1, 1)),
        ('EFID', I(own(b.util_effect_id(0)))), ('EFIT', struct.pack('<fII', 0.0, 0, SOAK_SLOW_SECONDS)),
    ])
    add('MGEF', GUARD_EFFECT, 'ESSB_BloodGuardEffect', [
        ('FULL', Z('護血')),
        ('DATA', b.mgef_data(GUARD_FLAGS, 1, casting=1, delivery=0)),
        ('DNAM', Z('護血池 <mag> 點（吸血溢出灌入，上限最大生命 20%）。')),
    ])
    add('SPEL', GUARD, 'ESSB_BloodGuard', [
        ('OBND', bytes(12)), ('FULL', Z('護血')), etyp, ('DESC', Z('')),
        ('SPIT', b.spit(0, 1, 0)),
        ('EFID', I(own(GUARD_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, GUARD_SECONDS)),
    ])
    for effect, spell, edid, label, seconds in [
            (ECHO_EFFECT, ECHO, 'ESSB_EchoPending', '餘響待發', ECHO_SECONDS),
            (TWIN_EFFECT, TWIN, 'ESSB_TwinWindow', '雙生', TWIN_SECONDS)]:
        add('MGEF', effect, edid + 'Effect', [
            ('FULL', Z(label)),
            ('DATA', b.mgef_data(MARKER_FLAGS, 1, casting=1, delivery=0)),
        ])
        add('SPEL', spell, edid, [
            ('OBND', bytes(12)), ('FULL', Z(label)), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, 0)),
            ('EFID', I(own(effect))), ('EFIT', struct.pack('<fII', 0.0, 0, seconds)),
        ])
    # Same two effects as ESSB_SilenceSpell (script silence + MagickaRateMult -100), fixed durations.
    for seconds in range(1, SILENCE_COUNT + 1):
        add('SPEL', SILENCE + seconds - 1, silence_edid(seconds), [
            ('OBND', bytes(12)), ('FULL', Z('沉默')), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, 1)),
            ('EFID', I(own(b.ID_SILENCE_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, seconds)),
            ('EFID', I(own(b.util_effect_id(12)))), ('EFIT', struct.pack('<fII', 100.0, 0, seconds)),
        ])


def new_edids():
    names = {'ESSB_Native_SpendMagickaEffect', 'ESSB_Native_SpendMagicka', 'ESSB_Native_SoakSlow',
             'ESSB_BloodGuardEffect', 'ESSB_BloodGuard', 'ESSB_EchoPendingEffect', 'ESSB_EchoPending',
             'ESSB_TwinWindowEffect', 'ESSB_TwinWindow'}
    return names | {silence_edid(s) for s in range(1, SILENCE_COUNT + 1)}
