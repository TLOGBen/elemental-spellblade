"""Round 22 (slice N3) records: the target status layer and the fire / divine self ladders as engine effects.

v0.4 2.3: every status is one effect on the target or the player; its layers are the effect's magnitude and its time
is the effect's duration. The DLL reads them at hit time, works out the next state and re-applies (Dispel(true) of the
old instance first, native-verification-3 section 5). This file is the single table of those effects:

  KINDS             one row per status: editor ID, label, who carries it, default seconds, whether its end needs a
                    settlement (a stub script makes the engine send the effect-removed event, native-verification-3 s2)
  DOT_KINDS         the two damage-over-time effects (blood, poison): Value Modifier on Health, so they cannot use the
                    duration-by-effectiveness technique below; one spell per whole second instead (1..DOT_MAX_SECONDS)
  (no miasma)       the 瘴氣 cloak of the first round-22 build is gone (commander ruling (b)+(d)): it cast a poison
                    tick of its own from the NPC (friendly fire, wrong kill credit, a fixed strength); the DLL's
                    per-second tick merges 0.5 dose into the neighbour's one poison instead
  holy tier extras  the passive halves of 聖佑 (weapon damage, armour) ride on the tier spells themselves

Duration technique (ledger decision 1): every status MGEF here is Script archetype with the No Magnitude flag. The
spell-apply visitor writes the magnitude override into the active effect regardless of flags (0x140551980), and the
effectiveness adjustment then scales only the duration of a No Magnitude effect (0x140540360). So the DLL casts with
magnitude override = layers and effectiveness = wanted seconds / record seconds. The record seconds are the design's
default, so if the engine ever behaved otherwise the effect would still last its default time.

IDs 0x005400-0x0054FF (after round 21's 0x005320-0x00534F). The generator writes them in this order.
"""
import struct

import fix21_records as hit21

BASE = 0x5400
STUB_SCRIPT = 'ESSBStub'

# MGEF flags: 0x1 hostile, 0x4 detrimental, 0x10 no hit event, 0x400 no magnitude, 0x800 no area,
# 0x1000 FX persist, 0x8000 hide in UI. (No 0x200 "no duration": effectiveness must scale the duration.)
TARGET_FLAGS = 0x00008C15   # same as the mark effects: hostile, detrimental, hidden, no magnitude/area/hit event
SELF_FLAGS = 0x00000C10     # player ladders are visible in the Active Effects list (not hidden), not hostile
SELF_HIDDEN_FLAGS = 0x00008C10

# (kind, editor id suffix, label, on_player, seconds, stub, description)
# `seconds` is the v0.4 default; the DLL scales it with effectiveness (nodes, MCM duration multiplier).
KINDS = [
    # ---- target statuses (v0.4 2.3 敵方元素狀態)
    ('kFreeze', 'Freeze', '凍結量表', False, 6.0, False, '凍結量表 <mag>／5（6 秒未命中歸零）。'),
    ('kFrozen', 'Frozen', '冰封', False, 3.0, True, '冰封：普攻蓄冰晶、重擊碎冰。'),
    ('kCrystal', 'Crystal', '冰晶', False, 6.0, False, '冰晶 <mag> 顆（碎冰時每顆加成）。'),
    ('kFissure', 'Fissure', '裂痕', False, 8.0, False, '裂痕。'),
    ('kDowned', 'Downed', '倒地', False, 3.0, False, '倒地：被命中的每一擊都算重擊。'),
    ('kUnbalance', 'Unbalance', '失衡', False, 3.0, False, '失衡：受風刃傷害 +30%。'),
    ('kBleed', 'Bleed', '血痕', False, 10.0, False, '血痕 <mag> 層。'),
    ('kJudge', 'Judge', '聖裁計數', False, 4.0, False, '聖裁計數 <mag>。'),
    ('kCatalyzed', 'Catalyzed', '催毒', False, 12.0, False, '催毒中（強度倍率 <mag>）。'),
    ('kSoak', 'Soak', '浸濕', False, 10.0, False, '浸濕。'),
    ('kPressure', 'Pressure', '水壓', False, 8.0, False, '水壓 <mag> 層。'),
    ('kCurse', 'Curse', '詛咒', False, 8.0, False, '詛咒 <mag> 層。'),
    ('kFearCooldown', 'FearCooldown', '恐懼冷卻', False, 12.0, False, '恐懼冷卻。'),
    ('kFrenzyCooldown', 'FrenzyCooldown', '瘋狂冷卻', False, 20.0, False, '瘋狂冷卻。'),
    ('kStar', 'Star', '星痕', False, 30.0, False, '星痕 <mag> 層（共鳴中）。'),
    ('kStarFuse', 'StarFuse', '星痕引信', False, 2.0, True, '停手 2 秒後星痕引爆。'),
    ('kAirborne', 'Airborne', '浮空', False, 2.0, True, '浮空：到期落地受 <mag> 點風傷。'),
    ('kStarLock', 'StarLock', '星鎖', False, 3.0, False, '星鎖：受所有元素傷 +10%。'),
    ('kOpenCooldown', 'OpenCooldown', '開印冷卻', False, 1.0, False, '開印冷卻。'),
    ('kEndCooldown', 'EndCooldown', '終焉冷卻', False, 1.0, False, '終焉冷卻。'),
    ('kGuided', 'Guided', '導引', False, 30.0, False, '導引：下一次終焉 ×<mag>。'),
    ('kDeathCurse', 'DeathCurse', '死咒', False, 3.0, True, '死咒引信。'),
    ('kNether', 'Nether', '冥印', False, 8.0, False, '冥印：帶著它死亡視同帶黑暗印記。'),
    ('kResidual', 'Residual', '副印記', False, 4.0, False, '疊印的副印記（元素 <mag>），融斷時可再結算一次。'),
    ('kWashCooldown', 'WashCooldown', '沖刷冷卻', False, 10.0, False, '沖刷冷卻。'),
    ('kDomainFire', 'DomainFire', '火域', False, 2.0, False, '身在火域：受火傷 +20%。'),
    ('kDomainFrost', 'DomainFrost', '冰原', False, 2.0, False, '身在冰原：凍結累積 ×2。'),
    ('kDomainAstral', 'DomainAstral', '星域', False, 2.0, False, '身在星域：受所有元素傷 +20%。'),
    # 5.12 幻影 (commander ruling (c)): the target carries it 3 s after a dark open; the player's PERK makes each of its
    # hits land for 0 with GetRandomPercent < 30 (build_v03 BRANCH_ENTRY_NODES).
    ('kPhantom', 'Phantom', '幻影', False, 3.0, False, '幻影：對你的每一擊 30% 落空。'),
    # ---- the player's fire and divine ladders and the windows the DLL reads (v0.4 2.3 你身上的資源)
    ('kHeat1', 'Heat1', '熱度：微熱', True, 3600.0, False, '熱度：微熱（火附傷 +15%）。'),
    ('kHeat2', 'Heat2', '熱度：灼熱', True, 3600.0, False, '熱度：灼熱（火附傷 +35%）。'),
    ('kHeat3', 'Heat3', '熱度：白熱', True, 8.0, True, '熱度：白熱（火附傷 +60%；引信到期＝過熱）。'),
    ('kHeat4', 'Heat4', '熱度：熔燒', True, 6.0, True, '熱度：熔燒（火附傷 +90%；到期＝過熱）。'),
    ('kHeatDecay', 'HeatDecay', '熱度維持', True, 6.0, False, '6 秒未命中，熱度退一階。'),
    ('kVentedHeat', 'VentedHeat', '洩壓熱度', True, 30.0, False, '洩壓時的熱度（下一次爆燃照它算）。'),
    ('kMoltenBody', 'MoltenBody', '熔身', True, 10.0, True, '熔身：火附傷 +100%、每秒回耐力 5。'),
    ('kFireBath', 'FireBath', '火浴', True, 8.0, False, '火浴：每秒回血（人數 <mag>）。'),
    ('kSourceLinger', 'SourceLinger', '火源餘溫', True, 2.0, False, '餘壓：洩壓後火源多留 2 秒。'),
    # A tier effect's age is its maturity clock (各階成熟 2 秒), so hits do not re-apply it; the separate decay timer is
    # what hits refresh (heat: 6 s without a fire hit; 聖佑: 8 s without hitting a marked target).
    ('kHoly1', 'Holy1', '聖佑 I', True, 3600.0, False, '聖佑 I（武器傷害 +10%、聖附傷 +10%）。'),
    ('kHoly2', 'Holy2', '聖佑 II', True, 3600.0, False, '聖佑 II（武器傷害 +20%、聖附傷 +20%、護甲 +50）。'),
    ('kHoly3', 'Holy3', '聖佑 III', True, 3600.0, False, '聖佑 III（武器傷害 +30%、聖附傷 +35%、護甲 +100）。'),
    ('kHolyDecay', 'HolyDecay', '聖佑維持', True, 8.0, False, '8 秒沒有命中帶神聖印記的目標，聖佑退一階。'),
    ('kOpenBoost', 'OpenBoost', '開印後', True, 5.0, False, '開印後 5 秒（元素 <mag>）。'),
    ('kEndBoost', 'EndBoost', '終焉後', True, 5.0, False, '終焉後 5 秒：接管元素附傷 +<mag>。'),
    ('kBloodthirst', 'Bloodthirst', '嗜血', True, 10.0, False, '嗜血：命中效果 +20%。'),
    ('kKillStreak', 'KillStreak', '連殺', True, 3600.0, False, '連殺：下一次潛行攻擊附傷 ×2。'),
    ('kBloodZone', 'BloodZone', '血區', True, 86400.0, False, '血區 <mag>（1 高、2 中、3 低）。'),
    ('kCrossCooldown', 'CrossCooldown', '越線冷卻', True, 10.0, False, '越線冷卻。'),
    ('kFireDomainPlayer', 'FireDomainPlayer', '身在火域', True, 2.0, False, '身在火域：熱度升階免等待。'),
    # 懲戒 (v0.4 2.3 / 5.9): the next 裁決 or 聖裁 +20% per layer, then cleared. Gaining it from hits taken is N4 (受擊);
    # round 22 has the consumption and 慈光's +2 on a divine open.
    ('kPunish', 'Punish', '懲戒', True, 8.0, False, '懲戒 <mag> 層：下一次裁決或聖裁每層 +20%。'),
]
KIND_NAMES = [k[0] for k in KINDS]

# Holy tiers: the passive halves of v0.4 5.9's tier table ride on the tier spell. The DLL casts the tier spells WITHOUT
# a magnitude override (override 0), because an override is written into every effect of the spell
# (native-verification-2: the apply visitor, 0x140551980), so the record magnitudes stand: weapon damage
# (AttackDamageMult +0.10/0.20/0.30) and armour (0/+50/+100).
HOLY_WEAPON = [0.10, 0.20, 0.30]
HOLY_ARMOR = [0.0, 50.0, 100.0]
AV_ATTACK_DAMAGE_MULT = 154  # RE::ActorValue::kAttackDamageMult (a multiplier, base 1.0); 34 is the flat MeleeDamage
AV_DAMAGE_RESIST = 39
AV_MAGIC_RESIST = 44

DOT_MAX_SECONDS = 45          # 15 s poison / 10 s bleed x the MCM duration multiplier (up to 3)
# (key, editor id suffix, label, element index, resist AV, description)
DOT_KINDS = [
    ('bleed', 'BleedDot', '流血', 5, 44, '每秒流失 <mag> 點生命。'),
    ('poison', 'PoisonDot', '中毒', 7, 40, '每秒受 <mag> 點毒傷。'),
]

POISON_DOSE_K = 0.2116        # v0.4 2.7 k_dot for poison (the GLOB ESSB_PoisonDotK default)

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
for _dot in DOT_KINDS:
    _take(_dot[0] + '.effect')
    _take(_dot[0] + '.spells', DOT_MAX_SECONDS)
_take('holyWeapon.effect')
_take('holyArmor.effect')
_take('frenzyBlade.effect')
_take('frenzyBlade.spell')
_take('iceChillGauge.effect')
_take('vision.effect')
_take('vision.spell')
LAST = _next - 1
assert LAST <= 0x54FF, hex(LAST)


def effect_id(kind):
    return _ids[kind + '.effect']


def spell_id(kind):
    return _ids[kind + '.spell']


def dot_effect_id(key):
    return _ids[key + '.effect']


def dot_spell_id(key, seconds):
    if not 1 <= seconds <= DOT_MAX_SECONDS:
        raise ValueError(seconds)
    return _ids[key + '.spells'] + seconds - 1


def frenzy_blade_spell_id():
    return _ids['frenzyBlade.spell']


def vision_spell_id():
    return _ids['vision.spell']


# v0.4 5.4 冰甲: enemies in the chill are slowed 20%, those with a freeze gauge >= 1 35% instead (霜膚 +10% on both). The
# gauge is the DLL's freeze effect now, so the chill spells carry two mutually exclusive slow effects conditioned on it
# (strongest, never both); the round-21 chill spells take the second effect (build/fix21_records.py).
ICE_CHILL_GAUGE_PCT = 35.0
ICE_CHILL_GAUGE_WIDE_PCT = 45.0


def ice_chill_gauge_effect_id():
    return _ids['iceChillGauge.effect']


def edid_effect(suffix):
    return f'ESSB_N3_{suffix}Effect'


def edid_spell(suffix):
    return f'ESSB_N3_{suffix}'


def dot_edid(suffix, seconds):
    return f'ESSB_N3_{suffix}_{seconds}'


def kind_row(kind):
    return next(k for k in KINDS if k[0] == kind)


def add_records(b, add, fx, settings):
    """fx: the build's fx lookup (editor selector -> FormID) for the frozen film and the white-hot flames;
    settings: settings.json (unused since the miasma cloak went; kept for the caller)."""
    I, Z = b.I, b.Z
    own = b.own
    etyp = ('ETYP', I(b.ref('Skyrim.esm', 0x13F45)))
    stub = ('VMAD', b.vmad(STUB_SCRIPT, {}))
    # v0.4 2.11: 冰封 has its own pale film for its 3 seconds; 白熱／熔燒 show full-body flames (Vulcano, falling back
    # to Phenderix's fire form shader when Vulcano is not installed).
    wanted = 'vulcano.esp|dar_moltenfxshader'
    flames = next((fid for key, fid in fx.items() if key.lower() == wanted), 0) or fx[f'{b.FX_PLUGIN}|ZZShader_FireForm']
    shaders = {'kFrozen': fx[b.FX_STATUS_FROZEN], 'kHeat3': flames, 'kHeat4': flames, 'kMoltenBody': flames}
    for kind, suffix, label, on_player, seconds, has_stub, text in KINDS:
        flags = SELF_FLAGS if on_player else TARGET_FLAGS
        if kind in ('kHeatDecay', 'kVentedHeat', 'kOpenBoost', 'kEndBoost', 'kBloodZone', 'kCrossCooldown',
                    'kFireDomainPlayer', 'kKillStreak', 'kHolyDecay', 'kSourceLinger'):
            flags = SELF_HIDDEN_FLAGS    # bookkeeping windows the player does not need to see
        shader = shaders.get(kind, 0)
        if shader:
            flags |= 0x1000               # FX persist: the shader stays for the effect's lifetime
        delivery = 0 if on_player else 1
        ss = [stub] if has_stub else []
        ss += [('FULL', Z(label)),
               ('DATA', b.mgef_data(flags, 1, casting=1, delivery=delivery, hit_shader=shader)),
               ('DNAM', Z(text))]
        add('MGEF', effect_id(kind), edid_effect(suffix), ss)
        # Record magnitude 0: a cast without an override (override 0) leaves 0 layers, so 0 means 0.
        efit = [('EFID', I(own(effect_id(kind)))), ('EFIT', struct.pack('<fII', 0.0, 0, int(seconds)))]
        tier = {'kHoly1': 0, 'kHoly2': 1, 'kHoly3': 2}.get(kind)
        if tier is not None:
            efit += [('EFID', I(own(_ids['holyWeapon.effect']))),
                     ('EFIT', struct.pack('<fII', HOLY_WEAPON[tier], 0, int(seconds)))]
            if HOLY_ARMOR[tier] > 0:
                efit += [('EFID', I(own(_ids['holyArmor.effect']))),
                         ('EFIT', struct.pack('<fII', HOLY_ARMOR[tier], 0, int(seconds)))]
        add('SPEL', spell_id(kind), edid_spell(suffix), [
            ('OBND', bytes(12)), ('FULL', Z(label)), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, delivery)),
        ] + efit)

    # 聖佑's weapon damage and armour: Peak Value Modifiers with Recover, like the mod's other timed buffs.
    for key, av, label in [('holyWeapon', AV_ATTACK_DAMAGE_MULT, '聖佑：武器傷害'),
                           ('holyArmor', AV_DAMAGE_RESIST, '聖佑：護甲')]:
        add('MGEF', _ids[key + '.effect'], f'ESSB_N3_{key[0].upper()}{key[1:]}Effect', [
            ('FULL', Z(label)),
            ('DATA', b.mgef_data(b.MGEF_BUFF_FLAGS, 34, actor_value=av, casting=1, delivery=0)),
        ])

    school_xp = 0.0   # a DoT tick is not a hit; the reaction spell already carries the school XP
    for key, suffix, label, ix, resist, text in DOT_KINDS:
        kws = [own(b.ID_KW_REACT), own(b.ID_KW_ELEMENT + ix)]
        add('MGEF', dot_effect_id(key), edid_effect(suffix), [
            ('FULL', Z(label)),
            ('KSIZ', I(len(kws))), ('KWDA', b''.join(I(x) for x in kws)),
            # Value Modifier on Health with a duration: hostile, detrimental, hidden, no area, no hit event.
            ('DATA', b.mgef_data(0x00008815, 0, base_cost=1.0, skill=b.SCHOOLS[ix], resist=resist, actor_value=24,
                                 casting=1, delivery=1, skill_usage=school_xp)),
            ('DNAM', Z(text)),
        ])
        for seconds in range(1, DOT_MAX_SECONDS + 1):
            add('SPEL', dot_spell_id(key, seconds), dot_edid(suffix, seconds), [
                ('OBND', bytes(12)), ('FULL', Z(label)), etyp, ('DESC', Z('')),
                ('SPIT', b.spit(0, 1, 1)),
                ('EFID', I(own(dot_effect_id(key)))), ('EFIT', struct.pack('<fII', 1.0, 0, seconds)),
            ])

    # v0.4 5.12 狂刃: a frenzied target deals +50% damage (it cuts its allies harder). The engine effect rides next to
    # the frenzy: ESSBController.ApplyFrenzy casts it for the same seconds when you own 狂刃 (AttackDamageMult +0.5).
    add('MGEF', _ids['iceChillGauge.effect'], 'ESSB_N3_IceChillGaugeEffect', [
        ('FULL', Z('冰甲寒氣（凍結中）')),
        ('DATA', b.mgef_data(hit21.CHILL_FLAGS, 34, actor_value=30, casting=2, delivery=2)),
        ('DNAM', Z('寒氣減速 <mag>%（目標帶凍結量表）。')),
        ('CTDA', hit21.HOSTILE_CTDA),
    ])
    add('MGEF', _ids['frenzyBlade.effect'], 'ESSB_N3_FrenzyBladeEffect', [
        ('FULL', Z('狂刃')),
        ('DATA', b.mgef_data(b.MGEF_BUFF_FLAGS | 0x8000, 34, actor_value=AV_ATTACK_DAMAGE_MULT, casting=1, delivery=1)),
        ('DNAM', Z('狂刃：瘋狂中造成的傷害 +50%。')),
    ])
    # v0.4 5.12 幻視 (line 1380: 3 s, attack -20%) on a target that cannot be charmed: attack damage x0.8, a multiplier
    # (AttackDamageMult -0.2, detrimental Value Modifier), not the flat MeleeDamage -20 of the old Papyrus (commander ruling).
    add('MGEF', _ids['vision.effect'], 'ESSB_N3_VisionEffect', [
        ('FULL', Z('幻視')),
        ('DATA', b.mgef_data(b.MGEF_DEBUFF_FLAGS, 34, actor_value=AV_ATTACK_DAMAGE_MULT, casting=1, delivery=1)),
        ('DNAM', Z('幻視：攻擊傷害 -<mag>（倍率）。')),
    ])
    add('SPEL', _ids['vision.spell'], 'ESSB_N3_Vision', [
        ('OBND', bytes(12)), ('FULL', Z('幻視')), etyp, ('DESC', Z('')),
        ('SPIT', b.spit(0, 1, 1)),
        ('EFID', I(own(_ids['vision.effect']))), ('EFIT', struct.pack('<fII', 0.2, 0, 3)),
    ])
    add('SPEL', _ids['frenzyBlade.spell'], 'ESSB_N3_FrenzyBlade', [
        ('OBND', bytes(12)), ('FULL', Z('狂刃')), etyp, ('DESC', Z('')),
        ('SPIT', b.spit(0, 1, 1)),
        ('EFID', I(own(_ids['frenzyBlade.effect']))), ('EFIT', struct.pack('<fII', 0.5, 0, 3)),
    ])


def contact_edids():
    """Spells cast ON the target (delivery 1): the target statuses, both DoTs, 狂刃."""
    names = {edid_spell(suffix) for kind, suffix, label, on_player, *_ in KINDS if not on_player}
    for key, suffix, *_ in DOT_KINDS:
        names |= {dot_edid(suffix, s) for s in range(1, DOT_MAX_SECONDS + 1)}
    return names | {'ESSB_N3_FrenzyBlade', 'ESSB_N3_Vision'}


def aimed_edids():
    """No aimed spells since the miasma cloak (and its payload) went."""
    return set()


def new_edids():
    names = set()
    for kind, suffix, *_ in KINDS:
        names |= {edid_effect(suffix), edid_spell(suffix)}
    for key, suffix, *_ in DOT_KINDS:
        names.add(edid_effect(suffix))
        names |= {dot_edid(suffix, s) for s in range(1, DOT_MAX_SECONDS + 1)}
    names |= {'ESSB_N3_HolyWeaponEffect', 'ESSB_N3_HolyArmorEffect',
              'ESSB_N3_FrenzyBladeEffect', 'ESSB_N3_FrenzyBlade', 'ESSB_N3_IceChillGaugeEffect'}
    names |= {'ESSB_N3_VisionEffect', 'ESSB_N3_Vision'}
    return names
