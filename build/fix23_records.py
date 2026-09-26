"""Round 23 (slice N4) records: your own resources, the hurt branches' windows and cooldowns, and the pools, as engine
effects the DLL reads and re-applies (ruling R3 / R4: DLL stores no design state; v0.4 2.3 "計數放在自身效果的強度").

  KINDS     one row per new status kind, appended to round 22's StatusKind (build/fix19_native.status_ids concatenates
            fix22_records.KINDS + these, in this order), so the round-22 machinery -- Board reads, Lower, the
            dispel-then-cast rule, the load-time resolution of every spell the DLL can cast -- covers them unchanged.
            Script-archetype rows are counters / windows / cooldowns: No Magnitude, magnitude override = count, the
            duration set through effectiveness (round 22 ledger decision 1). Rows with an actor value (`av`) are the
            engine halves of a resource (岩甲護甲、冰盾護甲與魔抗、逼近移速): Peak Value Modifiers the DLL casts with the
            record duration (effectiveness 1) and magnitude override = the value.
  GLOBALS   mirrors a PERK condition reads (v0.4 2.3: 門檻由 DLL 鏡射到全域變數); the older mirrors (ESSB_Sync,
            ESSB_SyncStage, ESSB_Charge, ESSB_Resolve, ESSB_IceShield, ESSB_RockArmor, ESSB_Wind) already exist.
  HOLY_MR   R7: the 聖佑 tier spells carry magic resist +10／20／35 (native MagicResist, the engine's 85% cap).

IDs 0x005500-0x0055FF (after round 22's 0x005400-0x0054FF). Append-only.
"""
import struct

BASE = 0x5500

TARGET_FLAGS = 0x00008C15      # hostile, detrimental, hidden, no magnitude / area / hit event (the mark flags)
SELF_FLAGS = 0x00000C10        # visible in the player's Active Effects, not hostile, no magnitude / area
SELF_HIDDEN_FLAGS = 0x00008C10
AV_FLAGS = 0x00008812          # build_v03 MGEF_BUFF_FLAGS: Recover, not hostile, hidden
AV_DAMAGE_RESIST = 39
AV_MAGIC_RESIST = 44
AV_SPEED_MULT = 30

# (kind, editor id suffix, label, on_player, seconds, hidden, description, av)
KINDS = [
    # ---- your resources (v0.4 2.3 你身上的資源)
    ('kSync', 'Sync', '同調', True, 86400.0, False, '同調 <mag>（三段門檻 5／15／30）。', None),
    ('kCharge', 'Charge', '電荷', True, 10.0, False, '電荷 <mag>（10 秒未命中歸零）。', None),
    ('kRockArmor', 'RockArmor', '岩甲', True, 86400.0, False, '岩甲 <mag> 層。', None),
    ('kWindGauge', 'WindGauge', '風勢', True, 5.0, False, '風勢 <mag>（5 秒未命中歸零）。', None),
    ('kResolve', 'Resolve', '戰意', True, 10.0, False, '戰意 <mag>（10 秒未命中歸零）。', None),
    ('kIceShield', 'IceShield', '冰盾', True, 8.0, False, '冰盾 <mag> 層。', None),
    ('kResonance', 'Resonance', '共鳴層', True, 20.0, False, '共鳴層 <mag>（20 秒沒有新增就歸零）。', None),
    ('kCosmos', 'Cosmos', '闇宙', True, 10.0, False, '闇星：闇宙 <mag>（每次命中打出一次滿層引爆）。', None),
    ('kOverload', 'Overload', '超載', True, 86400.0, False, '超載 <mag> 點魔力（先花超載；3 秒後每秒衰減）。', None),
    ('kOverloadWait', 'OverloadWait', '超載未衰減', True, 3.0, True, '最後一次灌魔後的等待。', None),
    ('kStoredForce', 'StoredForce', '蓄勁', True, 86400.0, False, '蓄勁 <mag>。', None),
    ('kExtreme', 'Extreme', '極致計數', True, 86400.0, True, '極致：同調三段的命中數 <mag>。', None),
    ('kAvatar', 'Avatar', '化身', True, 10.0, False, '化身：當前元素的持續傳奇主線視同點滿。', None),
    ('kAvatarCooldown', 'AvatarCooldown', '化身冷卻', True, 30.0, True, '化身冷卻。', None),
    ('kFormHeld', 'FormHeld', '同形態時間', True, 86400.0, True, '這個形態已開多久（專一）。', None),
    ('kSwitchCharge', 'SwitchCharge', '切換電荷', True, 60.0, True, '切換當下的電荷 <mag>（被切的雷終焉讀它）。', None),
    ('kPendingDischarge', 'PendingDischarge', '餘電', True, 30.0, True, '餘電：下一次開印附帶 ×0.5 放電（電荷 <mag>）。', None),
    ('kThunder', 'Thunder', '雷霆', True, 5.0, False, '雷霆：每次命中放電 ×0.3。', None),
    ('kQuickShock', 'QuickShock', '疾電', True, 3.0, False, '疾電：暴擊率 +15%。', None),
    ('kStrongShockCooldown', 'StrongShockCooldown', '強感電冷卻', True, 15.0, True, '強感電冷卻。', None),
    ('kWindFollow', 'WindFollow', '順勢', True, 5.0, False, '順勢：命中附帶一段風刃。', None),
    ('kConcert', 'Concert', '協奏待發', True, 3600.0, True, '切換後首次終焉 ×1.5。', None),
    ('kSyncKeepAll', 'SyncKeepAll', '三重奏保留', True, 60.0, True, '下一次融斷後保留全部同調。', None),
    ('kFallingStar', 'FallingStar', '墜星', True, 30.0, True, '墜星：闇宙 <mag> 層留到被切那一擊。', None),
    ('kSurgeUp', 'SurgeUp', '回湧', True, 8.0, False, '回湧：下一次重擊不扣血、命中效果 ×1.5、血痕 +2。', None),
    ('kChargedQuake', 'ChargedQuake', '蓄能', True, 3600.0, False, '蓄能：下一次地震／碎岩 +<mag>。', None),
    ('kBracing', 'Bracing', '蓄能架勢', True, 3.0, False, '蓄能：物理減傷 +<mag>%。', None),
    ('kInterruptCooldown', 'InterruptCooldown', '斷咒冷卻', True, 5.0, True, '斷咒冷卻。', None),
    ('kIceHeartCooldown', 'IceHeartCooldown', '冰心冷卻', True, 30.0, True, '冰心冷卻。', None),
    ('kSanctuaryCooldown', 'SanctuaryCooldown', '庇護冷卻', True, 30.0, True, '庇護冷卻。', None),
    ('kRetaliateCooldown', 'RetaliateCooldown', '反震冷卻', True, 10.0, True, '反震冷卻。', None),
    ('kReverseCooldown', 'ReverseCooldown', '逆電冷卻', True, 2.0, True, '逆電冷卻。', None),
    ('kUnyieldCooldown', 'UnyieldCooldown', '不屈冷卻', True, 3.0, True, '不屈冷卻。', None),
    ('kSpellReturnCooldown', 'SpellReturnCooldown', '咒返冷卻', True, 5.0, True, '咒返冷卻。', None),
    ('kPunishCooldown', 'PunishCooldown', '懲戒間隔', True, 1.0, True, '懲戒每 0.5 秒最多一層。', None),
    ('kCloseIn', 'CloseIn', '逼近', True, 2.0, False, '逼近：化法為力的回魔比例加倍。', None),
    ('kCloseInCooldown', 'CloseInCooldown', '逼近冷卻', True, 6.0, True, '逼近冷卻。', None),
    ('kTideBodyCooldown', 'TideBodyCooldown', '潮身冷卻', True, 30.0, True, '潮身冷卻。', None),
    ('kLingerCooldown', 'LingerCooldown', '餘魔冷卻', True, 30.0, True, '餘魔冷卻。', None),
    ('kLingerShield', 'LingerShield', '餘魔', True, 2.0, False, '餘魔：法盾改扣耐力再撐 2 秒。', None),
    ('kCleanseCooldown', 'CleanseCooldown', '洗淨冷卻', True, 3.0, True, '洗淨冷卻。', None),
    ('kAfterimage', 'Afterimage', '殘影', True, 2.0, False, '殘影：下一次攻擊無效。', None),
    ('kCloakGuard', 'CloakGuard', '破護', True, 2.0, False, '破護：不受元素披風反傷。', None),
    # ---- the engine halves of your resources (Peak Value Modifiers; magnitude override = the value)
    ('kRockArmorAV', 'RockArmorAV', '岩甲：護甲', True, 86400.0, False, '岩甲護甲 +<mag>。', AV_DAMAGE_RESIST),
    ('kIceShieldArmorAV', 'IceShieldArmorAV', '冰盾：護甲', True, 8.0, False, '冰盾護甲 +<mag>。', AV_DAMAGE_RESIST),
    ('kIceShieldMagicAV', 'IceShieldMagicAV', '冰盾：魔抗', True, 8.0, False, '冰盾魔抗 +<mag>%。', AV_MAGIC_RESIST),
    ('kCloseInSpeed', 'CloseInSpeed', '逼近：移速', True, 2.0, False, '移速 +<mag>%。', AV_SPEED_MULT),
    # ---- on the target (an attacker, or the one you opened on)
    ('kRetortCooldown', 'RetortCooldown', '反制冷卻', False, 3.0, True, '灼身／寒反／靜電／毒皮對這個攻擊者 3 秒一次。', None),
    ('kGrudgeCooldown', 'GrudgeCooldown', '怨縛冷卻', False, 2.0, True, '怨縛對這個攻擊者 2 秒一次。', None),
    ('kOath', 'Oath', '誓約', False, 8.0, True, '誓約：它 8 秒內打你，懲戒 +2。', None),
    ('kLastHitSneak', 'LastHitSneak', '潛行命中', False, 1.0, True, '1 秒內被你的潛行攻擊命中（形態 <mag>）。', None),
]
# 三重奏 (5.2): one 10-second marker per element whose end you triggered (a sliding window per element, like the Papyrus
# PushTrio it replaces); three present at an end = the third ×3.
ELEMENT_SHORT = ['火', '冰', '雷', '土', '風', '血', '聖', '毒', '水', '暗', '星']
KINDS += [(f'kTrio{e}', f'Trio{e}', f'三重奏：{ELEMENT_SHORT[e - 1]}', True, 10.0, True, f'10 秒內觸發過{ELEMENT_SHORT[e - 1]}終焉。', None)
          for e in range(1, 12)]
KIND_NAMES = [k[0] for k in KINDS]

# Mirrors a PERK condition reads (GetGlobalValue): the DLL writes them from the effects (v0.4 2.3).
GLOBALS = [
    ('ESSB_Bracing', 0),   # 蓄能：格擋換來的物理減傷點數（0..10）
]

HOLY_MR = [10.0, 20.0, 35.0]   # R7：聖佑 I／II／III 魔抗（原生魔抗，引擎 85% 上限）

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
for _name, _default in GLOBALS:
    _take(_name)
_take('holyMagic.effect')
LAST = _next - 1
assert LAST <= 0x55FF, hex(LAST)


def effect_id(kind):
    return _ids[kind + '.effect']


def spell_id(kind):
    return _ids[kind + '.spell']


def global_id(name):
    return _ids[name]


def holy_magic_effect_id():
    return _ids['holyMagic.effect']


def edid_effect(suffix):
    return f'ESSB_N4_{suffix}Effect'


def edid_spell(suffix):
    return f'ESSB_N4_{suffix}'


def kind_row(kind):
    return next(k for k in KINDS if k[0] == kind)


def add_records(b, add):
    I, Z, F = b.I, b.Z, b.F
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
        # Record magnitude 0 (a counter cast without an override has no layers); the DLL always casts with an override.
        add('SPEL', spell_id(kind), edid_spell(suffix), [
            ('OBND', bytes(12)), ('FULL', Z(label)), etyp, ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, delivery)),
            ('EFID', I(own(effect_id(kind)))), ('EFIT', struct.pack('<fII', 0.0, 0, int(seconds))),
        ])
    for name, default in GLOBALS:
        add('GLOB', global_id(name), name, [('FNAM', b's'), ('FLTV', F(default))])
    # R7 聖佑魔抗：a Peak Value Modifier the tier spells carry (build/fix22_records.py adds it to each tier spell).
    add('MGEF', holy_magic_effect_id(), 'ESSB_N4_HolyMagicEffect', [
        ('FULL', Z('聖佑：魔抗')),
        ('DATA', b.mgef_data(AV_FLAGS, 34, actor_value=AV_MAGIC_RESIST, casting=1, delivery=0)),
    ])


def contact_edids():
    """Spells cast ON a target (delivery 1)."""
    return {edid_spell(suffix) for kind, suffix, label, on_player, *_ in KINDS if not on_player}


def new_edids():
    names = set()
    for kind, suffix, *_ in KINDS:
        names |= {edid_effect(suffix), edid_spell(suffix)}
    names |= {name for name, _ in GLOBALS}
    names.add('ESSB_N4_HolyMagicEffect')
    return names
