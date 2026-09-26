"""Round 25 (slice N6) records: the per-second timers' windows, the domains (領域) as engine hazards, and the markers
the hazards leave on the enemies standing in them (ruling R4: enemy effects through a Spawn Hazard archetype MGEF the
DLL casts with CastSpellImmediate at the fused target's feet; the engine owns the hazard's lifetime and count; the DLL
stores no design state).

  KINDS     status kinds appended after round 24's (build/fix19_native.status_ids concatenates fix22 + fix23 + fix24 +
            these, in this order), so the round-22 machinery (Board reads, Lower, dispel-then-cast, load-time resolution)
            covers them. Target rows are the markers a domain's hazard spell puts on a hostile inside it (2 s; the hazard
            re-applies them when they run out); player rows are the windows the DLL's per-second work keeps on you
            (冰原 你在其中免疫減速, the 2 s of 魔力歸零, the storm's 3 s charge clock). All Script, No Magnitude.
  DOMAINS   per element that has a domain in v0.4 section 5 (火域 冰原 地裂 血池 聖域／神聖領域 毒霧 潮池 死域 星域;
            泥沼 left v0.4 with 地斷's rewrite, lightning and wind have none):
              ESSB_N6_Hazard_<X>       HAZD: invisible (Effects\\FXEmptyObject.nif, the vanilla empty hazard model),
                                       3 m (radius in feet: 210 units / 21.333), Inherit Duration + Drop to Ground,
                                       limit 0, target interval 0.3 s, the hazard spell
              ESSB_N6_HazardSpell_<X>  what the engine casts on every actor hostile to you inside it (native-verification-3
                                       s14.2): the marker (火域／冰原／星域 reuse round 22's ESSB_N3_Domain<X>Effect the hit
                                       path already reads) and the effects the engine can carry alone (地裂 stamina does not
                                       regenerate, 死域 cannot be healed: the shared utility effects #21 / #20 at 100)
              ESSB_N6_Divine<AV>Effect 聖域's「其中敵人傷害 -20%」(審查修正, commander's ruling): two harmful Peak Value
                                       Modifier effects on the divine hazard spell, 2 s like its marker -- AttackDamageMult
                                       -0.2 (AV 154, weapon hits) and DestructionPowerModifier -20 (AV 149, destruction
                                       spells); appended after the domains' ids
              ESSB_N6_DomainEffect_<X> MGEF, archetype 40 Spawn Hazard, associated item = the HAZD, no death dispel (the
                                       fused target may die in the same frame), no magnitude (the hazard keeps its
                                       record magnitudes: magnitude 0 means no override)
              ESSB_N6_Domain_<X>_<s>   one spell per whole second 1..DOMAIN_MAX_SECONDS (CastSpellImmediate cannot set a
                                       duration; the HAZD inherits the spell's): 5 s / 8 s × ESSB_MultDuration (0.25-3)

IDs 0x005800-0x005BFF (after round 24's 0x005600-0x0057FF). Append-only.
"""
import struct

BASE = 0x5800

SELF_HIDDEN_FLAGS = 0x00008C10
TARGET_FLAGS = 0x00008C15      # hostile, detrimental, hidden, no magnitude / area / hit event (the mark flags)
NO_DEATH_DISPEL = 0x10000000
# Spawn Hazard: not hostile (it is cast ON the fused enemy but places a hazard; hostility and the hit event would make
# the corpse or the enemy react to an invisible cast), no hit event, no magnitude, no area, hidden, no death dispel.
SPAWN_FLAGS = 0x00008C10 | NO_DEATH_DISPEL
ARCHETYPE_SCRIPT = 1
ARCHETYPE_SPAWN_HAZARD = 40
UNITS_PER_FOOT = 21.333333     # the engine's feet -> units (披風 radius = magnitude x 21.33, v0.4 5.3)
DOMAIN_RADIUS_UNITS = 210.0    # v0.4 2.9: 融斷後留下的領域 3 公尺
DOMAIN_RADIUS_FEET = DOMAIN_RADIUS_UNITS / UNITS_PER_FOOT
HAZARD_MODEL = 'Effects\\FXEmptyObject.nif'
HAZARD_FLAGS = 0x02 | 0x10     # Inherit Duration from Spawn Spell, Drop to Ground
HAZARD_TARGET_INTERVAL = 0.3   # the vanilla hazards' interval
HAZARD_LIMIT = 0               # 0 = the engine does not cap one hazard type (vanilla FireSpellHazard, IceHazard01)
MARKER_SECONDS = 2             # the hazard spell's markers: re-applied by the hazard once they run out
DOMAIN_MAX_SECONDS = 24        # 神聖領域 8 s × the duration slider's 3.0

UTIL_HEAL_RATE_DEBUFF = 20     # build_v03 UTILS: 治療削減 (HealRateMult)
UTIL_STAMINA_RATE_DEBUFF = 21  # 耐力凝滯 (StaminaRateMult)
# 審查修正（指揮官裁定）: 聖域／神聖領域「其中敵人傷害 -20%」as the hazard's own effects on the enemies inside:
# (key, editor id suffix, label, AV, magnitude taken off) -- harmful Peak Value Modifier (archetype 34, Recover).
AV_DESTRUCTION_POWER_MODIFIER = 149
AV_ATTACK_DAMAGE_MULT = 154
DIVINE_WEAKEN = [
    ('attack', 'DivineAttack', '聖域：攻擊減弱', AV_ATTACK_DAMAGE_MULT, 0.2),
    ('magic', 'DivineMagic', '聖域：毀滅法術減弱', AV_DESTRUCTION_POWER_MODIFIER, 20.0),
]

# (kind, editor id suffix, label, on_player, seconds, description)
KINDS = [
    # ---- markers the hazards put on a hostile inside them
    ('kDomainEarth', 'DomainEarth', '地裂', False, 2.0, '身在地裂：耐力不回復，耐力歸 0 時跌倒。'),
    ('kDomainBlood', 'DomainBlood', '血池', False, 2.0, '身在血池（血池只對你有效果）。'),
    ('kDomainDivine', 'DomainDivine', '聖域', False, 2.0, '身在聖域。'),
    ('kDomainPoison', 'DomainPoison', '毒霧', False, 2.0, '身在毒霧：每秒中毒 +1 劑。'),
    ('kDomainWater', 'DomainWater', '潮池', False, 2.0, '身在潮池：每秒被沖刷一個增益。'),
    ('kDomainDark', 'DomainDark', '死域', False, 2.0, '身在死域：無法被治療，每秒受暗傷。'),
    # ---- your windows
    ('kFrostDomainPlayer', 'FrostDomainPlayer', '冰原：免疫減速', True, 2.0, '你在冰原中：免疫減速。'),
    ('kManaEmpty', 'ManaEmpty', '魔力歸零', True, 3600.0, '魔力歸零多久了（2 秒後關閉形態）。'),
    ('kStormCooldown', 'StormCooldown', '雷雨充能', True, 3.0, '雷雨：每 3 秒一格電荷。'),
]
KIND_NAMES = [k[0] for k in KINDS]

# element (1..11) -> (suffix, label, the hazard spell's effects: ('kind', name) = a status kind's effect (round 22's
# ESSB_N3_* or this round's), ('util', index) = a shared utility effect at magnitude 100)
DOMAINS = {
    1: ('Fire', '火域', [('n3', 'kDomainFire')]),
    2: ('Frost', '冰原', [('n3', 'kDomainFrost')]),
    4: ('Earth', '地裂', [('n6', 'kDomainEarth'), ('util', UTIL_STAMINA_RATE_DEBUFF)]),
    6: ('Blood', '血池', [('n6', 'kDomainBlood')]),
    7: ('Divine', '聖域', [('n6', 'kDomainDivine'), ('weaken', 'attack'), ('weaken', 'magic')]),
    8: ('Poison', '毒霧', [('n6', 'kDomainPoison')]),
    9: ('Water', '潮池', [('n6', 'kDomainWater')]),
    10: ('Darkness', '死域', [('n6', 'kDomainDark'), ('util', UTIL_HEAL_RATE_DEBUFF)]),
    11: ('Astral', '星域', [('n3', 'kDomainAstral')]),
}
DOMAIN_ELEMENTS = sorted(DOMAINS)

# ---------------------------------------------------------------- FormID layout (append-only; one place)
_ids = {}
_next = BASE


def _take(name, count=1):
    global _next
    _ids[name] = _next
    _next += count
    return _ids[name]


for _kind in KINDS:
    _take(_kind[0] + '.effect')
    _take(_kind[0] + '.spell')
for _element in DOMAIN_ELEMENTS:
    _take(f'{_element}.hazard')
    _take(f'{_element}.hazardSpell')
    _take(f'{_element}.spawnEffect')
    _take(f'{_element}.spawn', DOMAIN_MAX_SECONDS)
for _weaken in DIVINE_WEAKEN:          # 審查修正: appended after the domains, nothing above moves
    _take(_weaken[0] + '.weaken')
_take('EnvThunder.glob')               # 審查修正: ESSB_EnvThunder (2.10 雷雨), the DLL writes it every 5 s
LAST = _next - 1
assert LAST <= 0x5BFF, hex(LAST)


def effect_id(kind):
    return _ids[kind + '.effect']


def spell_id(kind):
    return _ids[kind + '.spell']


def hazard_id(element):
    return _ids[f'{element}.hazard']


def hazard_spell_id(element):
    return _ids[f'{element}.hazardSpell']


def spawn_effect_id(element):
    return _ids[f'{element}.spawnEffect']


THUNDER_GLOBAL = 'ESSB_EnvThunder'


def thunder_global_id():
    return _ids['EnvThunder.glob']


def weaken_id(key):
    return _ids[key + '.weaken']


def weaken_edid(key):
    return 'ESSB_N6_' + {w[0]: w[1] for w in DIVINE_WEAKEN}[key] + 'Effect'


def spawn_id(element, seconds):
    if not 1 <= seconds <= DOMAIN_MAX_SECONDS:
        raise ValueError(seconds)
    return _ids[f'{element}.spawn'] + seconds - 1


def edid_effect(suffix):
    return f'ESSB_N6_{suffix}Effect'


def edid_spell(suffix):
    return f'ESSB_N6_{suffix}'


def hazard_edid(element):
    return f'ESSB_N6_Hazard_{DOMAINS[element][0]}'


def hazard_spell_edid(element):
    return f'ESSB_N6_HazardSpell_{DOMAINS[element][0]}'


def spawn_effect_edid(element):
    return f'ESSB_N6_DomainEffect_{DOMAINS[element][0]}'


def spawn_edid(element, seconds):
    return f'ESSB_N6_Domain_{DOMAINS[element][0]}_{seconds}'


def hazard_effects(b, element):
    """The hazard spell's effects as (local MGEF id, magnitude, seconds)."""
    out = []
    for source, name in DOMAINS[element][2]:
        if source == 'n3':
            out.append((b.hit22.effect_id(name), 0.0, MARKER_SECONDS))
        elif source == 'n6':
            out.append((effect_id(name), 0.0, MARKER_SECONDS))
        elif source == 'weaken':
            out.append((weaken_id(name), {w[0]: w[4] for w in DIVINE_WEAKEN}[name], MARKER_SECONDS))
        else:
            out.append((b.util_effect_id(name), 100.0, MARKER_SECONDS))
    return out


def add_records(b, add):
    I, F, Z = b.I, b.F, b.Z
    own = b.own
    etyp = ('ETYP', I(b.ref('Skyrim.esm', 0x13F45)))
    for kind, suffix, label, on_player, seconds, text in KINDS:
        delivery = 0 if on_player else 1
        flags = SELF_HIDDEN_FLAGS if on_player else TARGET_FLAGS
        add('MGEF', effect_id(kind), edid_effect(suffix), [
            ('FULL', Z(label)), ('DATA', b.mgef_data(flags, ARCHETYPE_SCRIPT, casting=1, delivery=delivery)), ('DNAM', Z(text))])
        add('SPEL', spell_id(kind), edid_spell(suffix), [
            ('OBND', bytes(12)), ('FULL', Z(label)), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, delivery)),
            ('EFID', I(own(effect_id(kind)))), ('EFIT', struct.pack('<fII', 0.0, 0, int(seconds))),
        ])
    # 審查修正 (v0.4 2.10): 雷雨 is its own flag -- ESSB_EnvStormy stays 暴風雪 (the hit path's 凍結累積 ×2).
    add('GLOB', thunder_global_id(), THUNDER_GLOBAL, [('FNAM', b's'), ('FLTV', b.F(0))])
    for key, suffix, label, av, _magnitude in DIVINE_WEAKEN:
        add('MGEF', weaken_id(key), weaken_edid(key), [
            ('FULL', Z(f'元素魔戰士：{label}')),
            ('DATA', b.mgef_data(b.MGEF_DEBUFF_FLAGS, 34, base_cost=1.0, skill=-1, resist=-1, actor_value=av,
                                 casting=1, delivery=1)),
            ('DNAM', Z(f'{label} <mag>。'))])
    for element in DOMAIN_ELEMENTS:
        suffix, label, _effects = DOMAINS[element]
        spell = [('OBND', bytes(12)), ('FULL', Z(f'元素魔戰士：{label}')), etyp, ('DESC', Z('')), ('SPIT', b.spit(0, 1, 1))]
        for effect, magnitude, seconds in hazard_effects(b, element):
            spell += [('EFID', I(own(effect))), ('EFIT', struct.pack('<fII', magnitude, 0, seconds))]
        add('SPEL', hazard_spell_id(element), hazard_spell_edid(element), spell)
        data = struct.pack('<IffffIIIII', HAZARD_LIMIT, DOMAIN_RADIUS_FEET, 5.0, 0.0, HAZARD_TARGET_INTERVAL, HAZARD_FLAGS,
                           own(hazard_spell_id(element)), 0, 0, 0)
        add('HAZD', hazard_id(element), hazard_edid(element), [
            ('OBND', bytes(12)), ('FULL', Z(f'元素魔戰士：{label}')), ('MODL', Z(HAZARD_MODEL)), ('DATA', data)])
        mgef = bytearray(b.mgef_data(SPAWN_FLAGS, ARCHETYPE_SPAWN_HAZARD, casting=1, delivery=1))
        struct.pack_into('<I', mgef, 8, own(hazard_id(element)))   # wbMGEFData: Assoc. Item at offset 8
        add('MGEF', spawn_effect_id(element), spawn_effect_edid(element), [
            ('FULL', Z(f'元素魔戰士：{label}')), ('DATA', bytes(mgef)), ('DNAM', Z(f'在這裡留下{label}。'))])
        for seconds in range(1, DOMAIN_MAX_SECONDS + 1):
            add('SPEL', spawn_id(element, seconds), spawn_edid(element, seconds), [
                ('OBND', bytes(12)), ('FULL', Z(f'元素魔戰士：{label}')), etyp, ('DESC', Z('')), ('SPIT', b.spit(0, 1, 1)),
                ('EFID', I(own(spawn_effect_id(element)))), ('EFIT', struct.pack('<fII', 0.0, 0, seconds)),
            ])


def contact_edids():
    """Spells cast ON a target (delivery 1): the markers' own spells, the hazard spells, the spawn spells."""
    names = {edid_spell(suffix) for kind, suffix, label, on_player, *_ in KINDS if not on_player}
    for element in DOMAIN_ELEMENTS:
        names.add(hazard_spell_edid(element))
        names |= {spawn_edid(element, s) for s in range(1, DOMAIN_MAX_SECONDS + 1)}
    return names


def new_edids():
    names = set()
    for kind, suffix, *_ in KINDS:
        names |= {edid_effect(suffix), edid_spell(suffix)}
    for element in DOMAIN_ELEMENTS:
        names |= {hazard_edid(element), hazard_spell_edid(element), spawn_effect_edid(element)}
        names |= {spawn_edid(element, s) for s in range(1, DOMAIN_MAX_SECONDS + 1)}
    names |= {weaken_edid(w[0]) for w in DIVINE_WEAKEN}
    names.add(THUNDER_GLOBAL)
    return names
