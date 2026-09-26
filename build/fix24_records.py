"""Round 24 (slice N5) records: what the DLL needs to run the reaction bodies, the fusion and the death handling itself
(ruling R4: the damage and status parts of the Papyrus bodies move into the DLL; the DLL stores no design state).

  KINDS     status kinds appended after round 23's (build/fix19_native.status_ids concatenates fix22 + fix23 + these,
            in this order), so the round-22 machinery (Board reads, Lower, dispel-then-cast, load-time resolution of every
            spell the DLL can cast) covers them unchanged. Script rows are markers / cooldowns / windows (No Magnitude,
            magnitude override, duration through effectiveness; round 22 ledger decision 1). AV rows are 血承's seven
            Peak Value Modifiers on you (fixed record duration 15 s, magnitude override = the value; round 23 precedent).
  TIMED     the timed utility debuffs / buffs a reaction body casts (碎甲、攻擊削弱、抗性削減、治療削減、耐力凝滯、移速、
            毒抗、魔抗): CastSpellImmediate cannot set a duration and effectiveness only scales a magnitude effect's
            magnitude (0x140540360, round 24 ledger decision 2), so -- like round 21's soaked slow -- one spell per whole
            second (1..TIMED_MAX_SECONDS) sharing the existing ESSB_UtilEffect_<X> (the same effect the Papyrus bodies
            used; a Peak Value Modifier: the strongest instance counts, it never stacks).

IDs 0x005600-0x0057FF (after round 23's 0x005500-0x0055FF). Append-only.
"""
import struct

BASE = 0x5600

SELF_FLAGS = 0x00000C10        # visible in the player's Active Effects, not hostile, no magnitude / area
SELF_HIDDEN_FLAGS = 0x00008C10
TARGET_FLAGS = 0x00008C15      # hostile, detrimental, hidden, no magnitude / area / hit event (the mark flags)
AV_FLAGS = 0x00008812          # build_v03 MGEF_BUFF_FLAGS: Recover, not hostile, hidden

# (kind, editor id suffix, label, on_player, seconds, hidden, description, av)
KINDS = [
    # ---- markers the death sink reads on the corpse (set BEFORE the damage that may kill, same frame)
    ('kCremation', 'Cremation', '爆燃擊殺', False, 1.0, True, '1 秒內被你的爆燃打中（火葬讀它；強度＝那一下的爆燃量）。', None),
    ('kCurseKill', 'CurseKill', '死咒擊殺', False, 1.0, True, '1 秒內被你的死咒結算打中（亡魂、冥召讀它）。', None),
    # ---- windows and cooldowns
    ('kUndyingCooldown', 'UndyingCooldown', '不死冷卻', True, 30.0, True, '不死：每 30 秒一次。', None),
    ('kDoubleBurst', 'DoubleBurst', '雙斷', True, 3.0, False, '雙斷：3 秒內再開形態，對範圍內敵人立即開印一次。', None),
    ('kSafetyValve', 'SafetyValve', '安全閥', True, 2.0, False, '安全閥：受傷 -50%。', None),
    ('kRadiance', 'Radiance', '光耀', False, 5.0, True, '光耀：受聖傷 +20%。', None),
    ('kStarChainCooldown', 'StarChainCooldown', '星鏈冷卻', False, 2.0, True, '星鏈：每目標每 2 秒一次。', None),
    # ---- 血承 (5.8): the corpse's resists and more, on you for 15 s; only the latest one is kept (dispel-then-cast)
    ('kInheritFire', 'InheritFire', '血承：火抗', True, 15.0, False, '火抗 +<mag>。', 41),
    ('kInheritFrost', 'InheritFrost', '血承：冰抗', True, 15.0, False, '冰抗 +<mag>。', 43),
    ('kInheritShock', 'InheritShock', '血承：電抗', True, 15.0, False, '電抗 +<mag>。', 42),
    ('kInheritPoison', 'InheritPoison', '血承：毒抗', True, 15.0, False, '毒抗 +<mag>。', 40),
    ('kInheritMagic', 'InheritMagic', '血承：魔抗', True, 15.0, False, '魔抗 +<mag>。', 44),
    ('kInheritArmor', 'InheritArmor', '血承：護甲', True, 15.0, False, '護甲 +<mag>。', 39),
    ('kInheritHealth', 'InheritHealth', '血承：生命上限', True, 15.0, False, '生命上限 +<mag>。', 24),
]
KIND_NAMES = [k[0] for k in KINDS]

# The timed utilities (build_v03 UTILS index -> the C++ name). Target ones are contact casts, self ones self casts
# (the delivery of the shared ESSB_UtilEffect_<X>).
TIMED = [
    (1, 'kArmorDebuff'),         # 碎甲、聖裁破防、裂痕與震波的護甲削減
    (8, 'kMagicResistBuff'),     # 護持（你）
    (9, 'kHaste'),               # 雷閃、輕躍（你）
    (13, 'kFireResistDebuff'),   # 詛咒的抗性侵蝕、斷界
    (14, 'kFrostResistDebuff'),
    (15, 'kShockResistDebuff'),
    (16, 'kMagicResistDebuff'),  # 聖裁破防、感電削弱、腐蝕終焉、詛咒侵蝕、斷界
    (17, 'kMeleeDebuff'),        # 塵暴、深寒、萎靡
    (20, 'kHealRateDebuff'),     # 血咒、死咒的無法治療
    (21, 'kStaminaRateDebuff'),  # 地基、深寒
    (23, 'kPoisonResistBuff'),   # 毒膜（你）
    (24, 'kPoisonResistDebuff'), # 腐蝕開印、侵蝕、劇毒、詛咒侵蝕、斷界
]
TIMED_MAX_SECONDS = 20        # the longest body duration is 劇毒's poison remainder (15 s + 延毒 4 s); longer ones clamp
SELF_UTILS = {8, 9, 23}

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
for _util, _name in TIMED:
    _take(_name + '.timed', TIMED_MAX_SECONDS)
# review fix 3: the raised servant's attack bonus (詛咒 5 層以上每層 +10%) rides on ESSB_ReanimateSpell as its second effect
SERVANT_ATTACK_EFFECT = _take('servantAttack.effect')
SERVANT_ATTACK_EDID = 'ESSB_N5_ServantAttackEffect'
AV_ATTACK_DAMAGE_MULT = 154   # RE::ActorValue::kAttackDamageMult (build/fix22_records.py)
NO_DEATH_DISPEL = 0x10000000  # the corpse is still dead when the spell lands; the reanimate effect raises it
LAST = _next - 1
assert LAST <= 0x57FF, hex(LAST)


def effect_id(kind):
    return _ids[kind + '.effect']


def spell_id(kind):
    return _ids[kind + '.spell']


def timed_id(name, seconds):
    if not 1 <= seconds <= TIMED_MAX_SECONDS:
        raise ValueError(seconds)
    return _ids[name + '.timed'] + seconds - 1


def edid_effect(suffix):
    return f'ESSB_N5_{suffix}Effect'


def edid_spell(suffix):
    return f'ESSB_N5_{suffix}'


def timed_edid(name, seconds):
    return f'ESSB_N5_Timed{name[1:]}_{seconds}'


def add_records(b, add):
    I, Z = b.I, b.Z
    own = b.own
    etyp = ('ETYP', I(b.ref('Skyrim.esm', 0x13F45)))
    for kind, suffix, label, on_player, seconds, hidden, text, av in KINDS:
        delivery = 0 if on_player else 1
        if av is not None:
            data = b.mgef_data(AV_FLAGS, 34, actor_value=av, casting=1, delivery=delivery)
        else:
            flags = (SELF_HIDDEN_FLAGS if hidden else SELF_FLAGS) if on_player else TARGET_FLAGS
            data = b.mgef_data(flags, 1, casting=1, delivery=delivery)
        add('MGEF', effect_id(kind), edid_effect(suffix), [('FULL', Z(label)), ('DATA', data), ('DNAM', Z(text))])
        add('SPEL', spell_id(kind), edid_spell(suffix), [
            ('OBND', bytes(12)), ('FULL', Z(label)), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, delivery)),
            ('EFID', I(own(effect_id(kind)))), ('EFIT', struct.pack('<fII', 0.0, 0, int(seconds))),
        ])
    add('MGEF', SERVANT_ATTACK_EFFECT, SERVANT_ATTACK_EDID, [
        ('FULL', Z('元素魔戰士：亡者歸來（攻擊）')),
        ('DATA', b.mgef_data(b.MGEF_BUFF_FLAGS | 0x8000 | NO_DEATH_DISPEL, 34, actor_value=AV_ATTACK_DAMAGE_MULT, casting=1,
                             delivery=1)),
        ('DNAM', Z('僕從攻擊 +<mag>（倍率）。')),
    ])
    for util, name in TIMED:
        suffix, label, _av, timed, harmful, _resist = b.UTILS[util]
        assert timed, (util, 'a timed family needs a timed utility effect')
        delivery = 1 if harmful else 0
        assert (util in SELF_UTILS) == (not harmful), (util, 'self utilities are the beneficial ones')
        for seconds in range(1, TIMED_MAX_SECONDS + 1):
            add('SPEL', timed_id(name, seconds), timed_edid(name, seconds), [
                ('OBND', bytes(12)), ('FULL', Z(f'元素魔戰士：{label}')), etyp, ('DESC', Z('')),
                ('SPIT', b.spit(0, 1, delivery)),
                ('EFID', I(own(b.util_effect_id(util)))), ('EFIT', struct.pack('<fII', 0.0, 0, seconds)),
            ])


def contact_edids(b):
    """Spells cast ON a target (delivery 1)."""
    names = {edid_spell(suffix) for kind, suffix, label, on_player, *_ in KINDS if not on_player}
    for util, name in TIMED:
        if util not in SELF_UTILS:
            names |= {timed_edid(name, s) for s in range(1, TIMED_MAX_SECONDS + 1)}
    return names


def new_edids():
    names = set()
    for kind, suffix, *_ in KINDS:
        names |= {edid_effect(suffix), edid_spell(suffix)}
    for _util, name in TIMED:
        names |= {timed_edid(name, s) for s in range(1, TIMED_MAX_SECONDS + 1)}
    return names | {SERVANT_ATTACK_EDID}
